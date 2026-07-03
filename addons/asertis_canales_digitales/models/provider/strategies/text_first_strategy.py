from ..handlers.message_builder import MessageBuilder
from .base_strategy import BaseFileStrategy, MessageType
import logging

_logger = logging.getLogger(__name__)


class TextFirstStrategy(BaseFileStrategy):
    """Estrategia: enviar texto primero, luego archivos"""

    def execute(self, message) -> bool:
        _logger.info("Executing text-first strategy")
        success = True

        if message.body and message.body.strip():
            text_message = MessageBuilder.create_text_only_message(message)
            success &= self._send_message(text_message, MessageType.TEXT_ONLY)

        for index, attachment in enumerate(message.attachment_ids, 1):
            file_message = MessageBuilder.create_file_only_message(message, attachment)
            success &= self._send_message(file_message, MessageType.FILE_ONLY, index)

        return success
