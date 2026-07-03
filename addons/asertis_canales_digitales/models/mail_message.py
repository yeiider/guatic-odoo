from odoo import models, fields, api
import uuid
import logging

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = "mail.message"

    message_id_provider_chat = fields.Char(
        string="ID del mensaje del proveedor",
        index=True,
        readonly=True,
        copy=False,
        default=lambda self: str(uuid.uuid4()),
        help="UUID único para tracking de mensajes con proveedores externos",
    )

    is_from_webhook = fields.Boolean(
        string="Mensaje de Webhook",
        default=False,
        readonly=True,
        copy=False,
        help="Indica si este mensaje proviene de un webhook externo",
    )

    provider_delivery_status = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("sent", "Enviado"),
            ("failed", "Fallido"),
        ],
        default="pending",
        string="Estado de entrega al proveedor",
    )

    @api.model
    def check_duplicate_by_provider_id(self, provider_message_id):
        """
        Verificar si ya existe un mensaje con este provider_message_id
        """
        if not provider_message_id:
            return False
        try:

            self.env.cr.execute(
                """
                SELECT id FROM mail_message
                WHERE message_id_provider_chat = %s
                FOR UPDATE NOWAIT
            """,
                (provider_message_id,),
            )

            result = self.env.cr.fetchone()
            if result:

                return result

            return False

        except Exception as e:

            _logger.warning(
                "Could not acquire lock for message %s: %s",
                provider_message_id,
                str(e),
            )
            return False
