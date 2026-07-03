from odoo import models, fields, api


import psycopg2
import time
from .payloads.dispatcher import WebhookDispatcher
from .payloads.base_event import FileEvent, BaseEvent, ContactMetadata
from typing import List
import logging
from markupsafe import Markup
from odoo.tools import html_escape
from .utils.retry import retry_on_transient_error
from odoo.addons.queue_job.exception import RetryableJobError

_logger = logging.getLogger(__name__)


class WebhookProcessor(models.Model):
    """
    WebhookProcessor

    This Odoo model is responsible for processing incoming webhook events from external providers (such as chat or messaging platforms) and integrating them into the Odoo system as messages, partners, and channels. It includes robust duplicate detection and prevention mechanisms to ensure idempotent processing, as well as utilities for handling file attachments and cleaning up duplicate records.

    Main Responsibilities:
    - Process webhook events, extract relevant payload data, and route messages to the appropriate Odoo models.
    - Prevent duplicate message processing using row-level locking and final duplicate checks.
    - Create or find partners and channels based on incoming webhook data.
    - Handle file attachments from webhook messages, supporting both URLs and base64-encoded data.
    - Provide utility methods for cleaning up duplicate messages and gathering processing statistics.

    Key Methods:
    - process_webhook_event: Main entry point for processing a webhook event, with duplicate protection.
    - _check_and_lock_duplicate: Checks for duplicate messages using row-level locking to avoid race conditions.
    - _process_webhook_core: Core logic for processing the webhook, including partner and channel management.
    - _create_message_with_final_check: Creates a message in Odoo, with a final duplicate check.
    - _process_message_files / _create_attachment_from_file_event: Handle file attachments from webhook payloads.
    - cleanup_duplicate_messages: Utility to remove existing duplicate messages.
    - get_processing_stats: Returns statistics about webhook and regular message processing.

    Assumptions:
    - Relies on custom methods such as find_or_create_partner and find_or_create_channel on related models.
    - Expects payloads to follow a specific structure, including message, user, and contact information.
    - Designed for use in Odoo environments with multi-threaded or concurrent webhook delivery.

    Logging:
    - Uses _logger to record processing steps, warnings, errors, and statistics.

    Usage:
    - Intended to be called by webhook endpoints or background jobs that receive and process external events.
    """

    _name = "webhook.processor"
    _description = "Webhook Event Processor"

    name = fields.Char(string="Name", default="Webhook Processor")

    def process_webhook_event(self, provider_name: str, payload_data):
        """
        Procesar evento de webhook con protección mejorada contra duplicados.
        """

        try:
            dispatcher_webhook = WebhookDispatcher(provider_name, payload_data)
            payload = dispatcher_webhook.extract_event()

            if not payload.is_incoming:

                return {"status": "skipped", "message": "Not an incoming message"}

            message_id = payload.message.message_id_provider_chat

            if message_id and self._check_and_lock_duplicate(message_id):

                _logger.info("Duplicate message detected and skipped: %s", message_id)
                return {
                    "status": "duplicate",
                    "message": "Message already processed",
                    "message_id": message_id,
                }
            if payload.message.content == "" and (
                not payload.message.files
                or (
                    isinstance(payload.message.files, list)
                    and len(payload.message.files) == 0
                )
            ):
                return {
                    "status": "empty",
                    "message": "Empty message, no content and no files",
                }
            _logger.info(
                "Processing webhook event for provider: %s, user_id: %s, channel: %s",
                provider_name,
                payload.user_id,
                payload.channel_name or provider_name,
            )

            result = self._process_webhook_core(
                provider_name,
                payload.user_id,
                payload.message,
                payload.channel_name or provider_name,
                payload.user_name,
                payload,
            )

            return result
        except psycopg2.errors.ForeignKeyViolation as e:
            _logger.error("Foreign key violation processing webhook: %s", str(e))
            raise RetryableJobError("Foreign key violation - partner not yet committed", seconds=5)
        except ValueError as e:
            _logger.error("Validation error processing webhook: %s", str(e))
            raise
        except Exception as e:
            _logger.error("Unexpected error processing webhook: %s", str(e))

            raise

    def _check_and_lock_duplicate(self, message_id_provider_chat):
        """
        Verificar duplicados con bloqueo de fila para evitar condiciones de carrera.
        Retorna True si es duplicado, False si es nuevo.
        """
        if not message_id_provider_chat:
            return False

        try:

            self.env.cr.execute(
                """
                SELECT id FROM mail_message
                WHERE message_id_provider_chat = %s
                FOR UPDATE NOWAIT
            """,
                (message_id_provider_chat,),
            )

            result = self.env.cr.fetchone()
            if result:

                return True

            return False

        except Exception as e:

            _logger.warning(
                "Could not acquire lock for message %s: %s",
                message_id_provider_chat,
                str(e),
            )
            return True

    def _process_webhook_core(
        self, provider_name, user_id, message, channel_name, user_name, payload
    ):
        """Lógica core del procesamiento del webhook"""

        if not user_id:
            raise ValueError("user_id is required")
        partner = self.env["res.partner"].find_or_create_partner(
            provider_data={
                "user_id": user_id,
                "provider_name": provider_name,
                "user_name": user_name,
                "user_channel": channel_name or provider_name,
            },
            contact_metadata=(
                ContactMetadata(
                    first_name=(
                        payload.message.contact.first_name
                        if payload.message.contact
                        else None
                    ),
                    last_name=(
                        payload.message.contact.last_name
                        if payload.message.contact
                        else None
                    ),
                    phone_number=(
                        payload.message.contact.phone_number
                        if payload.message.contact
                        else None
                    ),
                    email=(
                        payload.message.contact.email
                        if payload.message.contact
                        else None
                    ),
                    profile_picture_url=(
                        payload.message.contact.profile_picture_url
                        if payload.message.contact
                        else None
                    ),
                )
                if payload.message.contact
                else None
            ),
        )
        if not partner:
            raise ValueError("Partner not found or created")
        internal_user = self._get_internal_user()
        internal_users_ids = self._get_internals_users_ids_by_ability_and_provider_name(
            payload.ability, provider_name
        )
        time.sleep(0.3)
        if not internal_user:
            raise ValueError("Internal user not found")
        members = [partner.id, internal_user.id] + internal_users_ids
        channel = self.env["discuss.channel"].find_or_create_channel(
            provider_name=provider_name,
            channel_name=channel_name or provider_name,
            partner_ids=members,
            external_channel_id=user_id,
            icon_name=payload.channel_config.type.value,
            extra_metadata=payload.metadata or {},
        )
        message_channel = self._create_message_with_final_check(
            channel, message, partner, provider_name, payload
        )
        _logger.info("Processed webhook event for provider: %s", message_channel)
        self.env.cr.commit()
        return {
            "status": "success",
            "message": "Message received and processed successfully",
            "channel_id": channel.id,
            "partner_id": partner.id,
            "message_id": message_channel.id if message_channel else None,
        }

    @retry_on_transient_error(
        max_retries=3, initial_delay=0.4, catch_integrity_error=True
    )
    def _create_message_with_final_check(
        self, channel, message, partner, provider_name, payload: BaseEvent
    ):
        """
        Crear mensaje con verificación final por si acaso.
        """
        self.env.cr.flush()
        self.env.cr.commit()
        time.sleep(0.2)  # Pequeña pausa para evitar problemas de concurrencia
        message_id_provider = getattr(message, "message_id_provider_chat", None)

        if message_id_provider:

            existing = self.env["mail.message"].check_duplicate_by_provider_id(
                message_id_provider
            )
            if existing:

                return existing

        try:

            message_event = payload.message
            attachment_ids = []

            if hasattr(message_event, "files") and message_event.files:
                attachment_ids = self._process_message_files(
                    channel, message_event.files
                )
            attachment_models = self.env["ir.attachment"].sudo().browse(attachment_ids)
            render = self.env["attachment.renderer"].sudo()

            body = render.generate_message_body_native(
                message.content, attachment_models
            )
            # Asegurar que body sea Markup si no lo es
            if not isinstance(body, Markup):
                body = Markup(body) if body else Markup("")
            time.sleep(0.1)  # Pequeña pausa para evitar problemas de concurrencia
            if not channel.exists():
                _logger.warning(
                    "Channel %s no longer exists, cannot create message", channel.id
                )
                searchChannel = (
                    self.env["discuss.channel"]
                    .sudo()
                    .search(
                        [
                            ("external_channel_id", "=", payload.user_id),
                            ("provider_name", "=", provider_name),
                            ("active", "=", True),
                        ],
                        limit=1,
                    )
                )
                if searchChannel:
                    channel = searchChannel
                else:
                    _logger.error(
                        "No active channel found for user_id %s and provider %s",
                        payload.user_id,
                        provider_name,
                    )
                    raise RetryableJobError(
                        "Failed to create new channel, channel_id is None"
                    )
            time.sleep(0.5)
            message_channel = channel.with_context(
                skip_send_to_provider=True,
                webhook_source=True,
            ).message_post(
                body=body,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                author_id=partner.id,
                attachment_ids=attachment_ids,
            )

            if message_channel:
                values_to_write = {
                    "is_from_webhook": True,
                }

                if message_id_provider:
                    values_to_write["message_id_provider_chat"] = message_id_provider

                message_channel.write(values_to_write)

                _logger.info(
                    "Created webhook message %s with provider_id: %s",
                    message_channel.id,
                    message_id_provider,
                )

            return message_channel

        except Exception as e:
            _logger.error("Error creating message: %s", str(e))
            raise

    def _get_internals_users_ids_by_ability_and_provider_name(
        self, ability: str, provider_name: str
    ) -> List[int]:
        """Obtener IDs de usuarios internos según la habilidad"""

        internal_users_ids = (
            self.env["res.partner"]
            .sudo()
            .search(
                [
                    ("provider_skill_ids.name", "=", ability),
                    ("provider_skill_ids.provider_id.name", "=", provider_name),
                    ("provider_skill_ids.active", "=", True),
                ]
            )
            .ids
        )
        _logger.info(
            "Found %s internal users with ability '%s' for provider '%s'",
            len(internal_users_ids),
            ability,
            provider_name,
        )

        if not internal_users_ids:
            _logger.warning("No internal users found with ability: %s", ability)
            admin_user = self._get_internal_user()
            return [admin_user.id]
        return internal_users_ids

    def _get_internal_user(self):
        """Obtener el usuario interno (operador del chat)"""
        return self.env.ref("base.user_admin").sudo().partner_id

    def _process_message_files(self, channel, files: List[FileEvent]) -> List[int]:
        """
        Procesar lista de FileEvent y crear attachments
        Retorna lista de IDs de attachments creados
        """
        attachment_ids = []

        try:
            for file_event in files:
                attachment = self._create_attachment_from_file_event(
                    channel, file_event
                )
                if attachment:
                    attachment_ids.append(attachment.id)
                else:
                    _logger.warning(
                        "Failed to create attachment for file: %s", file_event.name
                    )

            _logger.info(
                "Processed %s files, created %s attachments",
                len(files),
                len(attachment_ids),
            )
            return attachment_ids

        except Exception as e:
            _logger.error("Error processing message files: %s", str(e))
            return attachment_ids

    def _create_attachment_from_file_event(self, channel, file_event: FileEvent):
        """Crear ir.attachment desde FileEvent Maneja tanto URLs como datos base64"""

        try:

            if file_event.url:
                return self._download_and_create_attachment(file_event, channel)

            elif file_event.datas:
                return self._create_attachment_from_data(channel, file_event)

            else:
                _logger.warning("FileEvent sin URL ni datos: %s", file_event.name)
                return False

        except Exception as e:
            _logger.error("Error processing FileEvent %s: %s", file_event.name, str(e))
            return False

    def _download_and_create_attachment(self, file_event: FileEvent, channel=None):
        """Descargar archivo desde URL y crear attachment"""
        try:
            import requests
            from urllib.parse import urlparse
            import mimetypes
            import base64

            response = requests.get(file_event.url, timeout=10)
            response.raise_for_status()

            file_data_b64 = base64.b64encode(response.content).decode("utf-8")

            mimetype = file_event.mimetype
            if not mimetype:
                mimetype = response.headers.get("content-type")
                if not mimetype:
                    mimetype, _ = mimetypes.guess_type(
                        file_event.url or file_event.name
                    )
                    mimetype = mimetype or "application/octet-stream"

            name = file_event.name
            if not name:
                parsed_url = urlparse(file_event.url)
                path = parsed_url.path
                if isinstance(path, bytes):
                    path = path.decode("utf-8", errors="replace")
                name = path.split("/")[-1] or "archivo_descargado"

            attachment_data = {
                "name": name,
                "type": file_event.type,
                "datas": file_data_b64,
                "res_model": "discuss.channel",
                "url": file_event.url,
                "res_id": channel.id if channel else None,
                "mimetype": mimetype,
            }

            if file_event.description:
                attachment_data["description"] = file_event.description
            if file_event.access_token:
                attachment_data["access_token"] = file_event.access_token
            if file_event.checksum:
                attachment_data["checksum"] = file_event.checksum

            attachment = self.env["ir.attachment"].sudo().create(attachment_data)

            _logger.info(
                "Downloaded and created attachment from URL: %s -> ID: %s",
                file_event.url,
                attachment.id,
            )
            return attachment

        except Exception as e:
            _logger.error(
                "Error downloading file from URL %s: %s", file_event.url, str(e)
            )
            return False

    def _create_attachment_from_data(self, channel, file_event: FileEvent):
        """Crear attachment desde datos base64 existentes"""
        try:
            import mimetypes

            datas = file_event.datas
            if datas.startswith("data:"):

                if not file_event.mimetype:
                    mimetype_part = datas.split(";")[0].split(":")[1]
                    file_event.mimetype = mimetype_part
                datas = datas.split(",")[1]

            mimetype = file_event.mimetype
            if not mimetype and file_event.name:
                mimetype, _ = mimetypes.guess_type(file_event.name)
                mimetype = mimetype or "application/octet-stream"

            attachment_data = {
                "name": file_event.name or "archivo_webhook",
                "type": file_event.type,
                "datas": datas,
                "res_model": "discuss.channel",
                "res_id": channel.id,
                "url": file_event.url,
                "mimetype": mimetype,
            }

            if file_event.description:
                attachment_data["description"] = file_event.description
            if file_event.access_token:
                attachment_data["access_token"] = file_event.access_token
            if file_event.checksum:
                attachment_data["checksum"] = file_event.checksum

            attachment = self.env["ir.attachment"].sudo().create(attachment_data)

            _logger.info(
                "Created attachment from base64 data: %s -> ID: %s",
                file_event.name,
                attachment.id,
            )
            return attachment

        except Exception as e:
            _logger.error(
                "Error creating attachment from base64 for %s: %s",
                file_event.name,
                str(e),
            )
            return False

    def _validate_file_event(self, file_event: FileEvent) -> bool:
        """Validar que FileEvent tiene los datos mínimos necesarios"""
        if not file_event.name:
            _logger.warning("FileEvent without name")
            return False

        if not file_event.url and not file_event.datas:
            _logger.warning("FileEvent %s without URL or data", file_event.name)
            return False

        if file_event.datas:
            try:

                data_to_validate = file_event.datas
                if data_to_validate.startswith("data:"):
                    data_to_validate = data_to_validate.split(",")[1]

                return True
            except Exception as e:
                _logger.warning(
                    "FileEvent %s has invalid base64 data: %s", file_event.name, str(e)
                )
                return False

        return True

    @api.model
    def cleanup_duplicate_messages(self):
        """
        Método de utilidad para limpiar mensajes duplicados existentes.
        Ejecutar manualmente si ya tienes duplicados.
        """
        _logger.info("Starting duplicate cleanup...")

        self.env.cr.execute(
            """
            SELECT message_id_provider_chat, array_agg(id ORDER BY id) as ids
            FROM mail_message 
            WHERE message_id_provider_chat IS NOT NULL
            GROUP BY message_id_provider_chat
            HAVING COUNT(*) > 1
        """
        )

        duplicates = self.env.cr.fetchall()

        for message_id_provider, ids in duplicates:

            keep_id = ids[0]
            delete_ids = ids[1:]

            _logger.info(
                "Found duplicates for %s: keeping %s, deleting %s",
                message_id_provider,
                keep_id,
                delete_ids,
            )

            self.env["mail.message"].browse(delete_ids).unlink()

        _logger.info(
            "Duplicate cleanup completed. Processed %s groups", len(duplicates)
        )

    @api.model
    def get_processing_stats(self):
        """Obtener estadísticas de procesamiento de webhooks"""

        self.env.cr.execute(
            """
            SELECT 
                CASE 
                    WHEN message_id_provider_chat IS NOT NULL THEN 'webhook'
                    ELSE 'regular'
                END as source_type,
                COUNT(*) as count
            FROM mail_message
            WHERE create_date >= NOW() - INTERVAL '24 hours'
            GROUP BY source_type
        """
        )

        stats = dict(self.env.cr.fetchall())

        return {
            "webhook_messages_24h": stats.get("webhook", 0),
            "regular_messages_24h": stats.get("regular", 0),
            "total_messages_24h": sum(stats.values()),
        }
