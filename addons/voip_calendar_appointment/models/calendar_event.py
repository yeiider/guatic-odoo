# models/calendar_event.py
from odoo import models, _, api
from odoo.exceptions import UserError
import logging
import requests
import random
from datetime import datetime

_logger = logging.getLogger(__name__)


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def action_send_template_message(self):
        """Enviar mensaje de WhatsApp con template de cita médica"""
        self.ensure_one()

        try:
            # Obtener el teléfono del asistente principal
            phone = self._get_attendee_phone()
            if not phone:
                raise UserError(_("No se encontró teléfono del asistente"))

            # Preparar los parámetros del template
            params = self._prepare_template_params()

            # Enviar el mensaje
            success = self._send_whatsapp_template(phone, params)

            if success:
                # Notificar éxito usando message_post
                self.message_post(
                    body=_("✅ Mensaje de WhatsApp enviado exitosamente al teléfono %s")
                    % phone,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                )
                _logger.info(
                    "Mensaje WhatsApp enviado exitosamente para evento %s", self.id
                )

                # También mostrar notificación tipo toast al usuario actual
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Éxito"),
                        "message": _("Mensaje de WhatsApp enviado correctamente"),
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                # Notificar error usando message_post
                self.message_post(
                    body=_("❌ Error al enviar mensaje de WhatsApp al teléfono %s")
                    % phone,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                )
                _logger.error(
                    "Error al enviar mensaje WhatsApp para evento %s", self.id
                )

                # También mostrar notificación tipo toast de error
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Error"),
                        "message": _("No se pudo enviar el mensaje de WhatsApp"),
                        "type": "danger",
                        "sticky": True,
                    },
                }

        except Exception as e:
            _logger.error("Error en envío de WhatsApp: %s", str(e))
            # Notificar error en el chatter
            self.message_post(
                body=_("❌ Error inesperado al enviar WhatsApp: %s") % str(e),
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )
            # Mostrar notificación de error
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Error"),
                    "message": _("Error inesperado: %s") % str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def _get_attendee_phone(self):
        """Obtener el teléfono del primer asistente"""
        if not self.attendee_ids:
            return None

        # Buscar teléfono en el partner del asistente
        for attendee in self.attendee_ids:
            partner = attendee.partner_id
            if partner and partner.phone:
                # Limpiar el teléfono (remover espacios, guiones, paréntesis y el signo +)
                phone = (
                    partner.phone.replace(" ", "")
                    .replace("-", "")
                    .replace("(", "")
                    .replace(")", "")
                    .replace("+", "")
                )
                # Asegurar que tenga formato internacional (agregar 57 si no lo tiene)
                if not phone.startswith("57") and len(phone) == 10:
                    phone = "57" + phone
                return phone

        return None

    def _prepare_template_params(self):
        """Preparar los parámetros para el template de WhatsApp"""

        # Array de doctores aleatorios
        doctors = ["Dr. Carlos Rodríguez", "Dra. María González", "Dr. Andrés Martínez"]

        # Array de direcciones aleatorias
        addresses = ["Cra. 100 # 5-23", "Calle 15 # 102-45", "Av. 6N # 28-10"]

        # Obtener nombre del asistente
        attendee_name = "Paciente"  # Default
        if self.attendee_ids and self.attendee_ids[0].partner_id:
            attendee_name = self.attendee_ids[0].partner_id.name

        # Seleccionar doctor aleatorio
        selected_doctor = random.choice(doctors)

        # Formatear fecha (DD/MM/YYYY)
        event_date = (
            self.start.strftime("%d/%m/%Y")
            if self.start
            else datetime.now().strftime("%d/%m/%Y")
        )

        # Formatear hora (HH:MM a.m/p.m)
        event_time = "08:00 a.m"  # Default
        if self.start:
            hour = self.start.hour
            minute = self.start.minute
            am_pm = "a.m" if hour < 12 else "p.m"
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            event_time = f"{display_hour:02d}:{minute:02d} {am_pm}"

        # Seleccionar dirección aleatoria
        selected_address = random.choice(addresses)

        # Retornar array de parámetros
        return [
            attendee_name,
            selected_doctor,
            event_date,
            event_time,
            selected_address,
        ]

    def _send_whatsapp_template(self, phone, params):
        """Enviar template de WhatsApp via webhook"""

        url = (
            "https://serviciosfenalco.fenalcovalle.com/asertis/webhook/templatewhatsapp"
        )

        headers = {
            "Content-Type": "application/json",
            "Cookie": "session_id=b816748fdbac8d6a41468d943d9b9f4f8154c68c",
        }

        data = {
            "args": {
                "phone": phone,
                "id_template": "646457025156840",
                "name_template": "demo_citas_clinica_occidente",
                "id_bot": "736667109527733",
                "params": params,
            }
        }

        try:
            _logger.info(
                "Enviando mensaje WhatsApp a %s con parámetros: %s", phone, params
            )

            response = requests.post(url, json=data, headers=headers, timeout=30)

            _logger.info(
                "Respuesta del webhook WhatsApp: Status %s, Body: %s",
                response.status_code,
                response.text,
            )

            # Considerar exitoso si el status code es 200 o 201
            if response.status_code in [200, 201]:
                return True
            else:
                _logger.error("Error en webhook WhatsApp: %s", response.text)
                return False

        except requests.exceptions.Timeout:
            _logger.error("Timeout al enviar mensaje WhatsApp")
            return False
        except requests.exceptions.RequestException as e:
            _logger.error("Error de conexión al enviar WhatsApp: %s", str(e))
            return False
        except Exception as e:
            _logger.error("Error inesperado al enviar WhatsApp: %s", str(e))
            return False
