import time
from .utils.avatar import get_provider_avatar
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
import json

from .provider.handlers.file_handler import ProviderFileHandler
from psycopg2 import OperationalError, IntegrityError
from odoo.addons.queue_job.exception import RetryableJobError
from .utils.retry import retry_on_transient_error

_logger = logging.getLogger(__name__)


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    provider_metadata = fields.Json("Provider Metadata")
    provider_name = fields.Text("Nombre del proveedor")
    external_channel_id = fields.Text("ID del canal externo")
    channel_avatar = fields.Binary(string="Ícono del canal", attachment=True)

    def _to_store(self, store, **kwargs):
        """Incluir los campos personalizados en la serialización para el frontend"""
        results = []
        for channel in self:
            result = super(DiscussChannel, channel)._to_store(store, **kwargs) or {}

            # Añadir los campos personalizados al store
            result.update(
                {
                    "provider_metadata": channel.provider_metadata,
                    "provider_name": channel.provider_name,
                    "external_channel_id": channel.external_channel_id,
                }
            )
            results.append(result)
        return results

    def _channel_info(self, extra_info=False):
        """Incluir información personalizada en el canal"""
        results = super()._channel_info(extra_info=extra_info)

        # Iterar sobre los resultados para actualizar la información de cada canal
        for result in results:
            channel_id = result.get("id")
            if channel_id:
                channel = self.browse(channel_id)
                result.update(
                    {
                        "provider_metadata": channel.provider_metadata,
                        "provider_name": channel.provider_name,
                        "external_channel_id": channel.external_channel_id,
                    }
                )
        return results

    @api.model
    def message_post(self, **kwargs):
        """Override message_post to send responses to webhook"""

        if self.env.context.get("skip_send_to_provider"):
            return super().message_post(**kwargs)

        if self.env.context.get("webhook_source"):
            return super().message_post(**kwargs)

        message = super().message_post(**kwargs)

        should_send_to_provider = (
            self.channel_type == "chat"
            and message.author_id
            and not getattr(message.author_id, "is_provider_chat_user", False)
            and message.message_type == "comment"
            and self.provider_name
            and not getattr(message, "is_from_webhook", False)
        )

        if should_send_to_provider:
            try:
                self._send_to_provider(message, self.provider_name)
            except Exception as e:
                _logger.error(f"Error sending message to provider: {e}")
        else:
            _logger.info(
                "Skipping send to provider for message %s - is_from_webhook: %s",
                message.id,
                getattr(message, "is_from_webhook", False),
            )

        return message

    def action_show_message_history(self):
        """Acción para mostrar el historial de mensajes"""
        self.ensure_one()

        # Crear el registro transitorio
        history = self.env["message.history"].create(
            {
                "channel_id": self.id,
            }
        )

        # Llamar al método para obtener el historial
        return history.get_message_history()

    def _send_to_provider(self, message, provider_name: str = "Botpress"):
        """Enviar mensaje al webhook del proveedor - versión con arquitectura mejorada"""

        handler = ProviderFileHandler(provider_name, self.env)
        try:
            handler.send_message(message, self.provider_metadata)
            message.write({"provider_delivery_status": "sent"})
        except Exception as e:
            message.write({"provider_delivery_status": "failed"})
            _logger.error(f"Error sending message to provider {provider_name}: {e}")

    def _add_members_individually(self, partner_ids):
        """
        Add members one by one to handle individual duplicates
        """
        for partner_id in partner_ids:
            try:

                self.add_members([partner_id])
                _logger.info(
                    f"Successfully added partner {partner_id} to channel {self.id}"
                )
            except IntegrityError as e:
                if "discuss_channel_member_partner_unique" in str(e):
                    _logger.info(
                        f"Partner {partner_id} already member of channel {self.id}, skipping"
                    )
                else:
                    _logger.error(
                        f"Error adding partner {partner_id} to channel {self.id}: {e}"
                    )
                    raise
            except Exception as e:
                _logger.error(
                    f"Unexpected error adding partner {partner_id} to channel {self.id}: {e}"
                )
                raise

    def _find_fallback_channel(self, external_channel_id, provider_name):
        """
        Find channel created by another process as fallback
        """
        try:
            # Use a fresh cursor to avoid transaction issues

            fallback_channel = (
                self.env["discuss.channel"]
                .sudo()
                .search(
                    [
                        ("external_channel_id", "=", external_channel_id),
                        ("channel_type", "=", "chat"),
                        ("provider_name", "=", provider_name),
                        ("active", "=", True),
                    ],
                    limit=1,
                )
            )

            if fallback_channel:
                _logger.info(
                    f"Found fallback channel {fallback_channel.id} for external_id {external_channel_id}"
                )
                # Return the channel in the original environment
                return self.sudo().browse(fallback_channel.id)

        except Exception as e:
            _logger.error(f"Error finding fallback channel: {e}")

        return None

    def _compare_provider_metadata(self, current_metadata, new_metadata):
        """Comparar metadata del proveedor para detectar cambios"""
        try:
            current_str = json.dumps(current_metadata or {}, sort_keys=True)
            new_str = json.dumps(new_metadata or {}, sort_keys=True)
            return current_str == new_str
        except Exception as e:
            _logger.error(f"Error comparing metadata: {e}")
            return False

    @retry_on_transient_error(
        max_retries=3, initial_delay=0.4, catch_integrity_error=True
    )
    def find_or_create_channel(
        self,
        provider_name: str,
        channel_name: str,
        external_channel_id: str,
        partner_ids: list,
        icon_name: str = "generic",
        extra_metadata=None,
    ):
        """
        Busca un canal existente o crea uno nuevo, evita escrituras innecesarias
        y maneja concurrencia para Odoo 16.
        """
        # Flush para asegurar datos actualizados
        self.env.cr.flush()

        # Buscar canal existente
        existing_channel = self.sudo().search(
            [
                ("external_channel_id", "=", external_channel_id),
                ("channel_type", "=", "chat"),
                ("provider_name", "=", provider_name),
                ("active", "=", True),
            ],
            limit=1,
        )

        avatar_64 = get_provider_avatar(icon_name)

        if existing_channel:
            _logger.info(
                f"Found existing channel {existing_channel.id} for external_id {external_channel_id}"
            )

            # Actualizar canal existente
            self._update_existing_channel(
                existing_channel, partner_ids, avatar_64, extra_metadata, icon_name
            )
            return existing_channel

        # Crear nuevo canal - sin try/catch, el decorador maneja los errores
        _logger.info(f"Creating new channel for external_id {external_channel_id}")

        create_data = {
            "name": channel_name,
            "channel_type": "chat",
            "description": f"Canal de chat para {channel_name}",
            "provider_name": provider_name,
            "external_channel_id": external_channel_id,
            "provider_metadata": extra_metadata or {},
            "image_128": avatar_64,
        }
        try:
            with self.env.registry.cursor() as new_cr:
                new_env = self.env(cr=new_cr, context=self.env.context)
                new_channel = new_env["discuss.channel"].sudo().create(create_data)
                time.sleep(0.1)
                new_cr.commit()
                channel_id = new_channel.id

            time.sleep(0.05)  # Espera breve para evitar problemas de concurrencia
            if not channel_id:
                _logger.error("Failed to create new channel, channel_id is None")
                raise RetryableJobError(
                    "Failed to create new channel, channel_id is None"
                )
            new_channel = self.sudo().browse(channel_id)
            if not new_channel:
                _logger.error(
                    f"Failed to find newly created channel with ID: {channel_id}"
                )
                raise RetryableJobError(
                    f"Failed to find newly created channel with ID: {channel_id}"
                )
            _logger.info(f"New channel created with ID: {channel_id}")
            # Agregar miembros al nuevo canal
            if partner_ids:
                new_channel._safe_add_members(partner_ids)

            return new_channel

        except Exception as e:
            _logger.error(f"Error creating channel: {e}")
            # Tu decorador se encargará del retry automáticamente
            raise

    def _update_existing_channel(
        self, existing_channel, partner_ids, avatar_64, extra_metadata, icon_name
    ):
        """Método auxiliar para actualizar canal existente"""
        # Obtener los IDs de partners actuales
        current_partner_ids = set(
            existing_channel.channel_member_ids.mapped("partner_id.id")
        )
        expected_partner_ids = set(partner_ids)

        # Agregar partners faltantes
        missing_partners = expected_partner_ids - current_partner_ids
        if missing_partners:
            _logger.info(
                f"Adding {len(missing_partners)} missing partners to channel {existing_channel.id}"
            )
            existing_channel.with_delay(
                priority=5,
                eta=None,
                max_retries=3,
                channel="discuss.channel.member",
            )._add_manual_members(list(missing_partners))

        # Remover partners extra
        extra_partners = current_partner_ids - expected_partner_ids
        if extra_partners:
            _logger.info(
                f"Removing {len(extra_partners)} extra partners from channel {existing_channel.id}"
            )
            members_to_remove = existing_channel.channel_member_ids.filtered(
                lambda m: m.partner_id.id in extra_partners
            )
            if members_to_remove:
                members_to_remove.unlink()

        # Actualizar metadata si es necesario
        update = {}
        if extra_metadata and not self._compare_provider_metadata(
            existing_channel.provider_metadata, extra_metadata
        ):
            update["provider_metadata"] = extra_metadata

        if icon_name and existing_channel.channel_avatar != avatar_64:
            update["image_128"] = avatar_64

        if update:
            existing_channel.write(update)

    @retry_on_transient_error(
        max_retries=3, initial_delay=0.4, catch_integrity_error=True
    )
    def _safe_add_members(self, partner_ids):
        """
        Safely add members to channel, avoiding duplicates and validation errors
        """
        if not partner_ids:
            return

        # Obtener miembros existentes
        existing_member_partner_ids = set(
            self.channel_member_ids.mapped("partner_id.id")
        )

        # Filtrar partners que ya son miembros
        new_partner_ids = [
            pid for pid in partner_ids if pid not in existing_member_partner_ids
        ]

        if not new_partner_ids:
            _logger.info(f"All partners already members of channel {self.id}")
            return

        try:

            member_values = []
            for partner_id in new_partner_ids:
                exists = (
                    self.env["discuss.channel.member"]
                    .sudo()
                    .search(
                        [("channel_id", "=", self.id), ("partner_id", "=", partner_id)],
                        limit=1,
                    )
                )
                if not exists:
                    member_values.append(
                        {
                            "channel_id": self.id,
                            "partner_id": partner_id,
                        }
                    )

            if member_values and len(member_values) <= 2:
                self.env["discuss.channel.member"].sudo().create(member_values)
                _logger.info(
                    f"Successfully added {len(member_values)} members to channel {self.id}"
                )
            elif member_values and len(member_values) > 2:
                self._add_manual_members(new_partner_ids)

        except IntegrityError as e:
            if "discuss_channel_member_partner_unique" in str(e):
                _logger.warning(
                    f"Some partners already members of channel {self.id}, adding individually"
                )
                # Agregar miembros uno por uno como fallback
                self._add_members_individually(new_partner_ids)
            else:
                _logger.error(f"Error in _safe_add_members on channel {self.id}: {e}")
                raise
        except Exception as e:
            _logger.error(f"Error in _safe_add_members on channel {self.id}: {e}")
            raise

    def _add_manual_members(self, partner_ids):
        """
        Add members to the channel manually, avoiding duplicates
        """

        if not partner_ids:
            return

        existing_member_partner_ids = set(
            self.channel_member_ids.mapped("partner_id.id")
        )
        new_partner_ids = [
            pid for pid in partner_ids if pid not in existing_member_partner_ids
        ]

        if not new_partner_ids:
            _logger.info(f"All partners already members of channel {self.id}")
            return

        created_ids = []
        try:
            for partner_id in new_partner_ids:

                # 1. Obtener el ID del canal
                channel_id = self.id
                defaults = self.env["discuss.channel.member"].default_get(
                    ["new_message_separator"]
                )
                _logger.info(f"Defaults for new member: {defaults}")

                # 2. Insertar en discuss_channel_member directamente
                self.env.cr.execute(
                    """
                    INSERT INTO discuss_channel_member (
                        channel_id, partner_id, new_message_separator,
                        create_date, write_date, create_uid, write_uid)
                    VALUES (%s, %s, %s, NOW(), NOW(), %s, %s)
                    RETURNING id
                    """,
                    (channel_id, partner_id, 0, self.env.uid, self.env.uid),
                )
                created_id = self.env.cr.fetchone()[0]
                created_ids.append(created_id)
        except Exception as e:
            _logger.error(f"Error in direct SQL member creation: {e}")
            raise

        return self.browse(created_ids)

    def _create_direct_sql(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        created_ids = []
        for vals in vals_list:
            try:
                if "channel_id" in vals and "partner_id" in vals:
                    existing = self.search(
                        [
                            ("channel_id", "=", vals["channel_id"]),
                            ("partner_id", "=", vals["partner_id"]),
                        ]
                    )
                    if not existing:
                        self.env.cr.execute(
                            """
                            INSERT INTO discuss_channel_member (channel_id, partner_id, create_date, write_date, create_uid, write_uid)
                            VALUES (%s, %s, NOW(), NOW(), %s, %s)
                            RETURNING id
                        """,
                            (
                                vals["channel_id"],
                                vals["partner_id"],
                                self.env.uid,
                                self.env.uid,
                            ),
                        )
                        created_id = self.env.cr.fetchone()[0]
                        created_ids.append(created_id)
                    else:
                        created_ids.append(existing.id)
            except Exception as e:
                _logger.error(f"SQL error creating member: {e}")

        return self.browse(created_ids)
