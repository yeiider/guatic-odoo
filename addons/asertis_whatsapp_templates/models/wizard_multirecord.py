from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WhatsappAsertisTemplateMultiSendWizard(models.TransientModel):
    _name = "whatsapp.asertis.template.multi.send.wizard"
    _description = "Enviar plantilla de WhatsApp a múltiples oportunidades"

    template_id = fields.Many2one(
        comodel_name="whatsapp.asertis.template",
        string="Plantilla de WhatsApp",
        required=True,
    )

    record_ids = fields.Many2many(
        comodel_name="crm.lead", string="Oportunidades Seleccionadas"
    )

    model = fields.Char(string="Modelo", default="crm.lead")
    model_id = fields.Many2one(
        "ir.model", string="Modelo ID", compute="_compute_model_id", store=False
    )

    @api.depends("model")
    def _compute_model_id(self):
        for record in self:
            if record.model:
                model_record = self.sudo().env["ir.model"].search(
                    [("model", "=", record.model)], limit=1
                )
                record.model_id = model_record.id if model_record else False
            else:
                record.model_id = False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])

        res.update(
            {
                "model": active_model,
                "record_ids": [(6, 0, active_ids)],
            }
        )

        return res

    def action_send_template(self):
        """Enviar la plantilla a todas las oportunidades seleccionadas"""
        if not self.template_id:
            raise UserError(_("Debe seleccionar una plantilla."))

        if not self.record_ids:
            raise UserError(_("No hay oportunidades seleccionadas."))

        success_count = 0
        error_count = 0
        errors = []

        for lead in self.record_ids:
            try:
                # Enviar usando los valores automáticos de cada registro
                result = self.template_id.send_template(record_id=lead.id)

                if result.get("success"):
                    success_count += 1
                else:
                    error_count += 1
                    error_msg = result.get("error", "Error desconocido")
                    errors.append(f"• {lead.name}: {error_msg}")

            except Exception as e:
                error_count += 1
                errors.append(f"• {lead.name}: {str(e)}")

        # Preparar mensaje de resultado
        if error_count == 0:
            message = (
                _("✅ Plantilla enviada exitosamente a %s oportunidad(es)")
                % success_count
            )
            message_type = "success"
        elif success_count == 0:
            message = _(
                "❌ Error al enviar a todas las oportunidades:\n%s"
            ) % "\n".join(errors[:3])
            message_type = "danger"
        else:
            message = _(
                "⚠️ Enviado a %s oportunidad(es). Falló en %s.\n\nErrores:\n%s"
            ) % (success_count, error_count, "\n".join(errors[:3]))
            if len(errors) > 3:
                message += f"\n... y {len(errors) - 3} errores más"
            message_type = "warning"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WhatsApp - Envío Masivo"),
                "message": message,
                "type": message_type,
                "sticky": True,
            },
        }
