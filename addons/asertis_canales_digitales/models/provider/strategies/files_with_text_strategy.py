from ..handlers.message_builder import MessageBuilder
from .base_strategy import BaseFileStrategy, MessageType
import logging

_logger = logging.getLogger(__name__)


class FilesWithTextStrategy(BaseFileStrategy):
    """Estrategia: cada archivo incluye el texto original"""

    def execute(self, message) -> bool:
        _logger.info("Executing files-with-text strategy")
        success = True

        for index, attachment in enumerate(message.attachment_ids, 1):
            file_message = MessageBuilder.create_file_with_text_message(
                message, attachment
            )
            success &= self._send_message(
                file_message, MessageType.FILE_WITH_TEXT, index
            )

        return success
