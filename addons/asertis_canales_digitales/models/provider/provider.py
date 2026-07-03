from abc import ABC, abstractmethod
from typing import Dict, Any
from .chat_provider_config import ChatProviderConfig


class Provider(ABC):
    """
    Abstract base class for all providers.
    """

    @abstractmethod
    def get_url(self, config=None) -> str:
        """
        Get the URL for the provider's API.

        :param url_base: Base URL from system configuration
        :param config: Additional configuration data
        :return: Complete URL as string
        """
        pass

    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """
        Get the headers required for API requests.

        :return: Dictionary of headers
        """
        pass

    @abstractmethod
    def get_payload(
        self, message: Dict[str, Any], config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get the payload to be sent to the provider.

        :param message: Odoo message object
        :param channel: Odoo channel object
        :param config: Configuration metadata from channel
        :return: Dictionary representing the payload
        """
        pass

    @classmethod
    def clear_html_message(self, body) -> str:
        """
        Convierte el contenido HTML del mail.message.body en texto plano apto para WhatsApp.
        """
        from bs4 import BeautifulSoup
        from markupsafe import Markup

        if isinstance(body, Markup):
            body = str(body)

        soup = BeautifulSoup(body, "html.parser")

        for img in soup.find_all("img"):
            img.decompose()

        for tag in soup(["script", "style"]):
            tag.decompose()

        for span in soup.find_all("span"):
            if not span.get_text(strip=True):
                span.decompose()

        text = soup.get_text(separator=" ", strip=True)

        return " ".join(text.split())

    @abstractmethod
    def get_config_provider(self) -> ChatProviderConfig:
        """
        Get the configuration metadata for the provider.

        :return: Dictionary containing configuration metadata
        """
        pass


class ProviderAuthentication(ABC):
    """
    Abstract base class for all providers.
    """

    @abstractmethod
    def get_auth_token(self) -> str:
        """
        Get the auth token for the provider.

        :return: auth token
        """
        pass

    @abstractmethod
    def get_base_url(self) -> str:
        """
        Get the base url for the provider.

        :return: base url
        """
        pass

    @abstractmethod
    def get_is_valid(self) -> bool:
        """
        Get the is valid for the provider.

        :return: is valid
        """
        pass

    @abstractmethod
    def get_is_valid_channel(self, channel_name) -> bool:
        """
        Get the is valid for the provider.

        :return: is valid
        """
        pass


class ProviderConfig(ABC):
    """
    Abstract base class for all providers.
    """

    @abstractmethod
    def get_provider_config(self) -> ChatProviderConfig:
        """
        Get the configuration metadata for the provider.

        :return: Dictionary containing configuration metadata
        """
        pass
