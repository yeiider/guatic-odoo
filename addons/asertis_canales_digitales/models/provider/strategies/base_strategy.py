from ..handlers.message_builder import MessageProxy
from abc import ABC, abstractmethod
from enum import Enum
import logging

_logger = logging.getLogger(__name__)


class MultipleFilesStrategy(Enum):
    """Estrategias disponibles para manejo de múltiples archivos"""

    SINGLE_REQUEST = "single_request"  # Una sola petición con todos los archivos
    TEXT_FIRST = "text_first"  # Texto primero, luego archivos
    FILES_FIRST = "files_first"  # Archivos primero, luego texto
    FILES_WITH_TEXT = "files_with_text"  # Cada archivo incluye el texto
    INTERLEAVED = "interleaved"


class MessageType(Enum):
    """Tipos de mensaje para logging y control"""

    TEXT_ONLY = "text_only"
    FILE_ONLY = "file_only"
    FILE_WITH_TEXT = "file_with_text"
    COMPLETE = "complete"


class BaseFileStrategy(ABC):
    """Clase base abstracta para estrategias de manejo de archivos"""

    def __init__(
        self,
        sender_callback,
        provider,
        webhook_url,
        headers,
        provider_name,
        chat_provider_metadata,
    ):
        self.sender_callback = sender_callback
        self.provider = provider
        self.webhook_url = webhook_url
        self.headers = headers
        self.provider_name = provider_name
        self.chat_provider_metadata = chat_provider_metadata

    @abstractmethod
    def execute(self, message) -> bool:
        """Ejecutar la estrategia de envío"""
        pass

    def _send_message(
        self, message_proxy: MessageProxy, message_type: MessageType, index: int = 0
    ) -> bool:
        """Método helper para enviar un mensaje"""
        try:
            payload = self.provider.get_payload(
                message_proxy, self.chat_provider_metadata
            )
            request_id = (
                f"{message_type.value}_{index}" if index > 0 else message_type.value
            )

            return self.sender_callback(
                self.webhook_url, payload, self.headers, self.provider_name, request_id
            )
        except (OSError, ValueError) as e:
            _logger.error("Error sending %s: %s", message_type.value, str(e))
            return False
