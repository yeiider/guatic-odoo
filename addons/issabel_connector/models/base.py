# -*- coding: utf-8 -*-
"""
Core Architecture - Abstract Base Classes & Event System
==========================================================

Este módulo define la arquitectura base del sistema AMI con:
- Clases abstractas para handlers de eventos
- Sistema de registry para handlers
- Tipos de datos tipificados con dataclasses
- Patrones: Strategy, Factory, Observer, Singleton
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable, Type
from enum import Enum
from datetime import datetime

_logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS - Tipos de datos tipificados
# ============================================================================


class AgentStatus(Enum):
    """Estados posibles de un agente"""

    UNKNOWN = 0
    AVAILABLE = 1
    IN_USE = 2
    BUSY = 3
    INVALID = 4
    UNAVAILABLE = 5
    RINGING = 6
    RINGING_IN_USE = 7
    ON_HOLD = 8

    @property
    def display_name(self) -> str:
        """Nombre traducible del estado"""
        names = {
            0: "Desconocido",
            1: "Disponible",
            2: "En uso",
            3: "Ocupado",
            4: "Inválido",
            5: "No disponible",
            6: "Sonando",
            7: "Sonando y en uso",
            8: "En espera",
        }
        return names.get(self.value, "Desconocido")

    @property
    def color(self) -> str:
        """Color para UI"""
        colors = {
            1: "#16a34a",  # Verde - Disponible
            2: "#2563eb",  # Azul - En uso
            3: "#ca8a04",  # Amarillo - Ocupado
            5: "#dc2626",  # Rojo - No disponible
        }
        return colors.get(self.value, "#9ca3af")


class ExtensionStatus(Enum):
    REMOVED_FROM_DIALPLAN = -2
    HINT_REMOVED = -1
    IDLE = 0
    IN_USE = 1
    BUSY = 2
    UNAVAILABLE = 4
    RINGING = 8
    IN_USE_RINGING = 9
    HOLD = 16
    IN_USE_HOLD = 17

    def descripcion(self):
        descripciones = {
            self.REMOVED_FROM_DIALPLAN: "Extensión eliminada",
            self.HINT_REMOVED: "Hint eliminado",
            self.IDLE: "Libre",
            self.IN_USE: "En uso",
            self.BUSY: "Ocupado",
            self.UNAVAILABLE: "No disponible",
            self.RINGING: "Sonando",
            self.IN_USE_RINGING: "En uso y sonando",
            self.HOLD: "En espera",
            self.IN_USE_HOLD: "En uso y en espera",
        }
        return descripciones.get(self, "Desconocido.")


class CallState(Enum):
    """Estados de una llamada"""

    QUEUED = "queued"
    RINGING = "ringing"
    CONNECTED = "connected"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class QueueStrategy(Enum):
    """Estrategias de distribución de cola"""

    RINGALL = "ringall"
    LEAST_RECENT = "leastrecent"
    FEWEST_CALLS = "fewestcalls"
    RANDOM = "random"
    RRMEMORY = "rrmemory"
    RRORDERED = "rrordered"
    LINEAR = "linear"
    WRANDOM = "wrandom"

    @property
    def display_name(self) -> str:
        names = {
            "ringall": "Llamar a todos",
            "leastrecent": "Menos reciente",
            "fewestcalls": "Menos llamadas",
            "random": "Aleatorio",
            "rrmemory": "Ronda con memoria",
            "rrordered": "Ronda ordenada",
            "linear": "Lineal",
            "wrandom": "Aleatorio ponderado",
        }
        return names.get(self.value, "Desconocida")


# ============================================================================
# DATA CLASSES - Estructuras de datos tipificadas
# ============================================================================


@dataclass
class AgentData:
    """Datos completos de un agente"""

    agent: str
    name: str
    queue: str
    status: AgentStatus
    paused: bool = False
    in_call: bool = False
    penalty: int = 0
    calls_taken: int = 0
    last_call: Optional[str] = None
    pause_reason: str = ""

    @property
    def status_display(self) -> str:
        return self.status.display_name

    @property
    def status_color(self) -> str:
        return self.status.color

    def to_dict(self) -> Dict[str, Any]:
        """Conversión a dict para JSON"""
        data = asdict(self)
        data["status"] = self.status.value
        data["status_display"] = self.status_display
        data["status_color"] = self.status_color
        return data


@dataclass
class CallData:
    """Datos de una llamada en cola"""

    unique_id: str
    caller_id_num: str
    caller_id_name: str
    queue: str
    position: int
    wait_time: int = 0
    channel: str = ""
    state: CallState = CallState.QUEUED
    priority: int = 0
    connected_line_num: str = ""
    connected_line_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data


@dataclass
class QueueData:
    """Datos de una cola"""

    queue: str
    calls: int = 0
    completed: int = 0
    abandoned: int = 0
    holdtime: int = 0
    talk_time: int = 0
    service_level: float = 0.0
    strategy: QueueStrategy = QueueStrategy.RINGALL
    max_len: int = 0
    weight: int = 0

    @property
    def strategy_display(self) -> str:
        return self.strategy.display_name

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["strategy"] = self.strategy.value
        data["strategy_display"] = self.strategy_display
        return data


# ============================================================================
# ABSTRACT BASE CLASSES - Patrones Strategy & Template Method
# ============================================================================


class BaseEventHandler(ABC):
    """
    Clase base abstracta para todos los handlers de eventos AMI.

    Patrón: Template Method - define el flujo común de procesamiento
    Patrón: Strategy - cada handler implementa su estrategia específica
    """

    def __init__(self, env):
        self.env = env
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def can_handle(self, event_type: str) -> bool:
        """
        Verifica si este handler puede procesar el evento.

        Returns:
            bool: True si puede manejar el evento
        """
        pass

    @abstractmethod
    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extrae y valida los datos del evento AMI.

        Returns:
            Objeto tipificado (AgentData, CallData, etc.) o None si inválido
        """
        pass

    @abstractmethod
    def get_notification_type(self) -> str:
        """Retorna el tipo de notificación para el bus"""
        pass

    def process(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Template Method: flujo común de procesamiento

        1. Validar que puede manejar el evento
        2. Extraer datos
        3. Procesar lógica de negocio (hook)
        4. Notificar al dashboard
        """
        if not self.can_handle(event_type):
            return False

        try:
            # Extraer datos tipificados
            data = self.extract_data(event_data)
            if data is None:
                self._logger.warning(f"Datos inválidos para {event_type}")
                return False

            # Hook para lógica de negocio adicional (opcional)
            self._process_business_logic(data, event_data)

            # Notificar al dashboard
            self._notify_dashboard(data)

            return True

        except Exception as e:
            self._logger.error(f"Error procesando {event_type}: {e}", exc_info=True)
            return False

    def _process_business_logic(self, data: Any, raw_event: Dict[str, Any]) -> None:
        """
        Hook opcional para lógica de negocio adicional.
        Los handlers pueden sobrescribir este método.
        """
        pass

    def _notify_dashboard(self, data: Any) -> None:
        """Envía notificación al dashboard vía bus"""
        try:
            notification_data = data.to_dict() if hasattr(data, "to_dict") else data

            payload = {
                "type": self.get_notification_type(),
                "data": notification_data,
            }

            # Enviar a todos los usuarios conectados
            self.env.user._bus_send("issabel_ami_event", payload)

            self._logger.debug(
                f"✅ Notificación enviada: {self.get_notification_type()}"
            )

        except Exception as e:
            self._logger.error(f"Error notificando: {e}", exc_info=True)


# ============================================================================
# EVENT HANDLER REGISTRY - Patrón Factory & Registry
# ============================================================================


class EventHandlerRegistry:
    """
    Registry centralizado de handlers de eventos.

    Patrón: Factory - crea handlers según el tipo de evento
    Patrón: Registry - mantiene registro de handlers disponibles
    Patrón: Singleton - única instancia del registry
    """

    _instance = None
    _handlers: Dict[str, Type[BaseEventHandler]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, event_types: List[str]):
        """
        Decorador para registrar handlers automáticamente

        Usage:
            @EventHandlerRegistry.register(['QueueMemberStatus', 'QueueMemberPause'])
            class AgentStatusHandler(BaseEventHandler):
                ...
        """

        def decorator(handler_class: Type[BaseEventHandler]):
            for event_type in event_types:
                cls._handlers[event_type] = handler_class
            _logger.info(f"✅ Registrado {handler_class.__name__} para {event_types}")
            return handler_class

        return decorator

    def get_handler(self, env, event_type: str) -> Optional[BaseEventHandler]:
        """Obtiene el handler apropiado para un tipo de evento"""
        handler_class = self._handlers.get(event_type)
        if handler_class:
            return handler_class(env)
        return None

    def get_all_registered_events(self) -> List[str]:
        """Retorna lista de todos los eventos registrados"""
        return list(self._handlers.keys())


# ============================================================================
# DATA MAPPERS - Patrón Mapper para conversión de datos
# ============================================================================


class AMIDataMapper:
    """
    Mapper para convertir datos crudos de AMI a objetos tipificados.

    Patrón: Mapper - separa lógica de conversión de datos
    """

    @staticmethod
    def to_agent_status(status_code: Any) -> AgentStatus:
        """Convierte código de estado a enum"""
        try:
            code = int(status_code) if status_code else 0
            return AgentStatus(code)
        except (ValueError, KeyError):
            return AgentStatus.UNKNOWN

    @staticmethod
    def to_queue_strategy(strategy_str: str) -> QueueStrategy:
        """Convierte string de estrategia a enum"""
        try:
            return QueueStrategy(strategy_str.lower())
        except ValueError:
            return QueueStrategy.RINGALL

    @staticmethod
    def parse_bool(value: Any) -> bool:
        """Convierte varios formatos a booleano"""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        return False

    @staticmethod
    def to_extension_status(status_code: Any) -> ExtensionStatus:
        """Convierte código de estado a enum"""
        try:
            code = int(status_code) if status_code else -2
            return ExtensionStatus(code)
        except (ValueError, KeyError):
            return ExtensionStatus.REMOVED_FROM_DIALPLAN

    @staticmethod
    def parse_int(value: Any, default: int = 0) -> int:
        """Conversión segura a entero"""
        try:
            return int(value) if value else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def parse_float(value: Any, default: float = 0.0) -> float:
        """Conversión segura a float"""
        try:
            return float(value) if value else default
        except (ValueError, TypeError):
            return default


# ============================================================================
# EVENT PRIORITY MANAGER
# ============================================================================


class EventPriorityManager:
    """
    Gestiona prioridades de procesamiento de eventos.

    Permite configurar diferentes prioridades según tipo de evento
    para optimizar el procesamiento en Queue Jobs.
    """

    # Prioridades (menor número = mayor prioridad)
    CRITICAL = 1
    HIGH = 5
    MEDIUM = 10
    LOW = 15

    _priorities: Dict[str, int] = {
        # Eventos críticos - prioridad máxima
        "QueueCallerJoin": CRITICAL,
        "QueueCallerAbandon": CRITICAL,
        "Hangup": CRITICAL,
        "QueueEntry": CRITICAL,
        "Join": CRITICAL,
        # Eventos importantes - alta prioridad
        "AgentConnect": HIGH,
        "AgentComplete": HIGH,
        "QueueMemberPause": HIGH,
        # Eventos regulares - prioridad media
        "QueueMemberStatus": MEDIUM,
        "QueueParams": MEDIUM,
        # Eventos informativos - baja prioridad
        "PeerStatus": LOW,
        "ExtensionStatus": LOW,
    }

    @classmethod
    def get_priority(cls, event_type: str) -> int:
        """Obtiene prioridad para un tipo de evento"""
        return cls._priorities.get(event_type, cls.MEDIUM)

    @classmethod
    def set_priority(cls, event_type: str, priority: int) -> None:
        """Configura prioridad personalizada"""
        cls._priorities[event_type] = priority
