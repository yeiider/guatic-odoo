from odoo import models, fields, api, _


class WhatsappAsertisTemplateSendWizardParam(models.TransientModel):
    _name = "whatsapp.asertis.template.send.wizard.param"
    _description = "Línea de parámetro para wizard de envío"
    _order = "param_sequence"

    wizard_id = fields.Many2one(
        "whatsapp.asertis.template.send.wizard",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )

    param_id = fields.Many2one(
        "whatsapp.asertis.template.param",
        string="Parámetro",
        readonly=True,
    )

    param_name = fields.Char(related="param_id.name", string="Nombre", readonly=True)

    param_sequence = fields.Integer(
        related="param_id.sequence", string="Secuencia", readonly=True
    )

    param_field_name = fields.Char(
        related="param_id.field_name", string="Campo Origen", readonly=True
    )

    param_value = fields.Text(
        string="Valor", required=False, help="Valor que se enviará en la plantilla"
    )
