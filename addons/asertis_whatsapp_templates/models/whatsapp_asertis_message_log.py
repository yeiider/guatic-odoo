# models/whatsapp_message_log.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class WhatsappMessageLog(models.Model):
    _name = "whatsapp.asertis.message.log"
    _description = "Historial de Mensajes WhatsApp"
    _order = "sent_date desc"
    _rec_name = "display_name"

    template_id = fields.Many2one(
        "whatsapp.asertis.template",
        string="Plantilla Utilizada",
        required=True,
        ondelete="cascade",
        help="Plantilla que se utilizó para el envío",
    )
    partner_id = fields.Many2one(
        "res.partner", string="Contacto", help="Contacto al que se envió el mensaje"
    )

    lead_id = fields.Many2one(
        "crm.lead", string="Lead/Oportunidad", help="Lead u oportunidad relacionada"
    )
    user_id = fields.Many2one(
        "res.users",
        string="Usuario",
        required=True,
        default=lambda self: self.env.user,
        help="Usuario que envió el mensaje",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
        help="Compañía desde la que se envió",
    )

    phone = fields.Char(
        string="Teléfono", required=True, help="Número de teléfono al que se envió"
    )
    sent_date = fields.Datetime(
        string="Fecha de Envío",
        required=True,
        default=fields.Datetime.now,
        help="Fecha y hora del envío",
    )
    status = fields.Selection(
        [
            ("sent", "Enviado"),
            ("failed", "Fallido"),
            ("pending", "Pendiente"),
            ("retry", "Reintentando"),
        ],
        string="Estado",
        required=True,
        default="pending",
        help="Estado del envío del mensaje",
    )
    template_name = fields.Char(
        string="Nombre de Plantilla",
        related="template_id.template_name",
        store=True,
        help="Nombre de la plantilla utilizada",
    )
    template_type = fields.Selection(
        related="template_id.template_type", store=True, string="Tipo de Plantilla"
    )
    params_data = fields.Text(
        string="Parámetros Enviados",
        help="Parámetros enviados a la plantilla (formato JSON)",
    )
    response_data = fields.Text(
        string="Respuesta API", help="Respuesta completa de la API (formato JSON)"
    )

    error_message = fields.Text(
        string="Mensaje de Error", help="Mensaje de error en caso de fallo"
    )
    retry_count = fields.Integer(
        string="Intentos", default=0, help="Número de intentos de envío realizados"
    )
    api_response_code = fields.Integer(
        string="Código de Respuesta", help="Código HTTP de respuesta de la API"
    )
    processing_time = fields.Float(
        string="Tiempo de Procesamiento (ms)",
        help="Tiempo que tomó procesar el envío en milisegundos",
    )
    display_name = fields.Char(
        string="Nombre", compute="_compute_display_name", store=True
    )
    params_display = fields.Text(
        string="Parámetros",
        compute="_compute_params_display",
        help="Visualización amigable de los parámetros",
    )
    status_color = fields.Integer(
        string="Color de Estado",
        compute="_compute_status_color",
        help="Color para mostrar en vistas kanban",
    )
    days_since_sent = fields.Integer(
        string="Días desde Envío",
        compute="_compute_days_since_sent",
        help="Días transcurridos desde el envío",
    )
    read_date = fields.Datetime(
        string="Fecha de Lectura",
        help="Fecha cuando el mensaje fue leído (si disponible)",
    )
    delivered_date = fields.Datetime(
        string="Fecha de Entrega",
        help="Fecha cuando el mensaje fue entregado (si disponible)",
    )

    @api.depends("template_id", "partner_id", "phone", "sent_date")
    def _compute_display_name(self):
        """Computar nombre de visualización"""
        for log in self:
            parts = []

            if log.template_id:
                parts.append(log.template_id.name)

            if log.partner_id:
                parts.append(f"→ {log.partner_id.name}")
            elif log.phone:
                parts.append(f"→ {log.phone}")

            if log.sent_date:
                date_str = log.sent_date.strftime("%d/%m/%Y %H:%M")
                parts.append(f"({date_str})")

            log.display_name = " ".join(parts) or "Mensaje WhatsApp"

    @api.depends("params_data")
    def _compute_params_display(self):
        """Mostrar parámetros de forma legible"""
        for log in self:
            if not log.params_data:
                log.params_display = "Sin parámetros"
                continue

            try:
                params = json.loads(log.params_data)
                if isinstance(params, list):
                    display_parts = []
                    for i, param in enumerate(params, 1):
                        display_parts.append(f"Parámetro {i}: {param}")
                    log.params_display = "\n".join(display_parts)
                else:
                    log.params_display = str(params)
            except:
                log.params_display = log.params_data

    @api.depends("status")
    def _compute_status_color(self):
        """Asignar color según estado"""
        color_map = {
            "sent": 10,  # Verde
            "failed": 1,  # Rojo
            "pending": 4,  # Azul
            "retry": 3,  # Amarillo
        }

        for log in self:
            log.status_color = color_map.get(log.status, 0)

    @api.depends("sent_date")
    def _compute_days_since_sent(self):
        """Calcular días desde envío"""
        now = fields.Datetime.now()
        for log in self:
            if log.sent_date:
                delta = now - log.sent_date
                log.days_since_sent = delta.days
            else:
                log.days_since_sent = 0

    def action_retry_send(self):
        """Reintentar envío del mensaje"""
        self.ensure_one()

        if self.status == "sent":
            raise UserError(_("No se puede reintentar un mensaje ya enviado"))

        if not self.template_id or not self.template_id.active:
            raise UserError(_("La plantilla no está disponible"))

        try:
            params = json.loads(self.params_data) if self.params_data else []
            start_time = datetime.now()
            success, response_data = self.template_id._send_whatsapp_message(
                self.phone, params
            )
            end_time = datetime.now()
            json_response_data = json.dumps(response_data)
            message = (
                _("✅ Mensaje reenviado exitosamente")
                if success
                else _("❌ Fallo al reenviar mensaje")
            )
            message_type = "success" if success else "danger"
            self.write(
                {
                    "status": "sent" if success else "failed",
                    "retry_count": self.retry_count + 1,
                    "response_data": json_response_data,
                    "processing_time": (end_time - start_time).total_seconds() * 1000,
                    "api_response_code": (
                        response_data.status_code
                        if hasattr(response_data, "status_code")
                        else 0
                    ),
                    "error_message": message,
                }
            )

        except Exception as e:
            self.write(
                {
                    "status": "failed",
                    "retry_count": self.retry_count + 1,
                    "error_message": str(e),
                }
            )
            message = _("❌ Error al reintentar: %s") % str(e)
            message_type = "danger"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Reintento de Envío"),
                "message": message,
                "type": message_type,
                "sticky": True,
            },
        }

    def action_view_template(self):
        """Ver plantilla utilizada"""
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": _("Plantilla Utilizada"),
            "view_mode": "form",
            "res_model": "whatsapp.asertis.template",
            "res_id": self.template_id.id,
            "target": "current",
        }

    def action_view_partner(self):
        """Ver contacto relacionado"""
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("No hay contacto relacionado"))

        return {
            "type": "ir.actions.act_window",
            "name": _("Contacto"),
            "view_mode": "form",
            "res_model": "res.partner",
            "res_id": self.partner_id.id,
            "target": "current",
        }

    def action_view_lead(self):
        """Ver lead/oportunidad relacionada"""
        self.ensure_one()

        if not self.lead_id:
            raise UserError(_("No hay lead/oportunidad relacionada"))

        return {
            "type": "ir.actions.act_window",
            "name": _("Lead/Oportunidad"),
            "view_mode": "form",
            "res_model": "crm.lead",
            "res_id": self.lead_id.id,
            "target": "current",
        }

    def action_show_details(self):
        """Mostrar detalles completos del envío"""
        self.ensure_one()
        details = []
        details.append(f"📱 Teléfono: {self.phone}")
        details.append(f"📋 Plantilla: {self.template_name}")
        details.append(f"📅 Fecha: {self.sent_date.strftime('%d/%m/%Y %I:%M %p')}")
        details.append(f"👤 Usuario: {self.user_id.name}")

        if self.retry_count > 0:
            details.append(f"🔁 Intentos: {self.retry_count}")

        if self.processing_time:
            details.append(f"⏱️ Tiempo: {self.processing_time:.0f}ms")

        if self.api_response_code:
            details.append(f"📊 Código HTTP: {self.api_response_code}")

        details_text = "\n".join(details)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Detalles del Mensaje"),
                "message": details_text,
                "type": "info",
                "sticky": True,
            },
        }

    @api.model
    def cleanup_old_logs(self, days=90):
        """Limpiar logs antiguos (para ejecutar via cron)"""
        cutoff_date = fields.Datetime.now() - timedelta(days=days)
        old_logs = self.search([("sent_date", "<", cutoff_date)])

        if old_logs:
            count = len(old_logs)
            old_logs.unlink()
            _logger.info(
                "Eliminados %d logs de WhatsApp anteriores a %s", count, cutoff_date
            )

        return True

    @api.model
    def get_statistics(self, date_from=None, date_to=None):
        """Obtener estadísticas de envíos"""
        domain = []

        if date_from:
            domain.append(("sent_date", ">=", date_from))
        if date_to:
            domain.append(("sent_date", "<=", date_to))

        logs = self.search(domain)

        total = len(logs)
        if not total:
            return {
                "total": 0,
                "sent": 0,
                "failed": 0,
                "success_rate": 0,
                "by_template": {},
                "by_user": {},
                "by_day": {},
            }

        sent = len(logs.filtered(lambda l: l.status == "sent"))
        failed = len(logs.filtered(lambda l: l.status == "failed"))
        success_rate = (sent / total) * 100 if total > 0 else 0

        by_day = {}
        for log in logs:
            day = log.sent_date.date().strftime("%Y-%m-%d")
            if day not in by_day:
                by_day[day] = {"total": 0, "sent": 0}
            by_day[day]["total"] += 1
            if log.status == "sent":
                by_day[day]["sent"] += 1
        by_template = {
            t.name: len(logs.filtered(lambda l: l.template_id == t))
            for t in logs.mapped("template_id")
        }
        by_user = {
            u.name: len(logs.filtered(lambda l: l.user_id == u))
            for u in logs.mapped("user_id")
        }
        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "success_rate": success_rate,
            "by_template": by_template,
            "by_user": by_user,
            "by_day": by_day,
        }

    @api.model
    def create_from_template_send(
        self, template_id, record_id, phone, params, success, response_data
    ):
        """
        Crear log desde envío de plantilla

        Args:
            template_id: ID de la plantilla
            record_id: ID del registro origen
            phone: Número de teléfono
            params: Lista de parámetros enviados
            success: True/False si fue exitoso
            response_data: Respuesta de la API
        """
        template = self.env["whatsapp.asertis.template"].browse(template_id)
        partner_id = None
        lead_id = None

        if template.model_id.model == "crm.lead":
            lead = self.env["crm.lead"].browse(record_id)
            lead_id = lead.id
            partner_id = lead.partner_id.id if lead.partner_id else None
        elif template.model_id.model == "res.partner":
            partner_id = record_id
        else:
            record = self.env[template.model_id.model].browse(record_id)
            partner = getattr(record, "partner_id", None)
            if partner is not None:
                partner_id = partner.id

        log_vals = {
            "template_id": template_id,
            "partner_id": partner_id,
            "lead_id": lead_id,
            "phone": phone,
            "status": "sent" if success else "failed",
            "params_data": json.dumps(params) if params else "[]",
            "response_data": response_data if response_data else "{}",
            "api_response_code": (
                response_data.status_code
                if hasattr(response_data, "status_code")
                else 0
            ),
            "error_message": (
                response_data.error
                if not success and hasattr(response_data, "error")
                else ""
            ),
            "sent_date": fields.Datetime.now().strftime("%d/%m/%Y %I:%M %p"),
            "user_id": self.env.user.id,
            "company_id": self.env.company.id,
        }

        return self.create(log_vals)

    @api.model
    def auto_retry_failed_messages(self):
        """Reintentar mensajes fallidos automáticamente (para cron)"""
        yesterday = fields.Datetime.now() - timedelta(hours=24)

        failed_logs = self.search(
            [
                ("status", "=", "failed"),
                ("sent_date", ">=", yesterday),
                ("retry_count", "<", 3),
            ]
        )

        retried_count = 0
        success_count = 0

        for log in failed_logs:
            try:
                import time

                time.sleep(1)

                log.action_retry_send()
                retried_count += 1

                if log.status == "sent":
                    success_count += 1

            except Exception as e:
                _logger.error(
                    "Error en reintento automático para log %s: %s", log.id, str(e)
                )
                continue

        _logger.info(
            "Reintento automático completado: %d mensajes procesados, %d exitosos",
            retried_count,
            success_count,
        )

        return {"retried": retried_count, "success": success_count}

    def mark_as_delivered(self, external_id=None):
        """Marcar mensaje como entregado (webhook callback)"""
        self.ensure_one()

        self.delivered_date = fields.Datetime.now()
        if self.lead_id:
            self.lead_id.message_post(
                body=_("📱 Mensaje WhatsApp entregado exitosamente"),
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

    def mark_as_read(self, external_id=None):
        """Marcar mensaje como leído (webhook callback)"""
        self.ensure_one()

        self.read_date = fields.Datetime.now().strftime("%d/%m/%Y %I:%M %p")
        if self.lead_id:
            self.lead_id.message_post(
                body=_("👁️ Mensaje WhatsApp leído por el destinatario"),
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

    def name_get(self):
        """Nombre personalizado para el log"""
        result = []
        for log in self:
            name_parts = []
            status_emoji = {
                "sent": "✅",
                "failed": "❌",
                "pending": "⏳",
                "retry": "🔄",
            }
            name_parts.append(status_emoji.get(log.status, "❓"))
            if log.template_name:
                name_parts.append(log.template_name)

            if log.partner_id:
                name_parts.append(f"→ {log.partner_id.name}")
            else:
                name_parts.append(f"→ {log.phone}")
            if log.sent_date:
                date_str = log.sent_date.strftime("%d/%m %H:%M")
                name_parts.append(f"({date_str})")

            name = " ".join(name_parts)
            result.append((log.id, name))

        return result
