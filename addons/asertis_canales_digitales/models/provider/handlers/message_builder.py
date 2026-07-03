from typing import List


class MessageBuilder:
    """Builder para crear diferentes tipos de mensajes"""

    @staticmethod
    def create_text_only_message(original_message) -> "MessageProxy":
        """Crear mensaje solo con texto"""
        return MessageProxy(
            body=original_message.body,
            message_id=original_message.message_id_provider_chat,
            attachments=[],
        )

    @staticmethod
    def create_file_only_message(
        original_message, attachment, description: str = None
    ) -> "MessageProxy":
        """Crear mensaje solo con archivo"""
        file_description = description or f"📎 {attachment.name}"
        return MessageProxy(
            body=file_description,
            message_id=original_message.message_id_provider_chat,
            attachments=[attachment],
        )

    @staticmethod
    def create_file_with_text_message(original_message, attachment) -> "MessageProxy":
        """Crear mensaje con archivo y texto original"""
        return MessageProxy(
            body=original_message.body,
            message_id=original_message.message_id_provider_chat,
            attachments=[attachment],
        )

    @staticmethod
    def create_complete_message(original_message) -> "MessageProxy":
        """Crear mensaje completo (para providers que soportan múltiples archivos)"""
        return MessageProxy(
            body=original_message.body,
            message_id=original_message.message_id_provider_chat,
            attachments=list(original_message.attachment_ids),
        )


class MessageProxy:
    """Proxy para simular estructura de mensaje original"""

    def __init__(self, body: str, message_id: str, attachments: List):
        self.body = body
        self.message_id_provider_chat = message_id
        self.attachment_ids = attachments
