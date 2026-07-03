from ..provider.provider_type import ProviderType
from ..services.provider_service import ProviderService
from ..payloads.base_event import BaseEvent
from typing import Tuple


class HeyNowProviderService(ProviderService):
    """
    HeyNowProviderService provides integration logic for the HeyNow provider.
    Inherits from:
        ProviderService
    Args:
        env: Odoo environment object.
        provider_type (ProviderType, optional): The type of provider. Defaults to ProviderType.HEYNOW.
    Attributes:
        env: The Odoo environment.
        config: Provider configuration, expected to have attributes like auth_token, base_url, is_active, and allowed_channel_ids.
    Methods:
        get_auth_token() -> str:
            Returns the authentication token from the provider configuration, or an empty string if not configured.
        get_base_url() -> str:
            Returns the base URL from the provider configuration, or an empty string if not configured.
        get_is_valid() -> bool:
            Checks if the provider configuration is valid (i.e., config exists, has auth_token, base_url, and is active).
        get_is_valid_channel(channel_name) -> bool:
            Checks if the given channel name is allowed according to the provider configuration.
    """

    def __init__(self, env, provider_type: ProviderType = ProviderType.HEYNOW):
        self.env = env
        super().__init__(env, provider_type)

    def get_auth_token(self) -> str:
        return self.config.auth_token if self.config is not None else ""

    def get_base_url(self) -> str:
        return self.config.base_url if self.config is not None else ""

    def get_is_valid(self) -> bool:
        return bool(
            self.config is not None
            and self.config.auth_token
            and self.config.base_url
            and self.config.is_active
        )

    def get_is_valid_channel(self, channel_name: str) -> bool:
        if self.config is None or not hasattr(self.config, "allowed_channel_ids"):
            return False
        allowed_channel_name = [
            str(ch.get("name", "")) for ch in self.config.allowed_channel_ids
        ]
        return str(channel_name) in allowed_channel_name

    def _get_excluded_platforms_ids(self) -> list:
        extra_config = self.get_config_extra()
        return extra_config.get("excludedPlatformsIds", []) if extra_config else []

    def _get_excluded_bot_ids(self) -> list:
        extra_config = self.get_config_extra()

        return extra_config.get("excludedBotsIds", []) if extra_config else []

    def check_access_restrictions(self, payload: BaseEvent) -> Tuple[bool, str]:
        """
        Check access restrictions for the HeyNow provider.
        This method should be implemented to define specific access control logic.
        Args:
            payload (BaseEvent): The event payload to check against access restrictions.
        Returns:
            Tuple[bool, str]: A tuple where the first element indicates if access is allowed,
                              and the second element is a message or reason for the decision.
        """
        is_restricted = False
        message = "Access granted"

        # Implement specific access restriction logic here
        excluded_platforms = self._get_excluded_platforms_ids()
        excluded_bots = self._get_excluded_bot_ids()
        metadata = payload.metadata if hasattr(payload, "metadata") else {}
        platform_id = metadata.get("platformId")
        bot_id = metadata.get("botId")

        if platform_id in excluded_platforms:
            is_restricted = True
            message = "Access denied: Platform is excluded."

        if bot_id in excluded_bots:
            is_restricted = True
            message = "Access denied: Bot is excluded."
        # Additional checks can be added here as needed
        return is_restricted, message
