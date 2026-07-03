from typing import Optional, List, Dict
from dataclasses import dataclass
from .chat_provider_config import ChatProviderConfig


class ChatProviderModel:
    """Simulación del modelo Odoo chat.provider"""

    @staticmethod
    def get_active_provider_config(
        env, provider_type: str
    ) -> Optional[ChatProviderConfig]:
        """Obtiene la configuración activa para un tipo de proveedor específico."""

        provider = (
            env["chat.provider"]
            .sudo()
            .search(
                [("provider_type", "=", provider_type), ("is_active", "=", True)],
                limit=1,
            )
        )

        if provider:
            return ChatProviderConfig(
                id=provider.id,
                name=provider.name,
                provider_type=provider.provider_type,
                is_active=provider.is_active,
                base_url=provider.base_url,
                allowed_channel_ids=[
                    {"id": ch.id, "name": ch.name}
                    for ch in provider.allowed_channel_ids
                ],
                auth_token=provider.get_auth_token(),
                config_extra=provider.get_config_extra_dict(),
            )
        return None
