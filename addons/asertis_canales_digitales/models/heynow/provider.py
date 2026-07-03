
from typing import Dict, Any
from ..provider.provider_type import ProviderType
from ..provider.provider import Provider
from ..provider.chat_provider_config import ChatProviderConfig
import logging

_logger = logging.getLogger(__name__)


class HeynowProvider(Provider):
    """
    Heynow provider class.
    """

    supports_multiple_files = False  # No soporta múltiples archivos en una petición
    multiple_files_strategy = "text_first_then_files"

    def __init__(self, env):
        """
        Initialize the HeynowProvider with Odoo environment.

        :param env: Odoo environment object
        """
        self.env = env
        self._provider_config = None
        self._provider_name = ProviderType.HEYNOW.value

    def get_url(self, config=None) -> str:
        """
        Get the URL of the Heynow API.

        :return: The URL as a string.
        """
        url_base = self._get_base_url()
        if config:

            url_base = config.get("url_base", url_base)
            if not url_base.endswith("/"):
                url_base += "/"
            channel = config.get("channel", "")
            platform_id = config.get("platformId", "")
            client_id = config.get("clientId", "")
            session_id = config.get("session", "")

            url_base += f"{channel}/{platform_id}/{client_id}/{session_id}"
            return url_base

        return url_base

    def get_headers(self) -> Dict[str, str]:
        """
        Get the headers required for API requests to Heynow.

        :return: A dictionary of headers.
        """
        headers = {
            "Content-Type": "application/json",
        }

        partner_token = self._get_auth_token()
        if partner_token:
            headers["partner-token"] = partner_token

        return headers

    def get_payload(
        self, message: Dict[str, Any], config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Get the payload to be sent to Heynow.

        :param message: The message data to include in the payload.
        :param config: Optional configuration parameters.
        :return: A dictionary representing the payload.
        """
        message_text = self._clean_html(message.body)
        partner_user = self._get_partner_user()
        if config and config.get("partner_user"):
            partner_user = config.get("partner_user", {})
        payload = {
            "text": message_text,
            "partnerUser": partner_user,
            "idMessageHey": message.message_id_provider_chat,
        }

        if message.attachment_ids:
            attachment = message.attachment_ids[0]

            # En Odoo 16, el campo 'datas' ya está en base64
            file_data_b64 = attachment.datas

            # Verificar si datas es bytes (caso poco común en Odoo 16)
            if isinstance(file_data_b64, bytes):
                file_data_b64 = file_data_b64.decode("utf-8")

            # Verificar que no esté vacío
            if not file_data_b64:
                _logger.warning(
                    "Attachment data is empty for attachment: %s", attachment.name
                )
                return payload

            # Validar que sea base64 válido (opcional)
            try:
                import base64

                base64.b64decode(file_data_b64, validate=True)
            except Exception as e:
                _logger.error(
                    "Invalid base64 data for attachment %s: %s", attachment.name, str(e)
                )
                return payload

            payload["file"] = {
                "data": file_data_b64,
                "name": attachment.name,
                "encode": "base64",
                "mimeType": attachment.mimetype,
            }

        return payload

    def _get_auth_token(self) -> str:
        token = ""
        try:
            self._provider_config = self.get_config_provider()
            token = self._provider_config.auth_token
        except (AttributeError, KeyError) as e:
            self.env["ir.logging"].sudo().create(
                {
                    "name": "HeynowProvider",
                    "type": "server",
                    "dbname": self.env.cr.dbname,
                    "level": "ERROR",
                    "message": f"Error retrieving auth token: {str(e)}",
                    "path": __file__,
                    "func": "_get_auth_token",
                    "line": "",
                }
            )

        return token

    def _get_base_url(self) -> str:

        if not self._provider_config:
            self._provider_config = self.get_config_provider()

        if self._provider_config.base_url:
            return self._provider_config.base_url

        return ""

    def _get_partner_user(self) -> Dict[str, Any]:
        # logica para obtener el para el partner user de hey now
        if not self._provider_config:
            self._provider_config = self.get_config_provider()

        if self._provider_config.config_extra:
            return self._provider_config.config_extra.get("partnerUser", {})

        return {}

    def _clean_html(self, body) -> str:
        return self.clear_html_message(body)

    def get_config_provider(self) -> ChatProviderConfig:
        """
        Retrieve the provider configuration from the Odoo environment.

        :return: The provider configuration object.
        """

        provider = self.env["chat.provider"].search(
            [("provider_type", "=", self._provider_name)], limit=1
        )
        if not provider:
            raise ValueError("Provider not found: heynow")
        return ChatProviderConfig(
            id=provider.id,
            name=provider.name,
            provider_type=provider.provider_type,
            is_active=provider.is_active,
            base_url=provider.base_url,
            auth_token=provider.auth_token,
            allowed_channel_ids=provider.allowed_channel_ids,
            config_extra=provider.get_config_extra_dict(),
        )
