from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
from ..provider.provider import ProviderAuthentication, ProviderConfig
from ..provider.provider_type import ProviderType
from ..provider.chat_provider_config import ChatProviderConfig
from ..provider.chat_provider_model import ChatProviderModel
from ..payloads.base_event import BaseEvent


class ProviderService(ProviderAuthentication, ProviderConfig, ABC):
    """
    Clase abstracta base que define la interfaz común para todos los proveedores.
    Ahora obtiene la configuración automáticamente por tipo de proveedor.
    """

    def __init__(self, env, provider_type: ProviderType):
        self.provider_type = provider_type
        self.config = self._load_config()
        self.env = env
        if not self.config:
            raise ValueError(
                f"No se encontró configuración activa para el proveedor {provider_type.value}"
            )

    def _load_config(self) -> Optional[ChatProviderConfig]:
        """Carga la configuración desde la base de datos por tipo de proveedor."""
        return ChatProviderModel.get_active_provider_config(
            env=self.env, provider_type=self.provider_type.value
        )

    def reload_config(self):
        """Recarga la configuración desde la base de datos."""
        self.config = self._load_config()
        if not self.config:
            raise ValueError(
                f"No se encontró configuración activa para el proveedor {self.provider_type.value}"
            )

    def get_provider_type(self) -> ProviderType:
        """Obtener el tipo de proveedor."""
        return self.provider_type

    def get_provider_config(self) -> ChatProviderConfig:
        """Get the configuration metadata for the provider."""
        if self.config is None:
            raise ValueError(
                f"No se encontró configuración activa para el proveedor {self.provider_type.value}"
            )
        return self.config

    def get_allowed_channels(self) -> List[Dict[str, Any]]:
        """Obtener los canales permitidos para este proveedor."""
        if (
            self.config
            and getattr(self.config, "allowed_channel_ids", None) is not None
        ):
            return self.config.allowed_channel_ids
        return []

    def get_config_extra(self) -> Optional[Dict[str, Any]]:
        """Obtener configuración extra del proveedor."""
        if self.config and getattr(self.config, "config_extra", None) is not None:
            return self.config.config_extra
        return {}

    @abstractmethod
    def check_access_restrictions(self, payload: BaseEvent) -> Tuple[bool, str]:
        """
        Verifica si el acceso está restringido basado en el payload.

        :param payload: Información del mensaje o solicitud
        :return: (restringido: bool, mensaje: str)
        """
        pass
