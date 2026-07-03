from odoo import models, fields


class CrmAsertisStages(models.Model):
    _name = 'crm_asertis_stages'
    _description = 'Estados del flujo'
    _order = 'sequence'


    name = fields.Char('Nombre del Estado', required=True)
    sequence = fields.Integer('Secuencia', default=10)
    fold = fields.Boolean('Colapsado en Kanban')


    def name_get(self): 
        result = []
        for rec in self:
            name = rec.name
            result.append((rec.id, name))
        return result
