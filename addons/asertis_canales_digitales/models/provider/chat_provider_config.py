from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class ChatProviderConfig:
    """
    Represents the configuration for a chat provider integration.

    Attributes:
        id (int): Unique identifier for the chat provider configuration.
        name (str): Name of the chat provider.
        provider_type (str): Type of the chat provider (e.g., 'slack', 'teams').
        is_active (bool): Indicates whether the provider configuration is active.
        base_url (str): Base URL for the chat provider's API.
        allowed_channel_ids (List[Dict[str, Any]]): List of allowed channel identifiers and their metadata.
        auth_token (str): Authentication token used for API requests. Defaults to an empty string.
        config_extra (Optional[Dict[str, Any]]): Additional configuration parameters specific to the provider.
    """

    id: int
    name: str
    provider_type: str
    is_active: bool
    base_url: str
    allowed_channel_ids: List[Dict[str, Any]]
    auth_token: str = ""
    config_extra: Optional[Dict[str, Any]] = None
