from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VoipCall(models.Model):
    _inherit = "voip.call"

    calendar_event_ids = fields.One2many(
        "calendar.event", "voip_call_id", string="Citas Agendadas"
    )

    calendar_event_count = fields.Integer(
        string="Número de Citas", compute="_compute_calendar_event_count"
    )

    @api.depends("calendar_event_ids")
    def _compute_calendar_event_count(self):
        for record in self:
            record.calendar_event_count = len(record.calendar_event_ids)

    def action_schedule_appointment(self):
        """Acción para abrir el calendario y crear una cita"""
        self.ensure_one()

        # Preparar el contexto con valores por defecto
        context = {
            "default_user_id": self.env.user.id,
            "default_name": f"Cita telefónica - {self.display_name}",
            "default_voip_call_id": self.id,
            "default_description": f"Cita agendada desde llamada VoIP: {self.display_name}",
        }

        # Si tenemos un contacto de la llamada, agregarlo
        if self.partner_id:
            context.update(
                {
                    "default_partner_ids": [(6, 0, [self.partner_id.id])],
                    "default_name": f"Cita con {self.partner_id.name}",
                }
            )

        # Si tenemos número de teléfono, agregarlo a la descripción
        if hasattr(self, "phone_number") and self.phone_number:
            context["default_description"] += f"\nTeléfono: {self.phone_number}"

        return {
            "type": "ir.actions.act_window",
            "name": _("Agendar Cita"),
            "res_model": "calendar.event",
            "view_mode": "form",
            "target": "new",
            "context": context,
        }

    def action_view_appointments(self):
        """Ver todas las citas relacionadas con esta llamada"""
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": _("Citas Agendadas"),
            "res_model": "calendar.event",
            "view_mode": "tree,form,calendar",
            "domain": [("voip_call_id", "=", self.id)],
            "context": {
                "default_voip_call_id": self.id,
                "default_user_id": self.env.user.id,
            },
        }
