from ..strategies.strategy_factory import FileStrategyFactory
from ..strategies.base_strategy import MultipleFilesStrategy
from ..dispatcher import ProviderDispatcher
import requests
import logging

_logger = logging.getLogger(__name__)


class ProviderFileHandler:
    """Manejador principal para envío de archivos por proveedor"""

    def __init__(self, provider_name: str, env):
        self.provider_name = provider_name
        self.env = env

    def send_message(self, message, provider_metadata) -> bool:
        """Enviar mensaje con manejo inteligente de archivos múltiples"""
        try:

            provider = ProviderDispatcher(self.provider_name, self.env).get_provider()
            webhook_url = provider.get_url(config=provider_metadata)

            if not webhook_url:
                _logger.warning("No webhook URL configured for %s", self.provider_name)
                return False

            headers = provider.get_headers()

            strategy_type = self._determine_strategy(provider, message)

            strategy = FileStrategyFactory.create_strategy(
                strategy_type,
                self._send_single_request,
                provider,
                webhook_url,
                headers,
                self.provider_name,
                provider_metadata,
            )

            return strategy.execute(message)

        except Exception as e:
            _logger.error("Error in send_message: %s", str(e))
            return False

    def _determine_strategy(self, provider, message) -> MultipleFilesStrategy:
        """Determinar qué estrategia usar basado en el proveedor y mensaje"""

        if not message.attachment_ids:
            return MultipleFilesStrategy.SINGLE_REQUEST

        if getattr(provider, "supports_multiple_files", False):
            return MultipleFilesStrategy.SINGLE_REQUEST

        strategy_name = getattr(provider, "multiple_files_strategy", "text_first")

        try:
            return MultipleFilesStrategy(strategy_name)
        except (ValueError, KeyError):
            _logger.warning(
                "Invalid strategy %s for provider %s", strategy_name, self.provider_name
            )
            return MultipleFilesStrategy.TEXT_FIRST

    def _send_single_request(
        self, url, payload, headers, provider_name, request_type
    ) -> bool:
        """Callback para envío de petición HTTP individual"""
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)

            _logger.info(
                "Provider %s (%s): Status %s",
                provider_name,
                request_type,
                response.status_code,
            )

            if response.status_code == 200:
                _logger.info("Request %s sent successfully", request_type)
                return True
            else:
                _logger.error(
                    "Failed request %s: Status %s, Response: %s",
                    request_type,
                    response.status_code,
                    response.text,
                )
                return False

        except requests.RequestException as e:
            _logger.error("HTTP error sending %s: %s", request_type, str(e))
            return False
        except Exception as e:
            _logger.error("Unexpected error sending %s: %s", request_type, str(e))
            return False
