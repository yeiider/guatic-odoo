from ..handlers.message_builder import MessageBuilder
from .base_strategy import BaseFileStrategy, MessageType
import logging

_logger = logging.getLogger(__name__)


class FilesFirstStrategy(BaseFileStrategy):
    """Estrategia: enviar archivos primero, luego texto"""

    def execute(self, message) -> bool:
        _logger.info("Executing files-first strategy")
        success = True

        for index, attachment in enumerate(message.attachment_ids, 1):
            file_message = MessageBuilder.create_file_only_message(message, attachment)
            success &= self._send_message(file_message, MessageType.FILE_ONLY, index)

        if message.body and message.body.strip():
            text_message = MessageBuilder.create_text_only_message(message)
            success &= self._send_message(text_message, MessageType.TEXT_ONLY)

        return success
