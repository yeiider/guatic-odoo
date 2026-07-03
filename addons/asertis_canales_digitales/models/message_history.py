# models/message_history.py
import dataclasses
from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class MessageHistory(models.TransientModel):
    _name = "message.history"
    _description = "Historial de Mensajes de Plataforma Externa"

    channel_id = fields.Many2one("discuss.channel", string="Canal", required=True)
    message_ids = fields.One2many(
        "message.history.line", "history_id", string="Mensajes"
    )
    display_content = fields.Text(string="Contenido a Mostrar")
    media_filename = fields.Char(string="Nombre de Archivo")
    media_size = fields.Float(string="Tamaño de Medios (en bytes)")
    timestamp = fields.Datetime(string="Fecha y Hora")
    message_type = fields.Selection(
        [
            ("text", "Texto"),
            ("image", "Imagen"),
            ("file", "Archivo"),
            ("audio", "Audio"),
        ],
        string="Tipo de Mensaje",
        default="text",
    )
    sender_type = fields.Selection(
        [("bot", "Bot"), ("user", "Usuario"), ("me", "Yo")],
        string="Tipo de Remitente",
        required=True,
    )
    sender_name = fields.Char(string="Nombre del Remitente")

    def get_message_history(self):
        """Consulta la API externa para obtener el historial de mensajes"""
        try:
            # Configurar la URL de tu API aquí
            api_url = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("message_history.api_url", "")
            )
            api_key = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("message_history.api_key", "")
            )

            if not api_url:
                raise ValueError("URL de API no configurada")

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            # Parámetros para la consulta (ajustar según tu API)
            params = {
                "channel_id": self.channel_id.id,
                "provider_id": self.channel_id.name,  # Ajustar según tu lógica
            }

            response = requests.get(api_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            messages_data = response.json()

            # Limpiar mensajes anteriores
            self.message_ids.unlink()

            # Crear líneas de mensajes
            message_lines = []
            for msg_data in messages_data.get("messages", []):
                message_lines.append(
                    (
                        0,
                        0,
                        {
                            "message_text": msg_data.get("text", ""),
                            "sender_type": self._determine_sender_type(msg_data),
                            "sender_name": msg_data.get("sender_name", ""),
                            "timestamp": msg_data.get("timestamp"),
                            "message_type": msg_data.get("type", "text"),
                        },
                    )
                )

            self.message_ids = message_lines

            return {
                "type": "ir.actions.act_window",
                "name": "Historial de Mensajes",
                "res_model": "message.history",
                "res_id": self.id,
                "view_mode": "form",
                "target": "new",
                "context": {"form_view_initial_mode": "readonly"},
            }

        except Exception as e:
            _logger.error(f"Error al consultar API: {str(e)}")
            raise UserError(f"Error al obtener historial: {str(e)}")

    def _determine_sender_type(self, msg_data):
        """Determina el tipo de remitente basado en los datos del mensaje"""
        sender_id = msg_data.get("sender_id", "")
        sender_type = msg_data.get("sender_type", "")

        if sender_type == "bot" or "bot" in sender_id.lower():
            return "bot"
        elif sender_id == self.env.user.partner_id.id or sender_type == "agent":
            return "me"
        else:
            return "user"


class MessageHistoryLine(models.TransientModel):
    _name = "message.history.line"
    _description = "Línea de Historial de Mensajes"
    _order = "timestamp desc"

    history_id = fields.Many2one(
        "message.history", string="Historial", ondelete="cascade"
    )
    message_text = fields.Text(string="Mensaje", required=True)
    sender_type = fields.Selection(
        [("bot", "Bot"), ("user", "Usuario"), ("me", "Yo")],
        string="Tipo de Remitente",
        required=True,
    )
    sender_name = fields.Char(string="Nombre del Remitente")
    media_url = fields.Char(string="URL de Medios")
    thumbnail_url = fields.Char(string="URL de Miniatura")
    latitude = fields.Float(string="Latitud")
    longitude = fields.Float(string="Longitud")
    location_name = fields.Char(string="Nombre de Ubicación")
    display_content = fields.Text(string="Contenido a Mostrar")
    media_filename = fields.Char(string="Nombre de Archivo")
    media_size = fields.Float(string="Tamaño de Medios (en bytes)")
    timestamp = fields.Datetime(string="Fecha y Hora")
    message_type = fields.Selection(
        [
            ("text", "Texto"),
            ("image", "Imagen"),
            ("file", "Archivo"),
            ("audio", "Audio"),
        ],
        string="Tipo de Mensaje",
        default="text",
    )
