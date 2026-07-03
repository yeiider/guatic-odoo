from odoo import models, fields, api
import logging
import json

from .provider.handlers.file_handler import ProviderFileHandler
from psycopg2 import OperationalError, IntegrityError
from odoo.addons.queue_job.exception import RetryableJobError
from .utils.retry import retry_on_transient_error

_logger = logging.getLogger(__name__)


class MailChannel(models.Model):
    _inherit = "discuss.channel"

    provider_metadata = fields.Json("Provider Metadata")
    provider_name = fields.Text("Nombre del proveedor")
    external_channel_id = fields.Text("ID del canal externo")

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

    def _send_to_provider(self, message, provider_name: str = "Botpress"):
        """
        Sends a message to the specified provider using the ProviderFileHandler.
        Args:
            message: The message record to be sent.
            provider_name (str, optional): The name of the provider to send the message to. Defaults to "Botpress".
        Side Effects:
            Updates the 'provider_delivery_status' field of the message to "sent" if successful,
            or "failed" if an exception occurs.
        Logs:
            Errors encountered during message sending are logged with the provider name and exception details.
        """
        handler = ProviderFileHandler(provider_name, self.env)
        try:
            handler.send_message(message, self.provider_metadata)
            message.write({"provider_delivery_status": "sent"})
        except Exception as e:
            message.write({"provider_delivery_status": "failed"})
            _logger.error(
                f"Error sending message to provider {provider_name}: {e}")

    def _safe_add_members(self, partner_ids):
        """
        Safely adds the given partner IDs as members to the channel.
        This method checks for existing members and only attempts to add new ones.
        It handles potential database integrity errors due to duplicate entries,
        logging warnings and falling back to adding members individually if necessary.
        Args:
            partner_ids (list[int]): List of partner IDs to add as members.
        Returns:
            None
        Raises:
            Exception: Re-raises unexpected exceptions encountered during member addition.
        """

        if not partner_ids:
            return

        existing_member_ids = set(
            self.channel_member_ids.mapped("partner_id.id"))

        new_partner_ids = [
            pid for pid in partner_ids if pid not in existing_member_ids]

        if not new_partner_ids:
            _logger.info(f"All partners already members of channel {self.id}")
            return

        try:

            with self.env.cr.savepoint():
                self.add_members(new_partner_ids)

        except IntegrityError as e:
            if "discuss_channel_member_partner_unique" in str(e):
                _logger.warning(
                    f"Duplicate member detected for channel {self.id}, ignoring: {e}"
                )
                self._add_members_individually(new_partner_ids)
            else:
                raise
        except Exception as e:
            _logger.error(
                f"Unexpected error adding members to channel {self.id}: {e}")
            raise

    def _add_members_individually(self, partner_ids):
        """
        Adds each partner in the given list to the channel individually, handling potential integrity errors.

        For each partner ID in `partner_ids`, attempts to add the partner to the channel using a database savepoint.
        If the partner is already a member (detected by the 'discuss_channel_member_partner_unique' constraint),
        logs an informational message and skips adding. Other integrity errors are logged and re-raised.
        Any unexpected exceptions are also logged and re-raised.

        Args:
            partner_ids (list): List of partner IDs to add as members to the channel.

        Raises:
            IntegrityError: If an integrity error occurs that is not due to the partner already being a member.
            Exception: For any other unexpected errors during the addition process.
        """
        for partner_id in partner_ids:
            try:
                with self.env.cr.savepoint():
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

    @retry_on_transient_error(
        max_retries=3, initial_delay=0.4, catch_integrity_error=True
    )
    def find_or_create_channel(
        self,
        provider_name: str,
        channel_name: str,
        external_channel_id: str,
        partner_ids: list,
        extra_metadata=None,
    ):
        """
        Finds an existing chat channel by external_channel_id and provider_name, or creates a new one if not found.
        Ensures the channel has the correct partner members and metadata.

        Args:
            provider_name (str): The name of the provider (e.g., 'heynow', 'twilio').
            channel_name (str): The display name for the channel.
            external_channel_id (str): The external identifier for the channel (from provider).
            partner_ids (list): List of partner (user) IDs to be members of the channel.
            extra_metadata (dict, optional): Additional metadata for the provider.

        Returns:
            recordset: The found or newly created channel record.

        Raises:
            RetryableJobError: If a concurrent update is detected (database serialization error).
            Exception: For other errors, possibly after attempting a fallback channel lookup.
        """

        try:

            self.env.cr.execute(
                """
                SELECT id FROM discuss_channel
                WHERE external_channel_id = %s AND channel_type = 'chat' AND provider_name = %s AND active = true
                FOR UPDATE
                """,
                (external_channel_id, provider_name),
            )
            result = self.env.cr.fetchone()

            if result:
                channel = self.sudo().browse(result[0])
                _logger.info(
                    f"Found existing channel {channel.id} for external_id {external_channel_id}"
                )
                current_partner_ids = set(channel.channel_partner_ids.ids)
                expected_partner_ids = set(partner_ids)
                missing_partners = expected_partner_ids - current_partner_ids
                if missing_partners:
                    _logger.info(
                        f"Adding {len(missing_partners)} missing partners to channel {channel.id}"
                    )
                    channel._safe_add_members(list(missing_partners))
                extra_partners = current_partner_ids - expected_partner_ids
                if extra_partners:
                    _logger.info(
                        f"Removing {len(extra_partners)} extra partners from channel {channel.id}"
                    )
                    try:
                        channel.write(
                            {
                                "channel_partner_ids": [
                                    (3, partner_id) for partner_id in extra_partners
                                ]
                            }
                        )
                    except Exception as e:
                        _logger.error(f"Error removing extra partners: {e}")
                if extra_metadata and not self._compare_provider_metadata(
                    channel.provider_metadata, extra_metadata
                ):
                    channel.write({"provider_metadata": extra_metadata})

                return channel
            _logger.info(
                f"Creating new channel for external_id {external_channel_id}")
            channel = self.sudo().create(
                {
                    "name": channel_name,
                    "channel_type": "chat",
                    "description": f"Canal de chat para {channel_name}",
                    "provider_name": provider_name,
                    "external_channel_id": external_channel_id,
                    "provider_metadata": extra_metadata or {},
                }
            )
            if partner_ids:
                initial_members = partner_ids
                channel._safe_add_members(initial_members)

            return channel

        except OperationalError as e:
            if "could not serialize access due to concurrent update" in str(e):
                _logger.warning(f"Concurrent update detected, retrying: {e}")
                raise RetryableJobError(
                    "Reintentando por error de concurrencia", seconds=5
                )
            else:
                _logger.error(
                    f"Operational error in find_or_create_channel: {e}")
                raise

        except IntegrityError as e:
            if "discuss_channel_member_partner_unique" in str(e):
                _logger.warning(
                    f"Integrity error with channel members, attempting fallback: {e}"
                )
                fallback_channel = self._find_fallback_channel(
                    external_channel_id, provider_name
                )
                if fallback_channel:
                    return fallback_channel
                else:
                    raise
            else:
                _logger.error(
                    f"Integrity error in find_or_create_channel: {e}")
                raise

        except Exception as e:
            _logger.error(f"Error creando o recuperando canal: {e}")
            fallback_channel = self._find_fallback_channel(
                external_channel_id, provider_name
            )
            if fallback_channel:
                return fallback_channel
            else:
                raise

    def _find_fallback_channel(self, external_channel_id, provider_name):
        """
        Searches for a fallback chat channel in the 'discuss.channel' model based on the given external channel ID and provider name.
        Args:
            external_channel_id (str): The external identifier of the channel to search for.
            provider_name (str): The name of the provider associated with the channel.
        Returns:
            discuss.channel or None: The found fallback channel record if one exists and is active, otherwise None.
        Logs:
            - Info: When a fallback channel is found.
            - Error: If an exception occurs during the search.
        """

        try:
            with self.env.registry.cursor() as new_cr:
                new_env = self.env(cr=new_cr)
                fallback_channel = (
                    new_env["discuss.channel"]
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
                    return self.sudo().browse(fallback_channel.id)

        except Exception as e:
            _logger.error(f"Error finding fallback channel: {e}")

        return None

    def _compare_provider_metadata(self, current_metadata, new_metadata):
        try:
            current_str = json.dumps(current_metadata or {}, sort_keys=True)
            new_str = json.dumps(new_metadata or {}, sort_keys=True)
            return current_str == new_str
        except Exception as e:
            _logger.error(f"Error comparing metadata: {e}")
            return False
