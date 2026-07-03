import logging

from typing import Dict, List, Any

# Import or define ChatHistoryProvider
from .provider import ChatHistoryProvider  
from ..heynow.chat_history import HeyNowChatHistoryProvider


_logger = logging.getLogger(__name__)


class ChatHistoryProviderFactory:
    """
    Factory para crear instancias de proveedores específicos.
    """

    _providers = {
        "heynow": HeyNowChatHistoryProvider,
    }

    @classmethod
    def register_provider(cls, provider_type: str, provider_class: type):
        """
        Registra un nuevo proveedor.

        Args:
            provider_type: Tipo de proveedor
            provider_class: Clase del proveedor
        """
        cls._providers[provider_type] = provider_class

    @classmethod
    def create_provider(
        cls, provider_config: Dict[str, Any]
    ) -> ChatHistoryProvider:
        """
        Crea una instancia del proveedor apropiado.

        Args:
            provider_config: Configuración del proveedor

        Returns:
            AbstractChatHistoryProvider: Instancia del proveedor

        Raises:
            ValueError: Si el tipo de proveedor no está registrado
        """
        provider_type = provider_config.get("provider_type")

        if provider_type not in cls._providers:
            raise ValueError(f"Proveedor no registrado: {provider_type}")

        provider_class = cls._providers[provider_type]
        return provider_class(provider_config)

    @classmethod
    def get_supported_providers(cls) -> List[str]:
        """
        Obtiene lista de proveedores soportados.

        Returns:
            List[str]: Lista de tipos de proveedores
        """
        return list(cls._providers.keys())
