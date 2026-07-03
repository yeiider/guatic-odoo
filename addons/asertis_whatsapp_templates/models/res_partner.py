from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"
    whatsapp_opt_out = fields.Boolean(
        string="Excluido de WhatsApp",
        default=False,
        help="Si está marcado, no se enviarán mensajes WhatsApp a este contacto",
    )

    whatsapp_phone = fields.Char(
        string="WhatsApp", help="Número de teléfono específico para WhatsApp"
    )

    preferred_phone_whatsapp = fields.Selection(
        [
            ("phone", "Teléfono"),
            ("mobile", "Celular"),
            ("whatsapp_phone", "WhatsApp específico"),
        ],
        string="Teléfono Preferido WhatsApp",
        default="mobile",
        help="Campo de teléfono preferido para mensajes WhatsApp",
    )
    whatsapp_count = fields.Integer(
        string="Mensajes WhatsApp",
        compute="_compute_whatsapp_count",
        help="Cantidad de mensajes WhatsApp enviados a este contacto",
    )

    last_whatsapp_sent = fields.Datetime(
        string="Último WhatsApp",
        compute="_compute_whatsapp_count",
        help="Fecha del último mensaje WhatsApp enviado",
    )

    whatsapp_log_ids = fields.One2many(
        "whatsapp.asertis.message.log",
        "partner_id",
        string="Historial WhatsApp",
        help="Historial de mensajes WhatsApp",
    )
    has_valid_whatsapp = fields.Boolean(
        string="WhatsApp Válido",
        compute="_compute_whatsapp_info",
        help="True si tiene un número válido para WhatsApp",
    )
    formatted_whatsapp_phone = fields.Char(
        string="Teléfono WhatsApp Formateado",
        compute="_compute_whatsapp_info",
        help="Número formateado para WhatsApp",
    )
    whatsapp_url = fields.Char(
        string="URL WhatsApp",
        compute="_compute_whatsapp_url",
        help="URL para abrir chat directo en WhatsApp",
    )
    whatsapp_country_code = fields.Char(
        string="Código País WhatsApp",
        default="57",
        help="Código de país para WhatsApp (por defecto 57 - Colombia)",
    )

    @api.depends("phone", "mobile", "whatsapp_phone", "preferred_phone_whatsapp")
    def _compute_whatsapp_info(self):
        """Computar información de WhatsApp"""
        for partner in self:
            phone = partner.get_whatsapp_phone()
            partner.has_valid_whatsapp = bool(phone)
            partner.formatted_whatsapp_phone = phone

    @api.depends("formatted_whatsapp_phone")
    def _compute_whatsapp_url(self):
        """Generar URL de WhatsApp"""
        for partner in self:
            if partner.formatted_whatsapp_phone:
                partner.whatsapp_url = (
                    f"https://wa.me/{partner.formatted_whatsapp_phone}"
                )
            else:
                partner.whatsapp_url = False

    @api.depends("whatsapp_log_ids", "whatsapp_log_ids.sent_date")
    def _compute_whatsapp_count(self):
        """Contar mensajes WhatsApp"""
        for partner in self:
            logs = partner.whatsapp_log_ids
            partner.whatsapp_count = len(logs)

            if logs:
                partner.last_whatsapp_sent = max(logs.mapped("sent_date"))
            else:
                partner.last_whatsapp_sent = False

    def get_whatsapp_phone(self):
        """Obtener número de teléfono para WhatsApp"""
        self.ensure_one()
        phone_field = self.preferred_phone_whatsapp or "mobile"
        phone = getattr(self, phone_field, None)
        if not phone:
            for field in ["mobile", "phone", "whatsapp_phone"]:
                phone = getattr(self, field, None)
                if phone:
                    break

        return self.format_phone_international(phone) if phone else None

    def format_phone_international(self, phone):
        """Formatear teléfono a formato internacional"""
        if not phone:
            return None
        clean_phone = re.sub(r"[^\d+]", "", str(phone))
        if clean_phone.startswith("+"):
            clean_phone = clean_phone[1:]

        country_code = self.whatsapp_country_code or "57"
        if clean_phone.startswith(country_code):
            return clean_phone
        if len(clean_phone) == 10 and country_code == "57":
            return country_code + clean_phone
        if len(clean_phone) >= 10:
            return clean_phone

        return None

    @api.constrains("whatsapp_phone")
    def _check_whatsapp_phone_format(self):
        """Validar formato de teléfono WhatsApp"""
        for partner in self:
            if partner.whatsapp_phone:
                formatted = partner.format_phone_international(partner.whatsapp_phone)
                if not formatted:
                    raise ValidationError(
                        _("El formato del teléfono WhatsApp no es válido")
                    )

    def action_send_whatsapp(self):
        """Enviar mensaje WhatsApp"""
        self.ensure_one()

        if self.whatsapp_opt_out:
            raise UserError(_("Este contacto está excluido de mensajes WhatsApp"))

        if not self.has_valid_whatsapp:
            raise UserError(_("No hay número de teléfono válido para WhatsApp"))
        model_id = self.sudo().env["ir.model"].search([("model", "=", "res.partner")], limit=1)

        templates = (
            self.env["whatsapp.asertis.template"].search(
                [
                    ("model_id", "=", model_id.id),
                    ("active", "=", True),
                    ("company_id", "=", self.company_id.id or self.env.company.id),
                ]
            )
            if model_id
            else self.env["whatsapp.asertis.template"].browse()
        )
        if not templates:
            raise UserError(_("No hay plantillas WhatsApp disponibles para contactos"))

        return {
            "type": "ir.actions.act_window",
            "name": _("Enviar WhatsApp"),
            "view_mode": "form",
            "res_model": "whatsapp.asertis.template.send.wizard",
            "target": "new",
            "context": {
                "default_partner_id": self.id,
                "default_phone": self.formatted_whatsapp_phone,
                "available_templates": templates.ids,
            },
        }

    def action_open_whatsapp_web(self):
        """Abrir WhatsApp Web"""
        self.ensure_one()

        if not self.has_valid_whatsapp:
            raise UserError(_("No hay número de teléfono válido para WhatsApp"))

        url = self.whatsapp_url
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def action_view_whatsapp_history(self):
        """Ver historial de mensajes WhatsApp"""
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": _("Historial WhatsApp - %s") % self.name,
            "view_mode": "tree,form",
            "res_model": "whatsapp.asertis.message.log",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
            "target": "current",
        }

    def action_toggle_whatsapp_opt_out(self):
        """Alternar exclusión de WhatsApp"""
        for partner in self:
            partner.whatsapp_opt_out = not partner.whatsapp_opt_out
            if hasattr(partner, "activity_schedule"):
                activity_type = self.env.ref(
                    "mail.mail_activity_data_todo", raise_if_not_found=False
                )
                if activity_type:
                    status = (
                        "excluido de" if partner.whatsapp_opt_out else "incluido en"
                    )
                    partner.activity_schedule(
                        activity_type_id=activity_type.id,
                        summary=f"Contacto {status} mensajes WhatsApp",
                        note=f"El contacto {partner.name} ha sido {status} mensajes WhatsApp",
                        user_id=self.env.user.id,
                    )

    def action_validate_whatsapp_phone(self):
        """Validar y limpiar número de WhatsApp"""
        for partner in self:
            for field_name in ["phone", "mobile", "whatsapp_phone"]:
                phone_value = getattr(partner, field_name, None)
                if phone_value:
                    formatted = partner.format_phone_international(phone_value)
                    if formatted and formatted != phone_value:
                        setattr(partner, field_name, formatted)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Teléfonos Validados"),
                "message": _(
                    "Los números de teléfono han sido validados y formateados"
                ),
                "type": "success",
            },
        }

    def get_whatsapp_context_variables(self):
        """Obtener variables de contexto para plantillas"""
        self.ensure_one()

        variables = {
            "name": self.name or "",
            "email": self.email or "",
            "phone": self.phone or "",
            "mobile": self.mobile or "",
            "whatsapp_phone": self.whatsapp_phone or "",
            "street": self.street or "",
            "street2": self.street2 or "",
            "city": self.city or "",
            "state": self.state_id.name if self.state_id else "",
            "country": self.country_id.name if self.country_id else "",
            "zip": self.zip or "",
            "is_company": self.is_company,
            "vat": self.vat or "",
            "website": self.website or "",
            "category_names": (
                ", ".join(self.category_id.mapped("name")) if self.category_id else ""
            ),
            "parent_name": self.parent_id.name if self.parent_id else "",
            "commercial_partner_name": (
                self.commercial_partner_id.name if self.commercial_partner_id else ""
            ),
            "user_name": self.user_id.name if self.user_id else "",
            "user_email": self.user_id.email if self.user_id else "",
            "create_date": (
                self.create_date.strftime("%d/%m/%Y") if self.create_date else ""
            ),
            "write_date": (
                self.write_date.strftime("%d/%m/%Y") if self.write_date else ""
            ),
        }

        return variables

    @api.model
    def find_partners_for_whatsapp_bulk(self, domain=None):
        """Encontrar contactos válidos para envío masivo"""
        base_domain = [
            ("whatsapp_opt_out", "=", False),
            ("has_valid_whatsapp", "=", True),
        ]

        if domain:
            base_domain.extend(domain)

        return self.search(base_domain)

    @api.model
    def send_whatsapp_bulk(self, partner_ids, template_id):
        """Envío masivo de WhatsApp a múltiples contactos"""
        partners = self.browse(partner_ids)
        template = self.env["whatsapp.asertis.template"].browse(template_id)

        if not template.exists():
            raise UserError(_("La plantilla no existe"))

        results = {"success": 0, "failed": 0, "skipped": 0, "details": []}

        for partner in partners:
            try:
                if partner.whatsapp_opt_out:
                    results["skipped"] += 1
                    results["details"].append(
                        {
                            "partner": partner.name,
                            "status": "skipped",
                            "reason": "Excluido de WhatsApp",
                        }
                    )
                    continue
                result = template.send_template(
                    partner.id, phone=partner.whatsapp_phone
                )
                if result["success"]:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["details"].append(
                        {
                            "partner": partner.name,
                            "status": "failed",
                            "reason": result["error"],
                        }
                    )
            except Exception as e:
                _logger.error("Error al enviar WhatsApp a %s: %s", partner.name, e)
                results["failed"] += 1
                results["details"].append(
                    {"partner": partner.name, "status": "failed", "reason": str(e)}
                )

        return results
