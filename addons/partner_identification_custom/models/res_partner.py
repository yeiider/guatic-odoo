from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    personal_id_type = fields.Selection(
        [
            ("CC", "Cédula de ciudadanía"),
            ("CE", "Cédula de extranjería"),
            ("TI", "Tarjeta de identidad"),
            ("NIT", "NIT (persona natural)"),
            ("PASSPORT", "Pasaporte"),
        ],
        default="CC",
        string="Tipo de identificación personal",
    )

    personal_id_number = fields.Char(
        string="Número de identificación personal",
    )
