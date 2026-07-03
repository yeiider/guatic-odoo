import json
from odoo import http
from odoo.http import request
from markupsafe import escape
import logging
import html

_logger = logging.getLogger(__name__)


class ChannelController(http.Controller):
    """Controlador para crear canales y hilos de discusión desde una URL."""
    @http.route('/fv_create_channels_demo', type='json', auth='public', website=True, csrf=False, methods=['POST'])
    def create_demo_channel(self, **mjs_entrada):
        """
        Creates or updates a demo channel and thread with the provided parameters.
        This method processes incoming JSON data to create or update a parent channel,
        a child channel, and a thread (message root). It also associates administrator
        users as members of the created channels and adds messages to the thread.
        Args:
            **mjs_entrada: Arbitrary keyword arguments (not used directly).
        Returns:
            str: HTML response indicating the success or failure of the operation.
        JSON Parameters:
            - canal_hijo (str): Name of the child channel to create or update.
            - canal_padre (str): Name of the parent channel to create or update.
            - thread (str): Subject of the thread (message root) to create or update.
            - mensaje (str): Message content to add to the thread.
        Behavior:
            - Validates the presence of required parameters ('canal_hijo', 'thread', 'mensaje').
            - Searches for or creates the parent channel (`canal_padre`) and child channel (`canal_hijo`).
            - Associates all administrator users as members of the created channels.
            - Searches for or creates the thread (message root) in the child channel.
            - Adds the provided message to the thread, either as the root message or as a reply.
        Logging:
            - Logs received data and the results of channel and thread searches.
        Errors:
            - Returns an error message if required parameters are missing.
        """
        # Extraer parámetros del JSON recibido
        cuerpo_solicitud = http.request.httprequest.data.decode()
        data = json.loads(cuerpo_solicitud)

        canal_hijo = escape(data.get("canal_hijo", "").strip())
        canal_padre = escape(data.get("canal_padre", "").strip())
        thread = escape(data.get("thread", "").strip())
        mensaje = escape(data.get("mensaje", "").strip())

        _logger.info(f"Datos recibidos: canal='{canal_hijo}', thread='{thread}', mensaje='{mensaje}'")
        # Validar parámetros

        if not canal_hijo or not thread or not mensaje:
            return "<h3>Error: Debes enviar los parámetros 'canal', 'thread' y 'mensaje'.</h3>"

        # Buscar o crear canal 
        Channel = request.env['discuss.channel'].sudo()
        # El canal padre es el canal principal, el hijo es el canal secundario

        channel_padre = Channel.search([('name', '=', canal_padre)], limit=1)  #canal 

        AdminUsers = request.env['res.users'].sudo().search([('groups_id.name', '=', 'Administrator')])
        if not channel_padre:
            channel_padre = Channel.sudo().create({
                'name': canal_padre,
                'channel_type': 'channel',
            })
        #channel_padre.message_subscribe(partner_ids=[admin.partner_id.id]) 
        # Relacionar como miembros a todos los usuarios que son administradores

        ChannelMember = request.env['discuss.channel.member'].sudo()
        for admin in AdminUsers:
            if not ChannelMember.search([('channel_id', '=', channel_padre.id), ('partner_id', '=', admin.partner_id.id)]):
                ChannelMember.create({
                    'channel_id': channel_padre.id,
                    'partner_id': admin.partner_id.id,
                })
        # Buscar o crear canal hijo

        channel_hijo = Channel.search([('name', '=', canal_hijo) , ('parent_channel_id','=',channel_padre.id)], limit=1)  #canal 

        _logger.info(f"Canal padre encontrado: {channel_padre}, Canal hijo encontrado: {channel_hijo}")

        if not channel_hijo:
            channel_hijo = Channel.sudo().create({
            'name': canal_hijo,
            'channel_type': 'channel',
            'parent_channel_id': channel_padre.id
            })
              
        # Relacionar como miembros a todos los usuarios que son administradores
        for admin in AdminUsers:
            if not ChannelMember.search([('channel_id', '=', channel_hijo.id), ('partner_id', '=', admin.partner_id.id)]):
                ChannelMember.create({
                    'channel_id': channel_hijo.id,
                    'partner_id': admin.partner_id.id,
                })

        # Registrar en el log los canales creados o encontrados 
        _logger.info(f"Canal padre creado o encontrado: {channel_padre}, Canal hijo creado o encontrado: {channel_hijo}")   
        # Buscar mensaje raíz (hilo) por subject
        Message = request.env['mail.message'].sudo()
        mensaje_raiz = Message.search([
            ('model', '=', 'discuss.channel'), 
            ('res_id', '=', channel_padre.id),
            ('subject', '=', thread),
            ('parent_id', '=', False),
        ], limit=1)
        
        _logger.info(f"Mensaje raíz encontrado: {mensaje}")

        mensaje_html = """
            <div>
                <h3 style="color: #5A9;">¡Hola!</h3>
                <p>Este es un <strong>mensaje HTML</strong> enviado desde el backend.</p>
                <p>Puedes incluir <a href='https://www.odoo.com' target='_blank'>enlaces</a>, listas, estilos, etc.</p>
            </div>
        """
        mensaje = html.unescape(mensaje)
        # Crear respuesta al hilo
        Message.create({
            'model': 'discuss.channel',
            'res_id': channel_hijo.id,
            'body': mensaje, 
            'message_type': 'comment',
            'subtype_id': request.env.ref('mail.mt_comment').id,
            'parent_id': mensaje_raiz.id,
            #'name' : 'Thread' 
        })
   
        ''' 
        if not mensaje_raiz: 
            
            # Crear mensaje raíz (inicio de hilo)
            mensaje_raiz = Message.create({
                'model': 'discuss.channel',
                'res_id': channel_hijo.id,
                'subject': thread,
                'body': f"<b>Inicio del hilo {thread}</b><br>{mensaje}",
                'message_type': 'comment',
                'subtype_id': request.env.ref('mail.mt_comment').id,
                #'name' : 'Thread'
            })
        else:   
            '''
        
        return f"<h3>✅ Canal '{channel_padre}' y hilo '{thread}' actualizados con mensaje: '{mensaje}'</h3>"
