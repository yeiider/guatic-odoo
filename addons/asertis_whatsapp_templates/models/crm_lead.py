# models/crm_lead.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"
    _description = "Lead/Opportunity"
    whatsapp_template_ids = fields.Many2many(
        "whatsapp.asertis.template",
        "crm_lead_whatsapp_template_rel",
        "lead_id",
        "template_id",
        string="Plantillas WhatsApp Disponibles",
        compute="_compute_whatsapp_templates",
        help="Plantillas de WhatsApp disponibles para este lead",
    )

    last_whatsapp_sent = fields.Datetime(
        string="Último WhatsApp Enviado",
        help="Fecha del último mensaje WhatsApp enviado",
    )

    whatsapp_count = fields.Integer(
        string="Mensajes WhatsApp",
        compute="_compute_whatsapp_count",
        help="Cantidad total de mensajes WhatsApp enviados",
    )

    whatsapp_log_ids = fields.One2many(
        "whatsapp.asertis.message.log",
        "lead_id",
        string="Historial WhatsApp",
        help="Historial de mensajes WhatsApp enviados",
    )
    has_whatsapp_phone = fields.Boolean(
        string="Tiene WhatsApp",
        compute="_compute_has_whatsapp_phone",
        help="True si tiene un número de teléfono válido para WhatsApp",
    )
    whatsapp_phone = fields.Char(
        string="Teléfono WhatsApp",
        compute="_compute_whatsapp_phone",
        help="Número de teléfono formateado para WhatsApp",
    )
    whatsapp_opt_out = fields.Boolean(
        string="Excluido de WhatsApp",
        default=False,
        help="Si está marcado, no se enviarán mensajes WhatsApp a este lead",
    )
    preferred_phone_type = fields.Selection(
        [
            ("phone", "Teléfono"),
            ("mobile", "Celular"),
        ],
        string="Tipo de Teléfono Preferido",
        default="mobile",
        help="Tipo de teléfono preferido para WhatsApp",
    )

    @api.depends("partner_id", "partner_id.phone", "partner_id.mobile")
    def _compute_has_whatsapp_phone(self):
        """Verificar si tiene teléfono válido para WhatsApp"""
        for lead in self:
            phone = lead._get_whatsapp_phone_number()
            lead.has_whatsapp_phone = bool(phone)

    @api.depends(
        "partner_id", "partner_id.phone", "partner_id.mobile", "preferred_phone_type"
    )
    def _compute_whatsapp_phone(self):
        """Obtener número de teléfono formateado para WhatsApp"""
        for lead in self:
            phone = lead._get_whatsapp_phone_number()
            lead.whatsapp_phone = phone

    @api.depends("whatsapp_log_ids")
    def _compute_whatsapp_count(self):
        """Contar mensajes WhatsApp enviados"""
        for lead in self:
            lead.whatsapp_count = len(lead.whatsapp_log_ids)

            if lead.whatsapp_log_ids:
                last_log = lead.whatsapp_log_ids.sorted("sent_date", reverse=True)[0]
                lead.last_whatsapp_sent = last_log.sent_date

    def _compute_whatsapp_templates(self):
        """Obtener plantillas disponibles para este lead"""
        for lead in self:
            model_id = self.sudo().env["ir.model"].search(
                [("model", "=", "crm.lead")], limit=1
            )
            if model_id:
                templates = self.env["whatsapp.asertis.template"].search(
                    [
                        ("model_id", "=", model_id.id),
                        ("active", "=", True),
                        ("company_id", "=", lead.company_id.id),
                    ]
                )
                lead.whatsapp_template_ids = templates
            else:
                lead.whatsapp_template_ids = self.env["whatsapp.asertis.template"]

    def _get_whatsapp_phone_number(self):
        """Obtener número de teléfono para WhatsApp"""
        self.ensure_one()

        if not self.partner_id:
            return None
        phone_type = self.preferred_phone_type or "mobile"
        phone = getattr(self.partner_id, phone_type, None)
        if not phone:
            other_type = "phone" if phone_type == "mobile" else "mobile"
            phone = getattr(self.partner_id, other_type, None)

        return self._format_whatsapp_phone(phone) if phone else None

    def _format_whatsapp_phone(self, phone):
        """Formatear número de teléfono para WhatsApp"""
        if not phone:
            return None
        clean_phone = (
            phone.replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
            .replace("+", "")
        )
        if not clean_phone.startswith("57") and len(clean_phone) == 10:
            clean_phone = "57" + clean_phone

        return clean_phone

    def action_send_whatsapp(self):
        """Abrir wizard para enviar WhatsApp"""
        self.ensure_one()

        if self.whatsapp_opt_out:
            raise UserError(_("Este contacto está excluido de mensajes WhatsApp"))

        if not self.has_whatsapp_phone:
            raise UserError(_("No hay número de teléfono válido para WhatsApp"))
        if not self.whatsapp_template_ids:
            raise UserError(
                _("No hay plantillas WhatsApp disponibles para este modelo")
            )

        return {
            "type": "ir.actions.act_window",
            "name": _("Enviar WhatsApp"),
            "view_mode": "form",
            "res_model": "whatsapp.asertis.template.send.wizard",
            "target": "new",
            "context": {
                "default_lead_id": self.id,
                "default_partner_id": self.partner_id.id if self.partner_id else False,
                "default_phone": self.whatsapp_phone,
                "available_templates": self.whatsapp_template_ids.ids,
            },
        }

    def action_open_whatsapp_multi_wizard(self):
        """Abrir wizard para envío múltiple de plantillas WhatsApp"""
        return {
            "name": _("Enviar Plantilla WhatsApp"),
            "type": "ir.actions.act_window",
            "res_model": "whatsapp.asertis.template.multi.send.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": self._name,
                "active_ids": self.ids,
            },
        }

    def action_send_whatsapp_template(self, template_id):
        """Enviar mensaje con plantilla específica (para uso en botones/menús)"""
        self.ensure_one()

        if self.whatsapp_opt_out:
            raise UserError(_("Este contacto está excluido de mensajes WhatsApp"))

        template = self.env["whatsapp.asertis.template"].browse(template_id)
        if not template.exists():
            raise UserError(_("La plantilla no existe"))

        if not template.active:
            raise UserError(_("La plantilla no está activa"))
        result = template.send_template(self.id, phone=self.whatsapp_phone)

        if result["success"]:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("WhatsApp Enviado"),
                    "message": _("Mensaje enviado exitosamente al teléfono %s")
                    % result["phone"],
                    "type": "success",
                    "sticky": False,
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error al Enviar"),
                    "message": _("No se pudo enviar el mensaje: %s")
                    % result.get("error", "Error desconocido"),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def action_view_whatsapp_history(self):
        """Ver historial de mensajes WhatsApp"""
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": _("Historial WhatsApp - %s") % self.name,
            "view_mode": "tree,form",
            "res_model": "whatsapp.asertis.message.log",
            "domain": [("lead_id", "=", self.id)],
            "context": {
                "default_lead_id": self.id,
                "default_partner_id": self.partner_id.id if self.partner_id else False,
            },
            "target": "current",
        }

    def action_toggle_whatsapp_opt_out(self):
        """Alternar exclusión de WhatsApp"""
        for lead in self:
            lead.whatsapp_opt_out = not lead.whatsapp_opt_out

            status = "excluido de" if lead.whatsapp_opt_out else "incluido en"
            lead.message_post(
                body=_("📱 Lead %s mensajes WhatsApp") % status,
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

    def get_whatsapp_templates_menu(self):
        """Obtener menú dinámico de plantillas para botón WhatsApp"""
        self.ensure_one()

        if not self.has_whatsapp_phone or self.whatsapp_opt_out:
            return []

        menu_items = []
        for template in self.whatsapp_template_ids:
            menu_items.append(
                {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description or "",
                    "template_type": template.template_type,
                }
            )

        return menu_items

    @api.model
    def send_whatsapp_bulk(self, lead_ids, template_id):
        """Envío masivo de WhatsApp a múltiples leads"""
        leads = self.browse(lead_ids)
        template = self.env["whatsapp.asertis.template"].browse(template_id)

        if not template.exists():
            raise UserError(_("La plantilla no existe"))

        results = {"success": 0, "failed": 0, "skipped": 0, "details": []}

        for lead in leads:
            try:
                if lead.whatsapp_opt_out:
                    results["skipped"] += 1
                    results["details"].append(
                        {
                            "lead": lead.name,
                            "status": "skipped",
                            "reason": "Excluido de WhatsApp",
                        }
                    )
                    continue

                if not lead.has_whatsapp_phone:
                    results["skipped"] += 1
                    results["details"].append(
                        {
                            "lead": lead.name,
                            "status": "skipped",
                            "reason": "Sin teléfono válido",
                        }
                    )
                    continue

                result = template.send_template(lead.id)

                if result["success"]:
                    results["success"] += 1
                    results["details"].append(
                        {
                            "lead": lead.name,
                            "status": "success",
                            "phone": result["phone"],
                        }
                    )
                else:
                    results["failed"] += 1
                    results["details"].append(
                        {
                            "lead": lead.name,
                            "status": "failed",
                            "reason": result.get("error", "Error desconocido"),
                        }
                    )

            except Exception as e:
                results["failed"] += 1
                results["details"].append(
                    {"lead": lead.name, "status": "failed", "reason": str(e)}
                )
                _logger.error("Error en envío masivo para lead %s: %s", lead.id, str(e))

        return results

    def _get_whatsapp_context_variables(self):
        """Obtener variables de contexto para plantillas"""
        self.ensure_one()

        variables = {
            "lead_name": self.name or "",
            "lead_stage": self.stage_id.name if self.stage_id else "",
            "lead_probability": self.probability or 0,
            "expected_revenue": self.expected_revenue or 0,
            "partner_name": self.partner_name or "",
            "partner_email": self.partner_id.email if self.partner_id else "",
            "partner_phone": self.partner_id.phone if self.partner_id else "",
            "partner_mobile": self.partner_id.mobile if self.partner_id else "",
            "user_name": self.user_id.name if self.user_id else "",
            "user_email": self.user_id.email if self.user_id else "",
            "user_phone": self.user_id.phone if self.user_id else "",
            "company_name": self.company_id.name,
            "company_email": self.company_id.email or "",
            "company_phone": self.company_id.phone or "",
            "create_date": (
                self.create_date.strftime("%d/%m/%Y") if self.create_date else ""
            ),
            "write_date": (
                self.write_date.strftime("%d/%m/%Y") if self.write_date else ""
            ),
        }

        return variables

    @api.model
    def get_whatsapp_statistics(self, date_from=None, date_to=None):
        """Obtener estadísticas de WhatsApp para leads"""
        domain = [("whatsapp_count", ">", 0)]

        if date_from:
            domain.append(("last_whatsapp_sent", ">=", date_from))
        if date_to:
            domain.append(("last_whatsapp_sent", "<=", date_to))

        leads_with_whatsapp = self.search(domain)

        stats = {
            "total_leads": len(self.search([])),
            "leads_with_whatsapp": len(leads_with_whatsapp),
            "total_messages": sum(leads_with_whatsapp.mapped("whatsapp_count")),
            "by_stage": {},
            "by_user": {},
        }
        for lead in leads_with_whatsapp:
            stage_name = lead.stage_id.name if lead.stage_id else "Sin etapa"
            if stage_name not in stats["by_stage"]:
                stats["by_stage"][stage_name] = 0
            stats["by_stage"][stage_name] += lead.whatsapp_count

        for lead in leads_with_whatsapp:
            user_name = lead.user_id.name if lead.user_id else "Sin asignar"
            if user_name not in stats["by_user"]:
                stats["by_user"][user_name] = 0
            stats["by_user"][user_name] += lead.whatsapp_count

        return stats
