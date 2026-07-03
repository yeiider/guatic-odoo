from datetime import datetime
from typing import Dict, Any, Optional


class ChatHistoryAuthManager:
    """
    Gestor de autenticación para proveedores de chat.
    Maneja tokens, expiración y almacenamiento seguro.
    """

    @staticmethod
    def save_auth_data(
        session, provider_type: str, token: str, expiration: Optional[datetime] = None
    ):
        """
        Guarda datos de autenticación en la sesión.

        Args:
            session: Sesión HTTP de Odoo
            provider_type: Tipo de proveedor
            token: Token de autenticación
            expiration: Fecha de expiración
        """
        auth_key = f"chat_auth_{provider_type}"
        auth_data = {
            "token": token,
            "expiration": expiration.isoformat() if expiration else None,
            "timestamp": datetime.now().isoformat(),
        }
        session[auth_key] = auth_data

    @staticmethod
    def get_auth_data(session, provider_type: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos de autenticación desde la sesión.

        Args:
            session: Sesión HTTP de Odoo
            provider_type: Tipo de proveedor

        Returns:
            Optional[Dict]: Datos de autenticación si existen
        """
        auth_key = f"chat_auth_{provider_type}"
        return session.get(auth_key)

    @staticmethod
    def is_token_valid(session, provider_type: str) -> bool:
        """
        Verifica si el token almacenado sigue siendo válido.

        Args:
            session: Sesión HTTP de Odoo
            provider_type: Tipo de proveedor

        Returns:
            bool: True si el token es válido
        """
        auth_data = ChatHistoryAuthManager.get_auth_data(session, provider_type)

        if not auth_data or not auth_data.get("token"):
            return False

        expiration_str = auth_data.get("expiration")
        if expiration_str:
            expiration = datetime.fromisoformat(expiration_str)
            if datetime.now() >= expiration:
                return False

        return True

    @staticmethod
    def clear_auth_data(session, provider_type: str):
        """
        Limpia datos de autenticación de la sesión.

        Args:
            session: Sesión HTTP de Odoo
            provider_type: Tipo de proveedor
        """
        auth_key = f"chat_auth_{provider_type}"
        if auth_key in session:
            del session[auth_key]

    @staticmethod
    def get_auth_token(session, provider_type: str) -> Optional[str]:
        """
        Obtiene el token de autenticación almacenado.

        Args:
            session: Sesión HTTP de Odoo
            provider_type: Tipo de proveedor

        Returns:
            Optional[str]: Token de autenticación si existe
        """
        auth_data = ChatHistoryAuthManager.get_auth_data(session, provider_type)

        return auth_data.get("token") if auth_data else None
