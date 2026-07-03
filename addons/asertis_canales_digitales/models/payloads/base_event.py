from dataclasses import asdict, dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from ..provider.provider_type import ProviderType
from uuid import uuid4
from datetime import datetime
import json


class ChannelEventType(Enum):
    WHATSAPP = "whatsapp"
    INSTAGRAM = "instagram"
    MESSENGER = "messenger"
    TELEGRAM = "telegram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    WEB = "web"
    EMAIL = "email"
    SMS = "sms"
    LINKEDIN = "linkedin"
    DISCORD = "discord"
    SIGNAL = "signal"
    CHATBOT = "chatbot"
    GENERIC = "generic"

    @staticmethod
    def from_str(value: str) -> "ChannelEventType":
        """Devuelve el Enum ChannelEventType desde un string (case-insensitive)"""
        value = value.lower()
        for member in ChannelEventType:
            if member.value == value:
                return member
        return ChannelEventType.GENERIC

    def default_icon(self) -> str:
        return {
            "whatsapp": "fa fa-whatsapp",
            "instagram": "fa fa-instagram",
            "messenger": "fa fa-facebook-messenger",
            "facebook": "fa fa-facebook",
            "telegram": "fa fa-telegram",
            "twitter": "fa fa-twitter",
            "web": "fa fa-globe",
            "email": "fa fa-envelope",
            "sms": "fa fa-comment-alt",
            "linkedin": "fa fa-linkedin",
            "discord": "fa fa-discord",
            "signal": "fa fa-signal",
            "chatbot": "fa fa-robot",
        }.get(self.value, "fa fa-comments")

    def default_color(self) -> str:
        return {
            "whatsapp": "#25D366",
            "instagram": "#C13584",
            "messenger": "#0084FF",
            "facebook": "#3b5998",
            "telegram": "#0088cc",
            "twitter": "#1DA1F2",
            "web": "#6c63ff",
            "email": "#D44638",
            "sms": "#4CAF50",
            "linkedin": "#0077B5",
            "discord": "#7289DA",
            "signal": "#3A76F0",
            "chatbot": "#FFC107",
        }.get(self.value, "#999999")


@dataclass
class ChannelConfiguration:
    type: ChannelEventType
    label: Optional[str] = None
    icon_class: Optional[str] = None
    color: Optional[str] = None

    def get_icon(self) -> str:
        return self.icon_class or self.type.default_icon()

    def get_color(self) -> str:
        return self.color or self.type.default_color()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "label": self.label,
            "icon_class": self.icon_class,
            "color": self.color,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ChannelConfiguration":
        return ChannelConfiguration(
            type=ChannelEventType.from_str(data.get("type", "generic")),
            label=data.get("label"),
            icon_class=data.get("icon_class"),
            color=data.get("color"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @staticmethod
    def from_json(json_str: str) -> "ChannelConfiguration":
        data = json.loads(json_str)
        return ChannelConfiguration.from_dict(data)


class MessageEventType(Enum):
    """
    Enumeration of message event types for handling various payload formats.

    Attributes:
        TEXT: Represents plain text messages.
        HTML: Represents HTML-formatted messages.
        IMAGE: Represents image files (e.g., JPEG, PNG, GIF).
        AUDIO: Represents audio files (e.g., MP3, WAV, AAC).
        VIDEO: Represents video files (e.g., MP4, WebM, AVI).
        DOCUMENT: Represents document files (e.g., PDF, Word, Excel).
        LOCATION: Represents location payloads.
        CONTACT: Represents contact information payloads.
        STICKER: Represents sticker payloads.
        VOICE_NOTE: Represents voice note audio files (e.g., OGG, OPUS, AMR).
        FILE: Represents generic file payloads.
        UNKNOWN: Represents unknown or unsupported payload types.

    Methods:
        from_mime_type(mime_type: str) -> "MessageEventType":
            Returns the corresponding MessageEventType based on the provided MIME type string.
            If the MIME type is not recognized, returns MessageEventType.UNKNOWN.
    """

    TEXT = "text"
    HTML = "html"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    LOCATION = "location"
    CONTACT = "contact"
    STICKER = "sticker"
    VOICE_NOTE = "voice_note"
    FILE = "file"
    UNKNOWN = "unknown"

    @staticmethod
    def from_mime_type(mime_type: str) -> "MessageEventType":
        """
        Maps a MIME type string to a corresponding MessageEventType.

        Args:
            mime_type (str): The MIME type to map (e.g., "image/png", "text/plain").

        Returns:
            MessageEventType: The corresponding event type for the given MIME type.
                              Returns MessageEventType.UNKNOWN if the MIME type is not recognized.

        Supported types include:
            - Text (plain, HTML)
            - Images (jpeg, png, gif, webp, bmp, tiff, svg)
            - Audio (mp3, wav, aac, ogg, opus, webm, amr)
            - Video (mp4, matroska, webm, ogg, quicktime, avi, wmv)
            - Documents (pdf, word, excel, powerpoint, zip, rar, json, csv, xml)
            - Custom types (location, contact, sticker)
        """
        MIME_TYPE_MAP = {
            "text/plain": MessageEventType.TEXT,
            "text/html": MessageEventType.HTML,
            "image/jpeg": MessageEventType.IMAGE,
            "image/jpg": MessageEventType.IMAGE,
            "image/png": MessageEventType.IMAGE,
            "image/gif": MessageEventType.IMAGE,
            "image/webp": MessageEventType.IMAGE,
            "image/bmp": MessageEventType.IMAGE,
            "image/tiff": MessageEventType.IMAGE,
            "image/svg+xml": MessageEventType.IMAGE,
            "audio/mpeg": MessageEventType.AUDIO,
            "audio/mp3": MessageEventType.AUDIO,
            "audio/mp4": MessageEventType.AUDIO,
            "audio/x-wav": MessageEventType.AUDIO,
            "audio/wav": MessageEventType.AUDIO,
            "audio/aac": MessageEventType.AUDIO,
            "audio/ogg": MessageEventType.VOICE_NOTE,
            "audio/opus": MessageEventType.VOICE_NOTE,
            "audio/webm": MessageEventType.AUDIO,
            "audio/amr": MessageEventType.VOICE_NOTE,
            "video/mp4": MessageEventType.VIDEO,
            "video/x-matroska": MessageEventType.VIDEO,
            "video/webm": MessageEventType.VIDEO,
            "video/ogg": MessageEventType.VIDEO,
            "video/quicktime": MessageEventType.VIDEO,
            "video/x-msvideo": MessageEventType.VIDEO,
            "video/x-ms-wmv": MessageEventType.VIDEO,
            "application/pdf": MessageEventType.DOCUMENT,
            "application/msword": MessageEventType.DOCUMENT,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": MessageEventType.DOCUMENT,
            "application/vnd.ms-excel": MessageEventType.DOCUMENT,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": MessageEventType.DOCUMENT,
            "application/vnd.ms-powerpoint": MessageEventType.DOCUMENT,
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": MessageEventType.DOCUMENT,
            "application/zip": MessageEventType.DOCUMENT,
            "application/x-rar-compressed": MessageEventType.DOCUMENT,
            "application/json": MessageEventType.DOCUMENT,
            "text/csv": MessageEventType.DOCUMENT,
            "application/xml": MessageEventType.DOCUMENT,
            "application/x-location": MessageEventType.LOCATION,
            "application/x-contact": MessageEventType.CONTACT,
            "application/x-sticker": MessageEventType.STICKER,
        }
        return MIME_TYPE_MAP.get(mime_type, MessageEventType.UNKNOWN)


@dataclass
class FileEvent:
    """Clase para representar archivos que serán convertidos a ir.attachment en Odoo 16"""

    name: str = ""
    type: str = "binary"
    datas: str = ""
    mimetype: Optional[str] = None
    description: Optional[str] = None
    public: bool = False
    access_token: Optional[str] = None
    checksum: Optional[str] = None
    url: Optional[str] = None
    file_size: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContactMetadata:
    """
    Represents metadata information for a contact.
    Attributes:
        first_name (Optional[str]): The contact's first name.
        last_name (Optional[str]): The contact's last name.
        phone_number (Optional[str]): The contact's phone number.
        email (Optional[str]): The contact's email address.
        identity_number (Optional[str]): The contact's identity or identification number.
        profile_picture_url (Optional[str]): URL to the contact's profile picture.
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    identity_number: Optional[str] = None
    profile_picture_url: Optional[str] = None

    def to_json(self) -> str:
        """
        Serializes the current instance to a JSON-formatted string.

        Returns:
            str: A JSON string representation of the instance.
        """
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(data: str):
        """
        Deserializes a JSON-formatted string into a ContactMetadata object.

        Args:
            data (str): A JSON string representing the ContactMetadata fields.

        Returns:
            ContactMetadata: An instance of ContactMetadata populated with data from the JSON string.
        """
        return ContactMetadata(**json.loads(data))


@dataclass
class MessageEvent:
    """
    Represents a message event containing information about a message exchanged through a provider.

    Attributes:
        id (str): Unique identifier for the message event. Automatically generated as a UUID.
        message_type (MessageEventType): The type of the message (e.g., text, image). Defaults to TEXT.
        content (str): The textual content of the message. Defaults to an empty string.
        files (Optional[List[FileEvent]]): List of files attached to the message, if any.
        contact (Optional[ContactMetadata]): Metadata about the contact associated with the message.
        metadata (Dict[str, Any]): Additional metadata related to the message event.
        provider_type (ProviderType): The provider through which the message was sent. Defaults to HEYNOW.
        created_at (datetime): Timestamp when the message event was created. Defaults to the current time.
        message_id_provider_chat (Optional[str]): Identifier of the message in the provider's chat system.
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    message_type: MessageEventType = MessageEventType.TEXT
    content: str = ""
    files: Optional[List[FileEvent]] = None
    contact: Optional[ContactMetadata] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    provider_type: ProviderType = ProviderType.HEYNOW
    created_at: datetime = field(default_factory=datetime.now)
    message_id_provider_chat: Optional[str] = None


@dataclass
class BaseEvent:
    """
    BaseEvent representa un evento base para la integración de mensajes en diferentes canales de comunicación.

    Atributos:
        user_id (str): Identificador del usuario.
        message (MessageEvent): Objeto que representa el mensaje asociado al evento.
        user_name (str): Nombre del usuario.
        channel_name (str): Nombre del canal de comunicación.
        channel (str): Tipo de canal de comunicación (Whatsapp, Instagram, Messenger, etc.).
        channel_config (Optional[ChannelConfiguration]): Configuración del canal, si está disponible.
        ability (Optional[str]): Habilidad o capacidad asociada al evento, si aplica.
        is_processable (bool): Indica si el evento es procesable por el sistema.
        is_incoming (bool): Indica si el mensaje es entrante (True) o saliente (False).
        is_processable (bool): Indica si el mensaje es procesable por el sistema.
        metadata (Dict[str, Any]): Diccionario con metadatos adicionales del evento.

    Métodos:
        to_json(): Convierte la instancia del evento a una cadena JSON.
        to_dict(): Convierte la instancia del evento a un diccionario.
        from_dict(data): Crea una instancia de BaseEvent a partir de un diccionario, reconstruyendo objetos anidados.
        from_json(json_str): Crea una instancia de BaseEvent a partir de una cadena JSON.
    """

    user_id: str
    message: MessageEvent
    user_name: str
    channel_name: str
    channel: str
    is_incoming: bool
    channel_config: Optional[ChannelConfiguration] = None
    is_processable: bool = True
    ability: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self):
        """Convertir a JSON string"""
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    def to_dict(self):
        """Convertir a diccionario"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """Crear desde diccionario"""
        if "message" in data and data["message"]:
            message_data = data["message"]
            files = None
            if "files" in message_data and message_data["files"]:
                files = [FileEvent(**file_data) for file_data in message_data["files"]]
            data["message"] = MessageEvent(
                content=message_data["content"],
                message_id_provider_chat=message_data.get("message_id_provider_chat"),
                files=files,
            )
        return cls(**data)

    @classmethod
    def from_json(cls, json_str):
        """Crear desde JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
