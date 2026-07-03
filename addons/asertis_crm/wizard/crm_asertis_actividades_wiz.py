from odoo import models, fields, api


class CrmAsertisActividadesWizard(models.TransientModel):
    _name = 'crm_asertis_actividades_wizard'
    _description = 'Wizard para registrar actividad'

    actividad = fields.Selection([
        ('llamada', 'Llamada'),
        ('reunion', 'Reunión'),
        ('email', 'Correo'),
        ('otro', 'Otro'),
    ], string='Tipo de Actividad', required=True)
    descripcion = fields.Text(string='Descripción')
    fecha = fields.Datetime(string='Fecha', default=fields.Datetime.now)
    crm_id = fields.Many2one('crm_asertis', string='Relacionado a', required=True)


    def action_guardar_actividad(self):
        self.ensure_one()
        self.env['crm_asertis_actividades'].create({
            'actividad': self.actividad,
            'descripcion': self.descripcion,
            'fecha': self.fecha,
            'crm_id': self.crm_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}
