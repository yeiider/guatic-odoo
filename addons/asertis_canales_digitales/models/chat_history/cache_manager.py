import pickle
import time
from typing import Dict, Any, Optional

class SimpleCacheManager:
    """
    Gestor simple de cache usando la sesión de Odoo.
    En producción, considera usar Redis o Memcached.
    """
    
    @staticmethod
    def _get_cache_key(provider_type: str, channel_id: int, page: int) -> str:
        """Genera clave única para cache."""
        return f"chat_cache_{provider_type}_{channel_id}_{page}"
    
    @staticmethod
    def get_cached_data(session, provider_type: str, channel_id: int, 
                       page: int, ttl_minutes: int = 30) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos del cache si están disponibles y no han expirado.
        """
        cache_key = SimpleCacheManager._get_cache_key(provider_type, channel_id, page)
        cached_entry = session.get(cache_key)
        
        if not cached_entry:
            return None
            
        # Verificar expiración
        cache_time = cached_entry.get("timestamp", 0)
        current_time = time.time()
        
        if (current_time - cache_time) > (ttl_minutes * 60):
            # Cache expirado
            del session[cache_key]
            return None
            
        return cached_entry.get("data")
    
    @staticmethod
    def save_to_cache(session, provider_type: str, channel_id: int, 
                     page: int, data: Dict[str, Any]):
        """
        Guarda datos en cache con timestamp.
        """
        cache_key = SimpleCacheManager._get_cache_key(provider_type, channel_id, page)
        cache_entry = {
            "data": data,
            "timestamp": time.time()
        }
        session[cache_key] = cache_entry
    
    @staticmethod
    def clear_cache_for_channel(session, provider_type: str, channel_id: int):
        """
        Limpia todo el cache para un canal específico.
        """
        prefix = f"chat_cache_{provider_type}_{channel_id}_"
        keys_to_delete = [key for key in session.keys() if key.startswith(prefix)]
        
        for key in keys_to_delete:
            del session[key]

# Actualizar métodos en el controlador:
def _get_cached_data(self, provider, channel_id: int, page: int) -> Optional[Dict[str, Any]]:
    """Obtiene datos desde cache si están disponibles."""
    return SimpleCacheManager.get_cached_data(
        request.session,
        provider.provider_type,
        channel_id,
        page,
        provider.get_cache_expiry_minutes()
    )

def _save_to_cache(self, provider, channel_id: int, page: int, data: Dict[str, Any]):
    """Guarda datos en cache."""
    SimpleCacheManager.save_to_cache(
        request.session,
        provider.provider_type,
        channel_id,
        page,
        data
    )