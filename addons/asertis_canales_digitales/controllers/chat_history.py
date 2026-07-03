import logging
from datetime import datetime
from typing import Dict, Any, Optional

from odoo import http, _
from odoo.http import request, Response
from odoo.exceptions import ValidationError, AccessError

# Import the ChatHistoryProviderFactory from its module
from ..models.chat_history.factory import ChatHistoryProviderFactory
from ..models.chat_history.auth_manager import ChatHistoryAuthManager

_logger = logging.getLogger(__name__)




class ChatHistoryController(http.Controller):
    """
    Controlador para manejar peticiones de historial de chat.
    """

    @http.route(
        "/api/chat/history/<int:channel_id>", type="json", auth="user", methods=["POST"]
    )
    def get_conversation_history(
        self,
        channel_id: int,
        page: int = 1,
        limit: int = 50,
        force_refresh: bool = False,
    ):
        """
        Obtiene el historial de conversación de un canal específico.

        Args:
            channel_id: ID del canal en Odoo
            page: Página de resultados (default: 1)
            limit: Límite de mensajes por página (default: 50, max: 100)
            force_refresh: Forzar actualización ignorando cache

        Returns:
            Dict con el historial formateado
        """
        try:
            # Validar parámetros
            if not channel_id or channel_id <= 0:
                return self._error_response("ID de canal inválido")

            limit = max(1, min(limit, 100))  # Limitar entre 1 y 100
            page = max(1, page)

            # Obtener datos del canal
            channel_data = self._get_channel_data(channel_id)
            if not channel_data:
                return self._error_response("Canal no encontrado")

            # Verificar permisos
            if not self._check_channel_access(channel_id):
                return self._error_response(
                    "Sin permisos para acceder al canal", status_code=403
                )

            # Obtener configuración del proveedor
            provider_config = self._get_provider_config(
                channel_data.get("provider_name")
            )
            if not provider_config:
                return self._success_response(
                    {
                        "messages": [],
                        "has_more": False,
                        "next_page": None,
                        "total_count": 0,
                        "info": "No hay proveedor configurado para este canal",
                    }
                )

            # Crear instancia del proveedor
            provider = ChatHistoryProviderFactory.create_provider(provider_config)

            # Validar datos del canal con el proveedor
            if not provider.validate_channel_data(channel_data):
                return self._error_response(
                    "Datos del canal inválidos para este proveedor"
                )

            # Manejar autenticación si es necesaria
            auth_success = self._handle_authentication(provider)
            if not auth_success:
                return self._error_response("Error de autenticación con el proveedor")

            # Verificar cache si no es refresh forzado
            if not force_refresh and provider.should_cache_response():
                cached_data = self._get_cached_data(provider, channel_id, page)
                if cached_data:
                    return self._success_response(cached_data)

            # Obtener historial del proveedor
            external_channel_id = channel_data.get("external_channel_id")
            token = ChatHistoryAuthManager.get_auth_token(
                request.session, provider.provider_type
            )
            raw_response = provider.fetch_conversation_history(
               channel_id=str(channel_id), token=token, external_channel_id=external_channel_id
            )

            # Formatear respuesta al estándar
            formatted_response = provider.format_to_standard(raw_response)

            # Guardar en cache si está habilitado
            if provider.should_cache_response():
                self._save_to_cache(provider, channel_id, page, formatted_response)

            # Actualizar metadatos del canal
            self._update_channel_metadata(
                channel_id,
                {
                    "last_history_fetch": datetime.now().isoformat(),
                    "provider_type": provider.provider_type,
                },
            )

            return self._success_response(formatted_response)

        except ValidationError as ve:
            _logger.warning(f"Validation error in get_conversation_history: {str(ve)}")
            return self._error_response(str(ve))

        except Exception as e:
            _logger.error(f"Unexpected error in get_conversation_history: {str(e)}")
            return self._error_response("Error interno del servidor", status_code=500)

    @http.route(
        "/api/chat/auth/refresh/<string:provider_type>",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def refresh_authentication(self, provider_type: str):
        """
        Refresca la autenticación de un proveedor específico.

        Args:
            provider_type: Tipo de proveedor

        Returns:
            Dict con resultado de la autenticación
        """
        try:
            # Obtener configuración del proveedor
            provider_config = self._get_provider_config_by_type(provider_type)
            if not provider_config:
                return self._error_response("Proveedor no configurado")

            # Crear instancia del proveedor
            provider = ChatHistoryProviderFactory.create_provider(provider_config)

            # Limpiar autenticación existente
            ChatHistoryAuthManager.clear_auth_data(request.session, provider_type)

            # Realizar nueva autenticación
            success, token, expiration = provider.authenticate()

            if success:
                # Guardar nueva autenticación
                ChatHistoryAuthManager.save_auth_data(
                    request.session, provider_type, token, expiration
                )

                return self._success_response(
                    {
                        "authenticated": True,
                        "provider_type": provider_type,
                        "expiration": expiration.isoformat() if expiration else None,
                        "message": "Autenticación exitosa",
                    }
                )
            else:
                return self._error_response("Falló la autenticación con el proveedor")

        except Exception as e:
            _logger.error(f"Error in refresh_authentication: {str(e)}")
            return self._error_response("Error refrescando autenticación")

    @http.route("/api/chat/providers/status", type="json", auth="user", methods=["GET"])
    def get_providers_status(self):
        """
        Obtiene el estado de todos los proveedores configurados.

        Returns:
            Dict con estado de proveedores
        """
        try:
            providers_status = []

            # Obtener todos los proveedores activos
            ChatProvider = request.env["chat.provider"].sudo()
            providers = ChatProvider.search([("is_active", "=", True)])

            for provider_record in providers:
                try:
                    # Crear instancia del proveedor
                    provider_config = self._build_provider_config(provider_record)
                    provider = ChatHistoryProviderFactory.create_provider(
                        provider_config
                    )

                    # Verificar estado de autenticación
                    requires_auth = provider.requires_authentication()
                    is_authenticated = False

                    if requires_auth:
                        is_authenticated = ChatHistoryAuthManager.is_token_valid(
                            request.session, provider.provider_type
                        )
                    else:
                        is_authenticated = True  # No requiere autenticación

                    providers_status.append(
                        {
                            "provider_type": provider.provider_type,
                            "provider_name": provider.provider_name,
                            "requires_authentication": requires_auth,
                            "is_authenticated": is_authenticated,
                            "supports_history": True,  # Si está aquí, soporta historial
                            "last_check": datetime.now().isoformat(),
                        }
                    )

                except Exception as e:
                    _logger.warning(
                        f"Error checking provider {provider_record.provider_type}: {str(e)}"
                    )
                    providers_status.append(
                        {
                            "provider_type": provider_record.provider_type,
                            "provider_name": provider_record.name,
                            "requires_authentication": True,
                            "is_authenticated": False,
                            "supports_history": False,
                            "error": str(e),
                            "last_check": datetime.now().isoformat(),
                        }
                    )

            return self._success_response(
                {
                    "providers": providers_status,
                    "supported_types": ChatHistoryProviderFactory.get_supported_providers(),
                }
            )

        except Exception as e:
            _logger.error(f"Error in get_providers_status: {str(e)}")
            return self._error_response("Error obteniendo estado de proveedores")

    # Métodos auxiliares privados

    def _get_channel_data(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene datos del canal desde la base de datos."""
        try:
            DiscussChannel = request.env["discuss.channel"].sudo()
            channel = DiscussChannel.browse(channel_id)

            if not channel.exists():
                return None

            return {
                "id": channel.id,
                "name": channel.name,
                "provider_name": channel.provider_name,
                "external_channel_id": channel.external_channel_id,
                "provider_metadata": channel.provider_metadata or {},
            }

        except Exception as e:
            _logger.error(f"Error getting channel data: {str(e)}")
            return None

    def _check_channel_access(self, channel_id: int) -> bool:
        """
        Verifica si el usuario tiene permisos para acceder al canal.

        Args:
            channel_id: ID del canal

        Returns:
            bool: True si tiene acceso
        """
        try:
            DiscussChannel = request.env["discuss.channel"]
            channel = DiscussChannel.browse(channel_id)

            # Verificar si el canal existe y el usuario tiene acceso
            if not channel.exists():
                return False

            # Verificar membresía del usuario en el canal
            current_user = request.env.user
            member = request.env["discuss.channel.member"].search(
                [
                    ("channel_id", "=", channel_id),
                    ("partner_id", "=", current_user.partner_id.id),
                ]
            )

            return bool(member)

        except AccessError:
            return False
        except Exception as e:
            _logger.error(f"Error checking channel access: {str(e)}")
            return False

    def _get_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene la configuración del proveedor por nombre.

        Args:
            provider_name: Nombre del proveedor

        Returns:
            Dict con configuración del proveedor
        """
        try:
            ChatProvider = request.env["chat.provider"].sudo()
            provider = ChatProvider.search(
                [("name", "=", provider_name), ("is_active", "=", True)], limit=1
            )

            if not provider:
                return None

            return self._build_provider_config(provider)

        except Exception as e:
            _logger.error(f"Error getting provider config: {str(e)}")
            return None

    def _get_provider_config_by_type(
        self, provider_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene la configuración del proveedor por tipo.

        Args:
            provider_type: Tipo del proveedor

        Returns:
            Dict con configuración del proveedor
        """
        try:
            ChatProvider = request.env["chat.provider"].sudo()
            provider = ChatProvider.search(
                [("provider_type", "=", provider_type), ("is_active", "=", True)],
                limit=1,
            )

            if not provider:
                return None

            return self._build_provider_config(provider)

        except Exception as e:
            _logger.error(f"Error getting provider config by type: {str(e)}")
            return None

    def _build_provider_config(self, provider_record) -> Dict[str, Any]:
        """
        Construye la configuración del proveedor desde el registro.

        Args:
            provider_record: Registro del proveedor

        Returns:
            Dict con configuración
        """
        return {
            "provider_type": provider_record.provider_type,
            "name": provider_record.name,
            "base_url": provider_record.base_url,
            "auth_token": provider_record.auth_token,
            "config_extra": provider_record.config_extra or "{}",
            "historial_config": provider_record.historial_config or "{}",
        }

    def _handle_authentication(self, provider) -> bool:
        """
        Maneja la autenticación del proveedor.

        Args:
            provider: Instancia del proveedor

        Returns:
            bool: True si la autenticación es exitosa
        """
        try:
            if not provider.requires_authentication():
                return True

            # Verificar token existente
            if ChatHistoryAuthManager.is_token_valid(
                request.session, provider.provider_type
            ):
                # Token válido, actualizar token del proveedor
                token = ChatHistoryAuthManager.get_auth_token(
                    request.session, provider.provider_type
                )
                if not token:
                    return False
                provider.auth_token = token
                return True

            # Realizar nueva autenticación
            success, token, expiration = provider.authenticate()

            if success:
                # Guardar token
                ChatHistoryAuthManager.save_auth_data(
                    request.session, provider.provider_type, token, expiration
                )
                provider.auth_token = token
                return True

            return False

        except Exception as e:
            _logger.error(
                f"Authentication error for provider {provider.provider_type}: {str(e)}"
            )
            return False

    def _get_cached_data(
        self, provider, channel_id: int, page: int
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos desde cache si están disponibles.

        Args:
            provider: Instancia del proveedor
            channel_id: ID del canal
            page: Página actual

        Returns:
            Dict con datos cacheados o None
        """
        # Implementar cache usando Redis, Memcached o cache de Odoo
        # Por ahora retorna None (sin cache)
        return None

    def _save_to_cache(
        self, provider, channel_id: int, page: int, data: Dict[str, Any]
    ):
        """
        Guarda datos en cache.

        Args:
            provider: Instancia del proveedor
            channel_id: ID del canal
            page: Página actual
            data: Datos a cachear
        """
        # Implementar guardado en cache
        pass

    def _update_channel_metadata(self, channel_id: int, metadata: Dict[str, Any]):
        """
        Actualiza metadatos del canal.

        Args:
            channel_id: ID del canal
            metadata: Metadatos a actualizar
        """
        try:
            DiscussChannel = request.env["discuss.channel"].sudo()
            channel = DiscussChannel.browse(channel_id)

            if channel.exists():
                current_metadata = channel.provider_metadata or {}
                current_metadata.update(metadata)
                channel.provider_metadata = current_metadata

        except Exception as e:
            _logger.error(f"Error updating channel metadata: {str(e)}")

    def _success_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera respuesta exitosa estándar.

        Args:
            data: Datos de respuesta

        Returns:
            Dict con respuesta formateada
        """
        return {"success": True, "data": data, "timestamp": datetime.now().isoformat()}

    def _error_response(self, message: str, status_code: int = 400) -> Dict[str, Any]:
        """
        Genera respuesta de error estándar.

        Args:
            message: Mensaje de error
            status_code: Código de estado HTTP

        Returns:
            Dict con error formateado
        """
        return {
            "success": False,
            "error": message,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat(),
        }
