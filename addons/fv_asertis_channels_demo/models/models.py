# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class fv_asertis_channels_demo(models.Model):
#     _name = 'fv_asertis_channels_demo.fv_asertis_channels_demo'
#     _description = 'fv_asertis_channels_demo.fv_asertis_channels_demo'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

