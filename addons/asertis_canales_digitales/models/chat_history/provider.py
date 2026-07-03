from abc import ABC, abstractmethod
import json
import logging
from datetime import datetime
from typing import Dict,  Any, Optional, Tuple
from .types import ChatHistory


_logger = logging.getLogger(__name__)


class ChatHistoryProvider(ABC):
    """
    Clase abstracta base para todos los proveedores de historial de chat.
    Define la interfaz común y comportamientos base para todos los proveedores.
    """
    
    def __init__(self, provider_config: Dict[str, Any]):
        """
        Inicializa el proveedor con la configuración necesaria.
        
        Args:
            provider_config: Diccionario con la configuración del proveedor
        """
        self.provider_config = provider_config
        self.provider_type = provider_config.get('provider_type')
        self.provider_name = provider_config.get('name')
        self.base_url = provider_config.get('base_url')
        self.auth_token = provider_config.get('auth_token')
        self.extra_config = self._parse_extra_config(provider_config.get('config_extra', '{}'))
        self.history_config = self._parse_history_config(provider_config.get('historial_config', '{}'))
        
    def _parse_extra_config(self, config_str: str) -> Dict[str, Any]:
        """Parse configuración extra desde JSON string"""
        try:
            return json.loads(config_str) if config_str else {}
        except json.JSONDecodeError:
            _logger.warning(f"Invalid extra config JSON for provider {self.provider_name}")
            return {}
    
    def _parse_history_config(self, config_str: str) -> Dict[str, Any]:
        """Parse configuración de historial desde JSON string"""
        try:
            return json.loads(config_str) if config_str else {}
        except json.JSONDecodeError:
            _logger.warning(f"Invalid history config JSON for provider {self.provider_name}")
            return {}
    
    @abstractmethod
    def authenticate(self) -> Tuple[bool, Optional[str], Optional[datetime]]:
        """
        Autentica el proveedor si es necesario.
        
        Returns:
            Tuple[bool, Optional[str], Optional[datetime]]: 
            - success: True si la autenticación fue exitosa
            - token: Token de autenticación (si aplica)
            - expiration: Fecha de expiración del token (si aplica)
        """
        pass
    
    @abstractmethod
    def requires_authentication(self) -> bool:
        """
        Verifica si el proveedor requiere autenticación.
        
        Returns:
            bool: True si requiere autenticación
        """
        pass
    
    @abstractmethod
    def fetch_conversation_history(self, channel_id: str, external_channel_id: str, token: str, 
                                 page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Obtiene el historial de conversación del proveedor externo.
        
        Args:
            channel_id: ID del canal en Odoo
            external_channel_id: ID del canal en el proveedor externo
            page: Página actual (para paginación)
            limit: Límite de mensajes por página
            
        Returns:
            Dict con la respuesta raw del proveedor
        """
        pass
    
    @abstractmethod
    def format_to_standard(self, raw_response: Dict[str, Any]) -> ChatHistory:
        """
        Convierte la respuesta del proveedor al formato estándar.
        
        Args:
            raw_response: Respuesta raw del proveedor
            
        Returns:
            Dict con formato estándar:
            {
                "messages": [
                    {
                        "id": str,
                        "author_name": str,
                        "author_avatar": str,
                        "timestamp": str (ISO format),
                        "content": str,
                        "message_type": str ("chat", "system", "file", etc.),
                        "attachments": [
                            {
                                "id": str,
                                "filename": str,
                                "mimetype": str,
                                "size": int,
                                "download_url": str
                            }
                        ]
                    }
                ],
                "has_more": bool,
                "next_page": str,
                "total_count": int
            }
        """
        pass
    
    def validate_channel_data(self, channel_data: Dict[str, Any]) -> bool:
        """
        Valida que los datos del canal sean válidos para este proveedor.
        
        Args:
            channel_data: Datos del canal desde discuss.channel
            
        Returns:
            bool: True si los datos son válidos
        """
        required_fields = ['external_channel_id', 'provider_name']
        return all(field in channel_data and channel_data[field] for field in required_fields)
    
    def handle_api_error(self, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        Maneja errores de API y los convierte a formato estándar.
        
        Args:
            error: Excepción capturada
            context: Contexto adicional del error
            
        Returns:
            Dict con error formateado
        """
        error_message = f"Error en {self.provider_name}"
        if context:
            error_message += f" ({context})"
        
        _logger.error(f"{error_message}: {str(error)}")
        
        return {
            "success": False,
            "error": error_message,
            "error_details": str(error),
            "messages": [],
            "has_more": False,
            "next_page": None
        }
    
    def get_cache_key(self, channel_id: str, page: int = 1) -> str:
        """
        Genera clave única para cache.
        
        Args:
            channel_id: ID del canal
            page: Página actual
            
        Returns:
            str: Clave de cache
        """
        return f"chat_history_{self.provider_type}_{channel_id}_{page}"
    
    def should_cache_response(self) -> bool:
        """
        Determina si las respuestas de este proveedor deben ser cacheadas.
        
        Returns:
            bool: True si debe cachear
        """
        return self.history_config.get('enable_cache', True)
    
    def get_cache_expiry_minutes(self) -> int:
        """
        Obtiene tiempo de expiración del cache en minutos.
        
        Returns:
            int: Minutos de expiración
        """
        return self.history_config.get('cache_expiry_minutes', 30)

