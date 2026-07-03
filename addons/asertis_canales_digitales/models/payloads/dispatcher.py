from ..heynow.payload import HeynowPayload

from .base_event import BaseEvent
from ..provider.provider_type import ProviderType


class WebhookDispatcher:
    """
    Dispatcher class for handling webhook payloads from different providers.

    Attributes:
        provider_name (str): The name of the webhook provider (e.g., "heynow").
        raw_payload (dict): The raw payload data received from the webhook.

    Methods:
        extract_event() -> BaseEvent:
            Extracts and returns a BaseEvent object from the raw payload based on the provider.
            Raises a ValueError if the provider is unsupported.
    """

    def __init__(self, provider_name: str, raw_payload: dict):
        self.provider_name = provider_name
        self.raw_payload = raw_payload

    def extract_event(self) -> BaseEvent:
        """
        Extracts and returns a BaseEvent object from the raw payload based on the provider name.

        Returns:
            BaseEvent: The extracted event object corresponding to the provider.

        Raises:
            ValueError: If the provider is not supported.
        """
        if self.provider_name == ProviderType.HEYNOW.value:
            return HeynowPayload(self.raw_payload).extract()

        else:
            raise ValueError(f"Unsupported provider: {self.provider_name}")
