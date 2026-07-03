# models/whatsapp_config.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import logging

_logger = logging.getLogger(__name__)


class WhatsappAsertisConfig(models.Model):
    _name = "whatsapp.asertis.config"
    _description = "Configuración Global de WhatsApp"
    _order = "company_id, name"
    _rec_name = "name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Nombre de Configuración",
        required=True,
        help="Nombre descriptivo de la configuración",
    )

    api_url = fields.Char(
        string="URL de la API",
        required=True,
        default="https://serviciosfenalco.fenalcovalle.com/asertis/webhook/templatewhatsapp",
        help="URL completa de la API intermedia",
    )
    bot_id = fields.Char(
        string="Bot ID ",
        required=True,
        help="ID del bot por defecto para nuevas plantillas",
    )
    platform_id = fields.Char(
        string="Platform ID ",
        required=True,
        default=35,
        help="ID de la plataforma por defecto para nuevas plantillas",
    )
    timeout = fields.Integer(
        string="Timeout (segundos)",
        default=30,
        help="Tiempo límite para conexiones API",
    )
    retry_attempts = fields.Integer(
        string="Intentos de Reintento",
        default=3,
        help="Número de reintentos en caso de fallo",
    )
    retry_delay = fields.Integer(
        string="Retraso entre Reintentos (segundos)",
        default=5,
        help="Tiempo de espera entre reintentos",
    )
    api_headers = fields.Text(
        string="Headers HTTP",
        default='{"Content-Type": "application/json"}',
        help="Headers HTTP adicionales en formato JSON",
    )
    default_country_code = fields.Char(
        string="Código de País por Defecto",
        default="57",
        help="Código de país por defecto (ej: 57 para Colombia)",
    )
    phone_validation = fields.Boolean(
        string="Validar Teléfonos",
        default=True,
        help="Activar validación de formato de números telefónicos",
    )
    enable_logging = fields.Boolean(
        string="Activar Logging",
        default=True,
        help="Registrar todos los envíos en el historial",
    )
    log_requests = fields.Boolean(
        string="Registrar Requests",
        default=False,
        help="Registrar datos de requests enviados (para debug)",
    )
    log_responses = fields.Boolean(
        string="Registrar Responses",
        default=True,
        help="Registrar respuestas de la API",
    )
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está activo, esta configuración estará disponible",
    )
    is_default = fields.Boolean(
        string="Configuración por Defecto",
        default=False,
        help="Usar como configuración por defecto para nuevas plantillas",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
        help="Compañía a la que pertenece esta configuración",
    )
    test_phone = fields.Char(
        string="Teléfono de Prueba", help="Número de teléfono para pruebas de conexión"
    )

    last_test_date = fields.Datetime(
        string="Última Prueba",
        readonly=True,
        help="Fecha de la última prueba de conexión",
    )
    last_test_result = fields.Selection(
        [
            ("success", "Exitoso"),
            ("failed", "Fallido"),
            ("pending", "Pendiente"),
        ],
        string="Resultado Última Prueba",
        readonly=True,
    )
    test_message = fields.Text(
        string="Mensaje de Prueba",
        readonly=True,
        help="Mensaje de la última prueba realizada",
    )
    total_messages_sent = fields.Integer(
        string="Mensajes Enviados",
        compute="_compute_stats",
        store=True,
        help="Total de mensajes enviados con esta configuración",
    )
    success_rate = fields.Float(
        string="Tasa de Éxito (%)",
        compute="_compute_stats",
        store=True,
        help="Porcentaje de mensajes enviados exitosamente",
    )
    _sql_constraints = [
        (
            "timeout_positive",
            "CHECK(timeout > 0)",
            "El timeout debe ser mayor a 0 segundos.",
        ),
        (
            "retry_attempts_positive",
            "CHECK(retry_attempts >= 0)",
            "Los intentos de reintento no pueden ser negativos.",
        ),
        (
            "unique_default_per_company",
            "UNIQUE(company_id, is_default) WHERE is_default = true",
            "Solo puede haber una configuración por defecto por compañía.",
        ),
    ]

    @api.depends("company_id")
    def _compute_stats(self):
        """Calcular estadísticas de uso"""
        for config in self:
            templates = self.env["whatsapp.asertis.template"].search(
                [("config_id", "=", self.id), ("company_id", "=", config.company_id.id)]
            )

            if templates:
                logs = self.env["whatsapp.asertis.message.log"].search(
                    [("template_id", "in", templates.ids)]
                )

                config.total_messages_sent = len(logs)

                if logs:
                    success_logs = logs.filtered(lambda l: l.status == "sent")
                    config.success_rate = (len(success_logs) / len(logs)) * 100
                else:
                    config.success_rate = 0.0
            else:
                config.total_messages_sent = 0
                config.success_rate = 0.0

    @api.constrains("api_headers")
    def _check_api_headers(self):
        """Validar formato JSON de headers"""
        for config in self:
            if config.api_headers:
                try:
                    import json

                    json.loads(config.api_headers)
                except ValueError:
                    raise ValidationError(
                        _("Los headers HTTP deben estar en formato JSON válido")
                    )

    @api.constrains("default_country_code")
    def _check_country_code(self):
        """Validar código de país"""
        for config in self:
            if config.default_country_code:
                if not config.default_country_code.isdigit():
                    raise ValidationError(
                        _("El código de país debe contener solo números")
                    )
                if len(config.default_country_code) > 4:
                    raise ValidationError(
                        _("El código de país no debe exceder 4 dígitos")
                    )

    @api.model
    def get_default_config(self, company_id=None):
        """Obtener configuración por defecto"""
        if not company_id:
            company_id = self.env.company.id
        default_config = self.search(
            [
                ("company_id", "=", company_id),
                ("is_default", "=", True),
                ("active", "=", True),
            ],
            limit=1,
        )

        if default_config:
            return default_config
        return self.search(
            [("company_id", "=", company_id), ("active", "=", True)], limit=1
        )

    def action_test_connection(self):
        """Probar conexión con la API"""
        self.ensure_one()

        if not self.test_phone:
            raise UserError(_("Debe configurar un teléfono de prueba"))

        try:
            test_data = {
                "args": {
                    "phone": self._format_test_phone(),
                    "id_template": "test_template_id",
                    "name_template": "test_template",
                    "id_bot": self.bot_id or "test_bot",
                    "params": ["Prueba de conexión", "Sistema Asertis"],
                }
            }
            headers = self._get_api_headers()
            response = requests.post(
                self.api_url, json=test_data, headers=headers, timeout=self.timeout
            )
            self.last_test_date = fields.Datetime.now()

            if response.status_code in [200, 201]:
                self.last_test_result = "success"
                self.test_message = (
                    f"✅ Conexión exitosa. Respuesta: {response.text[:200]}"
                )
                message_type = "success"
                title = _("Prueba Exitosa")
            else:
                self.last_test_result = "failed"
                self.test_message = (
                    f"❌ Error HTTP {response.status_code}: {response.text[:200]}"
                )
                message_type = "warning"
                title = _("Prueba con Advertencias")

        except requests.exceptions.Timeout:
            self.last_test_result = "failed"
            self.test_message = "❌ Timeout de conexión"
            message_type = "danger"
            title = _("Error de Conexión")

        except requests.exceptions.RequestException as e:
            self.last_test_result = "failed"
            self.test_message = f"❌ Error de conexión: {str(e)}"
            message_type = "danger"
            title = _("Error de Conexión")

        except Exception as e:
            self.last_test_result = "failed"
            self.test_message = f"❌ Error inesperado: {str(e)}"
            message_type = "danger"
            title = _("Error Inesperado")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": self.test_message,
                "type": message_type,
                "sticky": True,
            },
        }

    def _format_test_phone(self):
        """Formatear teléfono de prueba"""
        phone = (
            self.test_phone.replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
            .replace("+", "")
        )
        if not phone.startswith(self.default_country_code) and len(phone) == 10:
            phone = self.default_country_code + phone
        return phone

    def _get_api_headers(self):
        """Obtener headers para API"""
        try:
            import json

            headers = json.loads(self.api_headers) if self.api_headers else {}
        except:
            headers = {}
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        return headers

    def action_set_as_default(self):
        """Establecer como configuración por defecto"""
        self.ensure_one()
        other_defaults = self.search(
            [
                ("company_id", "=", self.company_id.id),
                ("id", "!=", self.id),
                ("is_default", "=", True),
            ]
        )
        other_defaults.write({"is_default": False})
        self.is_default = True
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Configuración Actualizada"),
                "message": _("Esta configuración ahora es la por defecto"),
                "type": "success",
            },
        }

    def action_duplicate_config(self):
        """Duplicar configuración"""
        self.ensure_one()

        copy_vals = {
            "name": _("%s (Copia)") % self.name,
            "is_default": False,
        }
        new_config = self.copy(copy_vals)
        return {
            "type": "ir.actions.act_window",
            "name": _("Configuración Duplicada"),
            "view_mode": "form",
            "res_model": "whatsapp.asertis.config",
            "res_id": new_config.id,
            "target": "current",
        }

    def get_templates_using_config(self):
        """Obtener plantillas que usan esta configuración"""
        self.ensure_one()

        templates = self.env["whatsapp.asertis.template"].search(
            [("config_id", "=", self.id), ("company_id", "=", self.company_id.id)]
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Plantillas que Usan esta Configuración"),
            "view_mode": "list,form",
            "res_model": "whatsapp.asertis.template",
            "domain": [("id", "in", templates.ids)],
            "target": "current",
        }

    @api.model
    def create_default_config(self, company_id=None):
        """Crear configuración por defecto para una compañía"""
        if not company_id:
            company_id = self.env.company.id

        existing = self.search([("company_id", "=", company_id)], limit=1)
        if existing:
            return existing

        company = self.env["res.company"].browse(company_id)
        config_vals = {
            "name": f"Configuración WhatsApp - {company.name}",
            "company_id": company_id,
            "is_default": True,
            "api_url": "https://serviciosfenalco.fenalcovalle.com/asertis/webhook/templatewhatsapp",
            "default_country_code": "57",
            "timeout": 30,
            "retry_attempts": 3,
        }

        return self.create(config_vals)

    def name_get(self):
        """Nombre personalizado que incluya la compañía"""
        result = []
        for config in self:
            name = config.name
            if config.is_default:
                name += " (Por Defecto)"
            if not config.active:
                name += " (Inactivo)"
            result.append((config.id, name))
        return result
