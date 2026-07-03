import json
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from ..chat_history.provider import ChatHistoryProvider
from ..chat_history.types import ChatHistory, ChatHistoryMessage, HistoryAttachment

_logger = logging.getLogger(__name__)


class HeyNowChatHistoryProvider(ChatHistoryProvider):
    """
    Proveedor de historial de chat para HeyNow.
    """

    def __init__(self, provider_config: Dict[str, Any]):
        super().__init__(provider_config)

        # Configuraciones específicas de HeyNow
        self.historial_config = self.history_config

        # Headers por defecto para HeyNow API
        self.default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def authenticate(self) -> Tuple[bool, Optional[str], Optional[datetime]]:
        """
        Autentica con HeyNow API.
        """
        try:

            # Verificar que el API key funcione haciendo una petición de prueba
            url = "https://api.heynowbots.com/api/login"
            headers = {"Content-Type": "application/json"}
            payload = json.dumps(
                {
                    "name": self.historial_config.get("username", ""),
                    "password": self.historial_config.get("password", ""),
                }
            )

            response = requests.post(url, headers=headers, data=payload, timeout=30)
            _logger.info("HeyNow auth response: %s", response)

            if response.status_code == 200:
                # HeyNow devuelve un token de acceso que expira en 1 día
                expiration = datetime.now() + timedelta(days=1)
                return True, response.json().get("token"), expiration
            else:
                _logger.error(
                    f"HeyNow auth failed: {response.status_code} - {response.text}"
                )
                return False, None, None

        except requests.exceptions.RequestException as e:
            _logger.error(f"HeyNow authentication error: {str(e)}")
            return False, None, None

    def requires_authentication(self) -> bool:
        """
        HeyNow requiere autenticación vía API key.
        """
        return True

    def fetch_conversation_history(
        self,
        channel_id: str,
        external_channel_id: str,
        token: str,
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Obtiene el historial de conversación desde HeyNow API.
        """
        try:
            # Construir URL de la API de HeyNow
            url = "https://api.heynowbots.com/api/report/session"
            begin = self.historial_config.get("begin", "2023-01-01")
            end = self.historial_config.get("end", datetime.now().strftime("%Y-%m-%d"))
            page_size = self.historial_config.get("pageSize", 10)

            # Parámetros de la petición
            params = {
                "begin": begin,
                "end": end,
                "pageSize": page_size,
                "contact": external_channel_id,
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }

            response = requests.get(url, headers=headers, params=params, timeout=50)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error fetching HeyNow history: {str(e)}")
            return self.handle_api_error(e, "fetch_conversation_history")

    def format_to_standard(self, raw_response: Dict[str, Any]) -> ChatHistory:
        """
        Convierte la respuesta de HeyNow al formato estándar.
        """
        try:
            messages = []
            for data in raw_response.get("data", []):
                source = data.get("_source", {})

                raw_chats = self._get_chats(source=source)
                bot_actor = self._get_bot_name(source=source)
                agents_list = self._get_agents_list(source=source)
                contact_name = self._get_contact_name(source=source)

                for raw_chat in raw_chats:
                    if not self._is_process_chat(
                        raw_chat
                    ) or not self._is_valid_content(raw_chat):
                        continue
                    # Formatear attachments
                    raw_attachments = raw_chat.get("metaData", {}).get("temporal", [])

                    attachments = []
                    for raw_attachment in raw_attachments:
                        attachment = HistoryAttachment(
                            id=str(raw_attachment.get("temporalId", "")),
                            filename=raw_attachment.get("name", ""),
                            mimetype=raw_attachment.get("mimeType", ""),
                            size=raw_attachment.get("size", 0),
                            download_url=raw_attachment.get("urlFileshare", ""),
                        )
                        attachments.append(attachment)

                    type_message = len(attachments) > 0 and "file" or "chat"
                    author_name = contact_name
                    incoming = raw_chat.get("incoming", False)
                    if not incoming:
                        author_name = bot_actor
                    if (
                        incoming
                        and "ability" in raw_chat
                        and raw_chat.get("ability") != ""
                    ):
                        agent_info = self._get_agent_by_id(
                            agents_list, raw_chat.get("idAgent", -1)
                        )
                        author_name = agent_info.get(
                            "name",
                            f"Agente {raw_chat.get('idAgent', '')}",
                        )
                    # Crear mensaje estándar
                    message = ChatHistoryMessage(
                        id=str(raw_chat.get("_id", "")),
                        author_name=author_name,
                        author_avatar=raw_chat.get("author", {}).get("avatar_url", ""),
                        timestamp=self._parse_heynow_timestamp(
                            raw_chat.get("date", "")
                        ),
                        content=raw_chat.get("message", ""),
                        message_type=self._map_heynow_message_type(type_message),
                        attachments=attachments,
                    )
                    messages.append(message)

            # Información de paginación
            pagination = raw_response.get("scroll", {})

            return ChatHistory(
                messages=messages,
                has_more=pagination.get("length", 0) > 0,
                next_page=pagination.get("id", ""),
                total_count=pagination.get("total", {}).get("value", 0),
            ).to_json()

        except Exception as e:
            _logger.error(f"Error formatting HeyNow response: {str(e)}")
            return ChatHistory(
                messages=[], has_more=False, next_page="", total_count=0
            ).to_json()

    def _get_agents_list(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de agentes de la conversación.
        """
        outcoming = source.get("messages", {}).get("outcoming", [])
        agents_list = []
        for out in outcoming:
            if "agents" in out:
                for agent in out["agents"]:
                    agents_list.append(agent)

        return agents_list

    def _get_chats(self, source: Dict[str, Any]) -> Dict[str, Any]:

        return source.get("chat", [])

    def _get_contact_name(self, source: Dict[str, Any]) -> str:
        """
        Obtiene el nombre del contacto de la conversación.
        """
        return source.get("agendaName", f"Usuario {source.get('clientId', '')}")

    def _get_bot_name(self, source: Dict[str, Any]) -> str:
        """
        Obtiene el nombre del bot de la conversación.
        """
        return source.get("bot", {}).get("name", "")

    def _is_valid_content(self, source: Dict[str, Any]) -> bool:
        """
        Verifica si el contenido del mensaje es válido.
        """
        if not source:
            return False

        if isinstance(source, dict):
            # Verificar si el mensaje es un archivo o un texto
            existe_temporal = "temporal" in source.get("metaData", {})
            existe_mensaje = "message" in source
            if not existe_temporal and not existe_mensaje:
                return False
            return True

        return True

    def _is_process_chat(self, source: Dict[str, Any]) -> bool:
        """
        Verifica si el chat es procesable teniendo si existe la propiedad de incoming.
        """
        if not source:
            return False
        if isinstance(source, dict):
            return "incoming" in source
        return hasattr(source, "incoming")

    def _get_agent_by_id(
        self, agents_list: List[Dict[str, Any]], agent_id: int
    ) -> Dict[str, Any]:
        """
        Obtiene el nombre del agente de la conversación.
        """
        return next(
            (agent for agent in agents_list if agent.get("idAgent") == agent_id), {}
        )

    def validate_channel_data(self, channel_data: Dict[str, Any]) -> bool:
        """
        Valida que los datos del canal sean válidos para HeyNow.
        """
        if not super().validate_channel_data(channel_data):
            return False

        # Validaciones específicas de HeyNow
        external_id = channel_data.get("external_channel_id", "")

        # HeyNow usa IDs UUID o numéricos
        if not external_id or len(external_id) < 3:
            return False

        return True

    def _parse_heynow_timestamp(self, timestamp_str: str) -> str:
        """
        Convierte timestamp de HeyNow a formato ISO estándar.
        """
        try:
            if not timestamp_str:
                return datetime.now().isoformat()

            # HeyNow puede usar varios formatos, intentar parsear
            formats_to_try = [
                "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO con microsegundos
                "%Y-%m-%dT%H:%M:%SZ",  # ISO sin microsegundos
                "%Y-%m-%d %H:%M:%S",  # Formato simple
            ]

            for fmt in formats_to_try:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue

            # Si no se puede parsear, usar timestamp actual
            _logger.warning(f"Could not parse HeyNow timestamp: {timestamp_str}")
            return datetime.now().isoformat()

        except Exception as e:
            _logger.error(f"Error parsing timestamp {timestamp_str}: {str(e)}")
            return datetime.now().isoformat()

    def _map_heynow_message_type(self, heynow_type: str) -> str:
        """
        Mapea tipos de mensaje de HeyNow al formato estándar.
        """
        type_mapping = {
            "text": "chat",
            "image": "file",
            "file": "file",
            "video": "file",
            "audio": "file",
            "system": "system",
            "notification": "system",
            "join": "system",
            "leave": "system",
        }
        return type_mapping.get(heynow_type, "chat")
