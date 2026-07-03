from ..handlers.message_builder import MessageBuilder
from .base_strategy import BaseFileStrategy, MessageType
import logging

_logger = logging.getLogger(__name__)


class InterleavedStrategy(BaseFileStrategy):
    """Estrategia: intercalar texto y archivos"""

    def execute(self, message) -> bool:
        _logger.info("Executing interleaved strategy")
        success = True

        if message.body and message.body.strip():
            text_message = MessageBuilder.create_text_only_message(message)
            success &= self._send_message(text_message, MessageType.TEXT_ONLY)

        for index, attachment in enumerate(message.attachment_ids, 1):
            file_message = MessageBuilder.create_file_only_message(
                message,
                attachment,
                f"📎 Archivo {index}/{len(message.attachment_ids)}: {attachment.name}",
            )
            success &= self._send_message(file_message, MessageType.FILE_ONLY, index)

        return success
