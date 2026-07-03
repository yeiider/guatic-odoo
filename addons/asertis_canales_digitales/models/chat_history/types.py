from dataclasses import asdict, dataclass, field
from typing import Dict, Any, List
from uuid import uuid4
import json


@dataclass
class HistoryAttachment:
    """Representa un archivo adjunto en el historial de chat."""
    id: str = field(default_factory=lambda: str(uuid4()))
    filename: str = ""
    mimetype: str = ""
    size: int = 0
    download_url: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryAttachment":
        """Crea una instancia desde un diccionario."""
        return cls(
            id=data.get("id", str(uuid4())),
            filename=data.get("filename", ""),
            mimetype=data.get("mimetype", ""),
            size=data.get("size", 0),
            download_url=data.get("download_url", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return asdict(self)


@dataclass
class ChatHistoryMessage:
    """Representa un mensaje en el historial de chat."""
    id: str = field(default_factory=lambda: str(uuid4()))
    author_name: str = ""
    author_avatar: str = ""
    timestamp: str = ""
    content: str = ""
    message_type: str = "chat"  # Default type
    attachments: List[HistoryAttachment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatHistoryMessage":
        """Crea una instancia desde un diccionario."""
        attachments = [
            HistoryAttachment.from_dict(a) for a in data.get("attachments", [])
        ]
        return cls(
            id=data.get("id", str(uuid4())),
            author_name=data.get("author_name", ""),
            author_avatar=data.get("author_avatar", ""),
            timestamp=data.get("timestamp", ""),
            content=data.get("content", ""),
            message_type=data.get("message_type", "chat"),
            attachments=attachments,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        data = asdict(self)
        data["attachments"] = [att.to_dict() for att in self.attachments]
        return data


@dataclass
class ChatHistory:
    """Representa el historial completo de chat con metadatos de paginación."""
    messages: List[ChatHistoryMessage] = field(default_factory=list)
    has_more: bool = False
    next_page: str = ""
    total_count: int = 0

    def to_json(self) -> str:
        """Convierte a JSON string."""
        data = {
            "messages": [msg.to_dict() for msg in self.messages],
            "has_more": self.has_more,
            "next_page": self.next_page,
            "total_count": self.total_count
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ChatHistory":
        """Crea una instancia desde JSON string."""
        data = json.loads(json_str)
        messages = [ChatHistoryMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            messages=messages,
            has_more=data.get("has_more", False),
            next_page=data.get("next_page", ""),
            total_count=data.get("total_count", 0),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatHistory":
        """Crea una instancia desde un diccionario."""
        messages = [ChatHistoryMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            messages=messages,
            has_more=data.get("has_more", False),
            next_page=data.get("next_page", ""),
            total_count=data.get("total_count", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario."""
        return {
            "messages": [msg.to_dict() for msg in self.messages],
            "has_more": self.has_more,
            "next_page": self.next_page,
            "total_count": self.total_count
        }

    def add_message(self, message: ChatHistoryMessage):
        """Añade un mensaje al historial."""
        self.messages.append(message)
        self.total_count += 1

    def is_empty(self) -> bool:
        """Verifica si el historial está vacío."""
        return len(self.messages) == 0
