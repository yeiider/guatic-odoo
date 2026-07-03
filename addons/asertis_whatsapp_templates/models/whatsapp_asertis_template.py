from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import requests
import json
from datetime import datetime
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class WhatsappAsertisTemplate(models.Model):
    _name = "whatsapp.asertis.template"
    _description = "Plantillas de WhatsApp Asertis"
    _order = "name"
    _rec_name = "name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Nombre de Plantilla",
        required=True,
        help="Nombre descriptivo de la plantilla",
    )
    template_name = fields.Char(
        string="Nombre del Template",
        required=True,
        help="Nombre del template en la API",
    )

    template_id_api = fields.Char(
        string="ID del Template", required=True, help="ID del template en la API"
    )

    config_id = fields.Many2one(
        "whatsapp.asertis.config",
        string="Configuración WhatsApp",
        required=True,
        help="Configuración de WhatsApp a utilizar",
    )
    model_id = fields.Many2one(
        string="Modelo de Aplicación",
        comodel_name="ir.model",
        default=lambda self: self.sudo().env["ir.model"]._get_id("res.partner"),
        ondelete="cascade",
        required=True,
        store=True,
        tracking=1,
    )
    model = fields.Char(
        string="Related Document Model", related="model_id.model", readonly=True
    )
    template_type = fields.Selection(
        [
            ("text", "Texto"),
            ("location", "Ubicación"),
            ("contact", "Contacto"),
            ("interactive", "Interactivo"),
            ("image", "Imagen"),
            ("video", "Video"),
            ("document", "Documento"),
            ("button", "Con Botones"),
            ("list", "Lista"),
            ("carousel", "Carrusel"),
        ],
        string="Tipo de Plantilla",
        default="text",
        required=True,
    )
    phone_field = fields.Selection(
        selection=[
            ("mobile", "Móvil"),
            ("phone", "Teléfono"),
            ("phone_mobile", "Teléfono / Móvil"),
            ("contact_phone", "Teléfono Contacto"),
            ("contact_mobile", "Móvil Contacto"),
        ],
        default="mobile",
        string="Campo de Teléfono",
        required=True,
        help="Campo del contacto a usar para el número de teléfono",
    )
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está activo, la plantilla estará disponible para uso",
    )

    description = fields.Text(
        string="Descripción", help="Descripción detallada de la plantilla y su uso"
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
        help="Compañía a la que pertenece la plantilla",
    )

    param_ids = fields.One2many(
        "whatsapp.asertis.template.param",
        string="Parámetros",
        inverse_name="template_id",
        help="Parámetros dinámicos de la plantilla",
    )
    message_log_ids = fields.One2many(
        "whatsapp.asertis.message.log",
        "template_id",
        string="Historial de Mensajes",
        readonly=True,
    )
    usage_count = fields.Integer(
        string="Veces Utilizada",
        compute="_compute_usage_count",
        store=True,
        help="Número de veces que se ha usado esta plantilla",
    )
    last_used_date = fields.Datetime(
        string="Último Uso",
        compute="_compute_last_used_date",
        store=True,
        help="Fecha del último uso de la plantilla",
    )
    preview_text = fields.Text(
        string="Vista Previa",
        compute="_compute_preview_text",
        help="Vista previa de la plantilla con parámetros de ejemplo",
    )
    param_count = fields.Integer(
        string="Número de Parámetros",
        compute="_compute_param_count",
        help="Cantidad de parámetros configurados",
        store=True,
    )

    @api.depends("message_log_ids")
    def _compute_usage_count(self):
        """Calcular número de usos de la plantilla"""
        for template in self:
            template.usage_count = len(template.message_log_ids)

    @api.depends("message_log_ids.sent_date")
    def _compute_last_used_date(self):
        """Calcular fecha del último uso"""
        for template in self:
            if template.message_log_ids:
                template.last_used_date = max(
                    template.message_log_ids.mapped("sent_date")
                )
            else:
                template.last_used_date = False

    @api.depends("param_ids")
    def _compute_param_count(self):
        """Contar parámetros configurados"""
        for template in self:
            template.param_count = len(template.param_ids)

    @api.depends("param_ids", "param_ids.name", "param_ids.default_value")
    def _compute_preview_text(self):
        """Generar vista previa con valores de ejemplo"""
        for template in self:
            if not template.param_ids:
                template.preview_text = "Plantilla sin parámetros configurados"
                continue

            preview_parts = []
            for i, param in enumerate(template.param_ids.sorted("sequence"), 1):
                value = param.default_value or f"[{param.name}]"
                preview_parts.append(f"Parámetro {i}: {value}")

            template.preview_text = "\n".join(preview_parts)

    @api.depends("model")
    def _compute_phone_field(self):
        to_reset = self.filtered(lambda template: not template.model)
        if to_reset:
            to_reset.phone_field = False
        for template in self.filtered("model"):
            if (
                template.phone_field
                and template.phone_field in self.env[template.model]._fields
            ):
                continue
            if "mobile" in self.env[template.model]._fields:
                template.phone_field = "mobile"
            elif "phone" in self.env[template.model]._fields:
                template.phone_field = "phone"

    @api.onchange("model_id")
    def _onchange_model_id(self):
        """Limpiar parámetros al cambiar modelo"""
        if self._origin and self._origin.model_id != self.model_id:
            self.param_ids = [(5, 0, 0)]

    @api.constrains("param_ids")
    def _check_param_sequence(self):
        """Validar que las secuencias de parámetros sean únicas"""
        for template in self:
            sequences = template.param_ids.mapped("sequence")
            if len(sequences) != len(set(sequences)):
                raise ValidationError(
                    _("Las secuencias de parámetros deben ser únicas")
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create para configuración por defecto"""
        default_config = self.env["whatsapp.asertis.config"].get_default_config()
        if default_config:
            for vals in vals_list:
                if not vals.get("config_id"):
                    vals["config_id"] = default_config.id
                if not vals.get("bot_id"):
                    vals["bot_id"] = default_config.bot_id
                if not vals.get("platform_id"):
                    vals["platform_id"] = default_config.platform_id

        return super().create(vals_list)

    def action_test_template(self):
        """Acción para probar la plantilla"""
        self.ensure_one()
        model = self.env[self.model_id.model]
        sample_record = model.search([], limit=1)

        if not sample_record:
            raise UserError(
                _("No hay registros disponibles en el modelo %s para probar")
                % self.model_id.name
            )
        test_params = self._get_template_params(sample_record)

        return {
            "type": "ir.actions.act_window",
            "name": _("Prueba de Plantilla"),
            "view_mode": "form",
            "res_model": "whatsapp.asertis.template.send.wizard",
            "target": "new",
            "context": {
                "default_template_id": self.id,
                "default_test_mode": True,
                "default_record_id": sample_record.id,
                "test_params": test_params,
            },
        }

    def send_template(self, record_id, phone=None, custom_params=None):
        """
        Enviar plantilla a un registro específico

        Args:
            record_id: ID del registro origen
            phone: Número de teléfono (opcional, se obtiene del registro)
            custom_params: Parámetros personalizados (opcional)

        Returns:
            dict: Resultado del envío
        """
        self.ensure_one()

        try:
            model = self.env[self.model_id.model]
            record = model.browse(record_id)

            if not record.exists():
                raise UserError(_("El registro no existe"))
            phone_number = phone or self._get_phone_from_record(record)
            if not phone_number:
                raise UserError(_("No se pudo obtener el número de teléfono"))
            params = custom_params or self._get_template_params(record)
            success, response_data = self._send_whatsapp_message(phone_number, params)
            if success:
                params_html = ""
                if params:
                    params_list = [f"<li>{param}</li>" for param in params]
                    params_html = f"<ul>{''.join(params_list)}</ul>"

                message_body = Markup(
                    "<p><strong>✅ Plantilla de WhatsApp enviada exitosamente</strong></p>"
                    "<p><strong>Plantilla:</strong> %s</p>"
                    "<p><strong>Número:</strong> %s</p>"
                    "%s"
                ) % (
                    self.name,
                    phone_number,
                    (
                        Markup(f"<p><strong>Parámetros:</strong></p>{params_html}")
                        if params_html
                        else ""
                    ),
                )

                if hasattr(record, "message_post") and callable(
                    getattr(record, "message_post", None)
                ):
                    record.message_post(
                        body=message_body,
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                        author_id=self.env.user.partner_id.id,
                    )

            self._create_message_log(
                record, phone_number, params, success, response_data
            )

            return {
                "success": success,
                "phone": phone_number,
                "response": response_data,
                "params": params,
            }

        except Exception as e:
            _logger.error("Error enviando plantilla WhatsApp: %s", str(e))
            return {
                "success": False,
                "error": str(e),
                "phone": phone,
                "params": custom_params,
            }

    def _get_phone_from_record(self, record):
        """Obtener número de teléfono del registro"""
        phone = None
        partner = None
        if hasattr(record, "partner_id") and record.partner_id:
            partner = record.partner_id
        elif record._name == "res.partner":
            partner = record

        if partner:
            field_name = self.phone_field
            phone = getattr(partner, field_name, None)

        return self._format_phone(phone) if phone else None

    def _format_phone(self, phone):
        """Formatear número de teléfono usando configuración"""
        if not phone:
            return None
        country_code = self.config_id.default_country_code or "57"
        clean_phone = (
            phone.replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
            .replace("+", "")
        )
        if not clean_phone.startswith(country_code) and len(clean_phone) == 10:
            clean_phone = country_code + clean_phone

        return clean_phone

    def _get_template_params(self, record):
        """Obtener parámetros procesados para el registro"""
        params = []

        for param in self.param_ids.sorted("sequence"):
            if param.active:
                value = param.get_field_value(record)
                params.append(value)

        return params

    def _send_whatsapp_message(self, phone, params):
        """Enviar mensaje vía API usando configuración"""
        headers = self.config_id._get_api_headers()
        bot_id = self.config_id.bot_id
        platform_id = self.config_id.platform_id

        data = {
            "args": {
                "phone": phone,
                "id_template": self.template_id_api,
                "name_template": self.template_name,
                "id_bot": bot_id,
                "params": params,
            }
        }
        if platform_id:
            data["args"]["id_platform"] = platform_id

        try:
            _logger.info("Enviando WhatsApp a %s con plantilla %s", phone, self.name)

            response = requests.post(
                self.config_id.api_url,
                json=data,
                headers=headers,
                timeout=self.config_id.timeout,
            )

            _logger.info(
                "Respuesta API WhatsApp: %s - %s", response.status_code, response.text
            )

            success = response.status_code in [200, 201]
            response_data = {
                "status_code": response.status_code,
                "response_text": response.text,
                "request_data": data,
            }

            return success, response_data

        except requests.exceptions.Timeout:
            _logger.error("Timeout enviando WhatsApp")
            return False, {"error": "Timeout de conexión"}

        except requests.exceptions.RequestException as e:
            _logger.error("Error de conexión WhatsApp: %s", str(e))
            return False, {"error": f"Error de conexión: {str(e)}"}

        except Exception as e:
            _logger.error("Error inesperado WhatsApp: %s", str(e))
            return False, {"error": f"Error inesperado: {str(e)}"}

    def _create_message_log(self, record, phone, params, success, response_data):
        """Crear registro en el log de mensajes"""
        partner_id = None
        if hasattr(record, "partner_id") and record.partner_id:
            partner_id = record.partner_id.id
        elif record._name == "res.partner":
            partner_id = record.id

        log_vals = {
            "template_id": self.id,
            "partner_id": partner_id,
            "phone": phone,
            "status": "sent" if success else "failed",
            "params_data": json.dumps(params),
            "response_data": json.dumps(response_data),
            "sent_date": fields.Datetime.now(),
            "user_id": self.env.user.id,
            "api_response_code": response_data.get("status_code", 0),
            "company_id": self.company_id.id,
        }
        if record._name == "crm.lead":
            log_vals["lead_id"] = record.id

        return self.env["whatsapp.asertis.message.log"].create(log_vals)

    @api.model
    def get_templates_for_model(self, model_name):
        """Obtener plantillas disponibles para un modelo específico"""
        model_id = (
            self.sudo().env["ir.model"].search([("model", "=", model_name)], limit=1)
        )
        if not model_id:
            return self.browse()

        return self.search(
            [
                ("model_id", "=", model_id.id),
                ("active", "=", True),
                ("company_id", "=", self.env.company.id),
            ]
        )

    def action_duplicate_template(self):
        """Duplicar plantilla"""
        self.ensure_one()

        copy_vals = {
            "name": _("%s (Copia)") % self.name,
            "template_name": "%s_copy" % self.template_name,
            "template_id_api": "%s_copy" % self.template_id_api,
        }

        new_template = self.copy(copy_vals)

        return {
            "type": "ir.actions.act_window",
            "name": _("Plantilla Duplicada"),
            "view_mode": "form",
            "res_model": "whatsapp.asertis.template",
            "res_id": new_template.id,
            "target": "current",
        }

    def generate_preview(self):
        """Generar vista previa manual"""
        self.ensure_one()
        self._compute_preview_text()
        return True
