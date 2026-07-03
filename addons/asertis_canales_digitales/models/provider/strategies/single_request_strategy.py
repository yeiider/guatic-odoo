from ..handlers.message_builder import MessageBuilder
from .base_strategy import BaseFileStrategy, MessageType
import logging

_logger = logging.getLogger(__name__)


class SingleRequestStrategy(BaseFileStrategy):
    """Estrategia para envío en una sola petición"""

    def execute(self, message) -> bool:
        _logger.info("Executing single request strategy")
        complete_message = MessageBuilder.create_complete_message(message)
        return self._send_message(complete_message, MessageType.COMPLETE)
