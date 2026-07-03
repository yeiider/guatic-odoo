from odoo import models, fields


class InheritResUsers(models.Model):
    _inherit = 'res.users'

    area = fields.Selection(selection=[('Asertis', 'Asertis'), ('Fenalsistemas', 'Fenalsistemas')], string="Área")
