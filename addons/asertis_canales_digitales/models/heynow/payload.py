from typing import List, Dict, Any, Optional
from uuid import uuid4


from ..utils.avatar import get_provider_avatar
from ..payloads.base_event import (
    ContactMetadata,
    MessageEvent,
    MessageEventType,
    FileEvent,
    BaseEvent,
    ChannelEventType,
    ChannelConfiguration,
)

from ..provider.provider_type import ProviderType
from .types import HeynowChannelType
from datetime import date


class HeynowPayload:
    """HeynowPayload is a class responsible for parsing and extracting structured event data from raw HeyNow integration payloads.

    Attributes:
        raw (dict): The raw payload data received from the HeyNow integration.

    Methods:
        __init__(raw: dict):
            Initializes the HeynowPayload instance with the provided raw payload data.

        extract() -> BaseEvent:
            Extracts and constructs a BaseEvent object from the raw payload data, including user, channel, message, and metadata.

        _get_chanel_name() -> str:
            Determines and returns the channel name based on contact and channel information in the payload.

        _get_message() -> MessageEvent:
            Extracts and returns the message content, type, files, and related metadata from the payload.

        _calculate_is_incoming() -> bool:
            Determines whether the event is incoming or outgoing based on the payload data.

        _formatter_files(files: List[Dict[str, Any]]) -> List[FileEvent]:
            Formats and returns a list of FileEvent objects from the provided file metadata in the payload.

        _get_custom_id() -> str:
            Generates and returns a custom unique identifier for the message.

        _get_message_contact() -> Optional[ContactMetadata]:
            Extracts and returns contact metadata from the payload, including name, phone number, email, and profile picture.
    """

    def __init__(self, raw: dict):
        self.raw = raw

    @property
    def event(self) -> dict:
        return self.raw.get("event", {})

    @property
    def data(self) -> dict:
        return self.raw.get("data", {})

    @property
    def new_data(self) -> dict:
        return self.event.get("new", {})

    @property
    def contact_data(self) -> dict:
        return self.new_data.get("__contact") or self.data.get("__contact", {})

    def extract(self) -> BaseEvent:
        """
        Extracts and constructs a BaseEvent object from the raw payload data.

        This method processes the incoming payload, extracting relevant event information,
        contact details, channel type, and message content. It determines whether the event
        is incoming or outgoing and assembles all relevant metadata into a BaseEvent instance.

        Returns:
            BaseEvent: An object containing the extracted event data, user information,
            channel details, message, and associated metadata.
        """

        key = self.event.get("key", {})
        channel_type_name = HeynowChannelType.from_int(key.get("channel", 0))
        message = self._get_message()
        is_incoming = self._calculate_is_incoming()

        partner_user = None
        if self.data.get("idAgent"):
            partner_user = {
                "id": self.data.get("idAgent"),
                "names": "",
                "lastNames": "",
            }

        user_name = self._get_contact_full_name(
            fallback_first_name=channel_type_name,
            fallback_last_name=key.get("clientId", ""),
        )

        return BaseEvent(
            user_id=key.get("clientId"),
            message=message,
            user_name=user_name,
            channel_config=self._get_config_channel(),
            channel_name=self._get_channel_name(),
            channel=channel_type_name,
            ability=self.event.get("ability"),
            is_processable=self.event.get("ability") not in ("", None),
            is_incoming=is_incoming,
            metadata=self._build_event_metadata(key, channel_type_name, partner_user),
        )

    def _get_channel_name(self) -> str:
        """
        Devuelve el nombre del canal en formato 'Nombre Apellido - Canal'.
        """
        key = self.event.get("key", {})
        channel = HeynowChannelType.from_int(key.get("channel", 0))

        if self.contact_data:
            full_name = self._get_contact_full_name()
            return f"{full_name} - {channel}"

        return f"{channel} {self.data.get('contactId', 'Nuevo Contacto')}"

    def _get_message(self) -> MessageEvent:
        """
        Construye y devuelve un objeto MessageEvent.
        """
        last_message_trace = self.data.get("lastMessageTrace", {})
        message_text = self.data.get("message", "")
        meta_data = self.data.get("metaData", {})
        files = None
        message_type = MessageEventType.TEXT

        temporal_files = meta_data.get("temporal", [])
        if temporal_files:
            files = self._formatter_files(temporal_files)
            if files:
                mime_type = getattr(files[0], "mimetype", "text/plain")
                message_type = MessageEventType.from_mime_type(mime_type)

        message_id = last_message_trace.get("idMessageHey") or self._get_custom_id()

        return MessageEvent(
            id=message_id,
            content=message_text,
            message_type=message_type,
            contact=self._get_message_contact(),
            message_id_provider_chat=message_id,
            metadata=meta_data or {},
            files=files,
            provider_type=ProviderType.HEYNOW,
        )

    def _get_config_channel(self) -> Optional[ChannelConfiguration]:
        """
        Devuelve la configuración del canal para el evento actual.
        """
        key = self.event.get("key", {})
        channel = HeynowChannelType(key.get("channel", 0))

        if channel is None:
            return None
        icon_name = channel.icon_name()
        channel_type = ChannelEventType.from_str(icon_name)

        config = ChannelConfiguration(type=channel_type)

        return config

    def _calculate_is_incoming(self) -> bool:
        """
        Determina si el mensaje es entrante o saliente.
        """
        event = self.data.get("event", {})
        is_go_to_agent = (
            event.get("changeAgent", False)
            and event.get("changeAbility", False)
            and event.get("gotoPannel", False)
        )

        return self.data.get("incoming", False) or is_go_to_agent

    def _formatter_files(self, files: List[Dict[str, Any]]) -> List[FileEvent]:
        """
        Convierte los archivos temporales en objetos FileEvent.
        """
        result = []
        for file in files:
            file_event = FileEvent(
                name=file.get("name", ""),
                datas=file.get("data", ""),
                type="binary" if file.get("data") else "url",
                mimetype=file.get("mimeType", ""),
                description=file.get(
                    "description",
                    f'Archivo {file.get("name", "")} de HeyNow de {HeynowChannelType.from_int(file.get("channel", 0))}',
                ),
                url=file.get("urlFileshare", ""),
                file_size=file.get("size", 0),
                metadata={
                    "encode": file.get("encode", ""),
                    "channel": HeynowChannelType.from_int(file.get("channel", 0)),
                    "platform_id": file.get("platformId", 0),
                    "temporal_id": file.get("temporalId", ""),
                    "index_date": date.today(),
                },
            )
            result.append(file_event)
        return result

    def _get_custom_id(self) -> str:
        """
        Genera un UUID para identificar el mensaje si no se proporciona uno.
        """
        return str(uuid4())

    def _get_message_contact(self) -> Optional[ContactMetadata]:
        """
        Extrae y devuelve los metadatos del contacto del mensaje.
        """
        key = self.event.get("key", {})
        contact = self.contact_data

        phone_number = None
        config = self._get_config_channel()
        provider_name = config.type.value if config else "generic"
        profile_picture_url = get_provider_avatar(provider_name)
        channel = key.get("channel", 0)
        is_whatsapp = channel == HeynowChannelType.WHATSAPP.value or channel == HeynowChannelType.WHATSAPP_CLOUD.value
        if contact:
            phones = contact.get("phones", [])
            if phones:
                phone_number = phones[0]
            if is_whatsapp:
                phone_number = key.get("clientId")

            if contact.get("profilePictureUrl"):
                profile_picture_url = contact.get("profilePictureUrl")

            return ContactMetadata(
                first_name=contact.get("first_name"),
                last_name=contact.get("last_name"),
                phone_number=phone_number,
                email=contact.get("email"),
                identity_number=None,
                profile_picture_url=profile_picture_url,
            )

        if is_whatsapp:
            return ContactMetadata(
                phone_number=key.get("clientId"),
                profile_picture_url=profile_picture_url,
            )

        return ContactMetadata(
            profile_picture_url=profile_picture_url,
        )

    def _get_contact_full_name(
        self, fallback_first_name="", fallback_last_name=""
    ) -> str:
        """
        Construye el nombre completo del contacto.
        """
        contact = self.contact_data
        if contact:
            return f"{contact.get('first_name', fallback_first_name)} {contact.get('last_name', fallback_last_name)}".strip()
        return f"{fallback_first_name} {fallback_last_name}".strip()

    def _build_event_metadata(
        self, key: dict, channel_type: str, partner_user: Optional[dict]
    ) -> dict:
        """
        Construye el diccionario de metadatos para el evento.
        """
        return {
            "clientId": key.get("clientId"),
            "session": key.get("session"),
            "platformId": key.get("platformId"),
            "channel": key.get("channel"),
            "partner_user": partner_user,
            "channel_type": channel_type,
        }
