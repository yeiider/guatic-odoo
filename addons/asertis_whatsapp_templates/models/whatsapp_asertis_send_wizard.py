from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WhatsappAsertisTemplateSendWizard(models.TransientModel):
    _name = "whatsapp.asertis.template.send.wizard"
    _description = "Enviar plantilla de WhatsApp con parámetros editables"

    # Una sola plantilla
    template_id = fields.Many2one(
        comodel_name="whatsapp.asertis.template",
        string="Plantilla de WhatsApp",
        required=True,
    )

    record_id = fields.Integer(string="ID del Registro")
    model = fields.Char(string="Modelo")
    model_id = fields.Many2one(
        "ir.model", string="Modelo ID", compute="_compute_model_id", store=False
    )
    template_type = fields.Selection(
        related="template_id.template_type", string="Tipo de Plantilla", readonly=True
    )

    template_description = fields.Text(
        related="template_id.description", string="Descripción", readonly=True
    )
    param_line_ids = fields.One2many(
        "whatsapp.asertis.template.send.wizard.param", "wizard_id", string="Parámetros"
    )
    preview_text = fields.Html(
        string="Vista Previa", compute="_compute_preview_text", readonly=True
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

    @api.depends("template_id", "param_line_ids", "param_line_ids.param_value")
    def _compute_preview_text(self):
        for record in self:
            if not record.template_id:
                record.preview_text = ""
                continue

            if not record.param_line_ids:
                record.preview_text = "<p><i>Esta plantilla no tiene parámetros</i></p>"
                continue
            preview_html = "<div class='o_whatsapp_preview'>"
            preview_html += f"<h5>📱 Plantilla: {record.template_id.name}</h5>"
            preview_html += "<p><strong>Parámetros que se enviarán:</strong></p>"
            preview_html += "<ol>"
            sorted_params = record.param_line_ids.sorted(
                lambda x: x.param_id.sequence if x.param_id else 999
            )
            for param_line in sorted_params:
                value = param_line.param_value or "[Sin valor]"
                param_name = (
                    param_line.param_id.name if param_line.param_id else "Parámetro"
                )
                preview_html += f"<li><strong>{param_name}:</strong> {value}</li>"

            preview_html += "</ol></div>"
            record.preview_text = preview_html

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")

        res.update(
            {
                "model": active_model,
                "record_id": active_id,
            }
        )
        default_template_id = self.env.context.get("default_template_id")
        if default_template_id:
            res["template_id"] = default_template_id

        return res

    @api.onchange("template_id")
    def _onchange_template_id(self):
        """Cargar parámetros de la plantilla seleccionada"""
        self.param_line_ids = [(5, 0, 0)]  # Limpiar todas las líneas

        if not self.template_id:
            return
        record = None
        if self.model and self.record_id:
            try:
                record = self.env[self.model].browse(self.record_id)
                if not record.exists():
                    record = None
            except:
                record = None
        param_lines = []
        for param_config in self.template_id.param_ids.sorted("sequence"):
            if not param_config.active:
                continue
            default_value = ""
            if record:
                try:
                    default_value = (
                        param_config.get_field_value(record)
                        or param_config.default_value
                        or ""
                    )
                except:
                    default_value = param_config.default_value or ""
            else:
                default_value = param_config.default_value or ""

            param_lines.append(
                (
                    0,
                    0,
                    {
                        "param_id": param_config.id,
                        "param_sequence": param_config.sequence,
                        "param_value": default_value,
                        "param_name": param_config.name,
                        "param_field_name": param_config.field_name,
                    },
                )
            )

        self.param_line_ids = param_lines

    def _get_current_param_values(self):
        """Obtener valores actuales de los parámetros en orden correcto"""
        if not self.template_id:
            return []
        if not self.param_line_ids:
            return []

        param_lines = self.param_line_ids.sorted(
            lambda x: x.param_id.sequence if x.param_id else 999
        )
        return [line.param_value or "" for line in param_lines]

    def action_send_template(self):
        """Enviar la plantilla con los parámetros personalizados"""
        if not self.template_id:
            raise UserError(_("Debe seleccionar una plantilla."))

        if not self.model or not self.record_id:
            raise UserError(_("No se pudo determinar el modelo o el registro."))

        record = self.env[self.model].browse(self.record_id)
        if not record.exists():
            raise UserError(_("El registro no existe."))
        custom_params = self._get_current_param_values()
        for param_line in self.param_line_ids:
            if param_line.param_id.is_required and not param_line.param_value.strip():
                raise UserError(
                    _("El parámetro '%s' es requerido") % param_line.param_id.name
                )

        try:
            result = self.template_id.send_template(
                record_id=record.id, custom_params=custom_params
            )
            self._onchange_template_id()
            if result.get("success"):
                message = (
                    _("Plantilla '%s' enviada exitosamente.") % self.template_id.name
                )
                message_type = "success"

            else:
                error_msg = result.get("error", "Error desconocido")
                message = _("Error al enviar plantilla: %s") % error_msg
                message_type = "danger"

        except Exception as e:
            message = _("Error al enviar plantilla: %s") % str(e)
            message_type = "danger"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WhatsApp"),
                "message": message,
                "type": message_type,
                "sticky": message_type == "danger",
            },
        }

    def action_reload_params(self):
        """Recargar parámetros desde la plantilla"""
        self._onchange_template_id()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Parámetros Recargados"),
                "message": _(
                    "Los parámetros se han recargado desde la configuración de la plantilla"
                ),
                "type": "info",
            },
        }
