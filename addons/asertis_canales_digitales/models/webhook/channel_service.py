from utils.webhook_logger import WebhookLogger
from ..exceptions.webhook_exceptions import ChannelCreationError

import logging

_logger = logging.getLogger(__name__)


class ChannelManagementService:
    """Service for managing discussion channels from webhook events"""

    def __init__(self, env):
        self.env = env

    def find_or_create_channel(self, provider_name, payload, partner):
        """
        Find or create a discussion channel for the webhook.

        Args:
            provider_name (str): Name of the webhook provider
            payload: Webhook payload containing channel information
            partner (res.partner): The partner associated with the channel

        Returns:
            discuss.channel: The found or created channel
        """
        try:
            # Get internal users for the channel
            internal_users_ids = self._get_internal_users_by_ability(
                payload, provider_name
            )

            # Build member list
            members = self._build_members_list(partner, internal_users_ids)

            # Get channel configuration
            channel_config = self._get_channel_config(payload, provider_name)

            # Create or find channel
            channel = self.env["discuss.channel"].find_or_create_channel(
                provider_name=provider_name,
                channel_name=channel_config["name"],
                partner_ids=members,
                external_channel_id=payload.user_id,
                icon_name=channel_config["icon_name"],
                extra_metadata=channel_config["metadata"],
            )

            if not channel:
                raise ChannelCreationError("Channel could not be found or created")

            WebhookLogger.log_channel_processed(channel.id, channel_config["name"])
            return channel

        except Exception as e:
            raise ChannelCreationError(f"Error processing channel: {str(e)}")

    def _get_internal_users_by_ability(self, payload, provider_name):
        """Get internal user IDs based on ability/skill"""
        ability = getattr(payload, "ability", None)
        if not ability:
            # Return default admin user if no ability specified
            admin_user = self._get_admin_user()
            return [admin_user.id]

        # Search for users with specific ability
        internal_users = (
            self.env["res.partner"]
            .sudo()
            .search(
                [
                    ("provider_skill_ids.name", "=", ability),
                    ("provider_skill_ids.provider_id.name", "=", provider_name),
                    ("provider_skill_ids.active", "=", True),
                ]
            )
        )

        internal_users_ids = internal_users.ids

        WebhookLogger.log_internal_users_found(
            len(internal_users_ids), ability, provider_name
        )

        # Fallback to admin user if no users found
        if not internal_users_ids:
            admin_user = self._get_admin_user()
            internal_users_ids = [admin_user.id]

        return internal_users_ids

    def _build_members_list(self, partner, internal_users_ids):
        """Build the list of channel members"""
        admin_user = self._get_admin_user()
        members = [partner.id, admin_user.id] + internal_users_ids

        # Remove duplicates while preserving order
        return list(dict.fromkeys(members))

    def _get_channel_config(self, payload, provider_name):
        """Get channel configuration from payload"""
        channel_name = getattr(payload, "channel_name", None) or provider_name

        icon_name = provider_name  # Default icon name
        if hasattr(payload, "channel_config") and hasattr(
            payload.channel_config, "type"
        ):
            icon_name = payload.channel_config.type.value

        metadata = getattr(payload, "metadata", {}) or {}

        return {
            "name": channel_name,
            "icon_name": icon_name,
            "metadata": metadata,
        }

    def _get_admin_user(self):
        """Get the admin user partner"""
        return self.env.ref("base.user_admin").sudo().partner_id
