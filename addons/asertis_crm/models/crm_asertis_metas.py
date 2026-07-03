from odoo import models, fields


class CrmAsertisMetas(models.Model):
    _name = 'crm_asertis_metas'
    _description = 'Metas CRM Asertis'


    meta = fields.Float(string='Meta (valor)', required=True)


    def name_get(self): 
        result = []
        for rec in self:
            name = rec.meta
            result.append((rec.id, name))
        return result