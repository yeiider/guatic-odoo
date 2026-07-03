from odoo import models, fields


class CrmAsertisServicio(models.Model):
    _name = 'crm_asertis_servicios'
    _description = 'Servicios CRM Asertis'
    _order = 'nombre'

    nombre = fields.Char(string='Nombre del Servicio', required=True)
    color = fields.Integer(string='Color', default=0)

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.nombre}"
