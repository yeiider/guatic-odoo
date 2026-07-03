from odoo import models, fields, api


class CrmAsertisActividad(models.Model):
    _name = 'crm_asertis_actividades'
    _description = 'Actividad registrada'
    _order = 'fecha desc'

    crm_id = fields.Many2one('crm_asertis', string='Relacionado a', required=True, ondelete='cascade')
    actividad = fields.Selection([
        ('llamada', 'Llamada'),
        ('reunion', 'Reunión'),
        ('email', 'Correo'),
        ('otro', 'Otro'),
    ], string='Tipo de Actividad', required=True)
    descripcion = fields.Text(string='Descripción')
    fecha = fields.Datetime(string='Fecha', default=fields.Datetime.now)
