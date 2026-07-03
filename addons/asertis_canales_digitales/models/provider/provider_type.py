from enum import Enum
from typing import List


class ProviderType(Enum):
    """
    Enum representa los diferentes tipos de proveedores de servicios de mensajería.
    """

    BOTPRESS = "botpress"
    HEYNOW = "heynow"
    TWILIO = "twilio"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    FACEBOOK = "facebook"
    SLACK = "slack"
    DISCORD = "discord"

    LINE = "line"

    @classmethod
    def get_all_types(cls) -> List[str]:
        """Devuelve una lista de todos los tipos de proveedores como cadenas."""
        return [provider_type.value for provider_type in cls]

    @classmethod
    def get_type(cls, value: str) -> "ProviderType":
        """Devuelve el tipo de proveedor correspondiente a un valor dado."""
        for provider_type in cls:
            if provider_type.value == value:
                return provider_type
        raise ValueError(f"Invalid provider type: {value}")
