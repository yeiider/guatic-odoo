# -*- coding: utf-8 -*-
"""
Complete AMI Event Handlers for Issabel 4 / Asterisk 11
========================================================

TODOS los eventos AMI relacionados con:
- 🎧 Agentes (Agent)
- ☎️ Llamadas en Cola (QueueCaller)
- 📊 Colas y Estadísticas (Queue)

Basado en documentación oficial de Asterisk 11 y compatible con Issabel 4.
"""

import lxml.builder
from typing import Dict, Any, Optional
from .base import (
    BaseEventHandler,
    EventHandlerRegistry,
    AgentData,
    CallData,
    QueueData,
    AMIDataMapper,
    CallState,
)


# ============================================================================
# 🎧 AGENT EVENTS - Eventos de Agentes
# ============================================================================


@EventHandlerRegistry.register(["QueueMemberStatus"])
class AgentStatusHandler(BaseEventHandler):
    """
    Evento: QueueMemberStatus
    -------------------------
    Descripción: Estado actual de un agente/miembro de cola
    Cuándo: Al conectar AMI, al cambiar estado del agente

    Campos importantes:
    - Status: 0=Unknown, 1=Available, 2=InUse, 3=Busy, 4=Invalid, 5=Unavailable
    - Paused: 0/1 si está en pausa
    - InCall: 0/1 si está en llamada
    - CallsTaken: Total de llamadas atendidas
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "QueueMemberStatus"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[AgentData]:
        try:
            agent = (
                event_data.get("Location")
                or event_data.get("StateInterface")
                or event_data.get("Interface")
            )

            if not agent:
                return None

            return AgentData(
                agent=agent,
                name=event_data.get("MemberName") or event_data.get("Name", "Unknown"),
                queue=event_data.get("Queue", ""),
                status=AMIDataMapper.to_agent_status(event_data.get("Status")),
                paused=AMIDataMapper.parse_bool(event_data.get("Paused")),
                in_call=AMIDataMapper.parse_bool(event_data.get("InCall")),
                penalty=AMIDataMapper.parse_int(event_data.get("Penalty")),
                calls_taken=AMIDataMapper.parse_int(event_data.get("CallsTaken")),
                last_call=event_data.get("LastCall"),
            )
        except Exception as e:
            self._logger.error(f"Error extrayendo AgentStatus: {e}")
            return None

    def get_notification_type(self) -> str:
        return "QueueMemberStatus"


@EventHandlerRegistry.register(["QueueMemberAdded"])
class AgentAddedHandler(BaseEventHandler):
    """
    Evento: QueueMemberAdded
    ------------------------
    Descripción: Un agente fue agregado a una cola
    Cuándo: queue add member CLI o AMI QueueAdd action

    Uso: Actualizar lista de agentes en dashboard
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "QueueMemberAdded"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[AgentData]:
        return AgentData(
            agent=event_data.get("Location") or event_data.get("Interface", ""),
            name=event_data.get("MemberName") or event_data.get("Name", "Unknown"),
            queue=event_data.get("Queue", ""),
            status=AMIDataMapper.to_agent_status(event_data.get("Status")),
            paused=AMIDataMapper.parse_bool(event_data.get("Paused")),
            pause_reason=event_data.get("Reason", ""),
            in_call=AMIDataMapper.parse_bool(event_data.get("InCall")),
            last_call=event_data.get("LastCall"),
            penalty=AMIDataMapper.parse_int(event_data.get("Penalty")),
            calls_taken=AMIDataMapper.parse_int(event_data.get("CallsTaken", 0)),
        )

    def get_notification_type(self) -> str:
        return "QueueMemberAdded"


@EventHandlerRegistry.register(["QueueMemberRemoved"])
class AgentRemovedHandler(BaseEventHandler):
    """
    Evento: QueueMemberRemoved
    --------------------------
    Descripción: Un agente fue removido de una cola
    Cuándo: queue remove member CLI o AMI QueueRemove action

    Uso: Eliminar agente del dashboard
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "QueueMemberRemoved"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "agent": event_data.get("Location") or event_data.get("Interface"),
            "queue": event_data.get("Queue"),
            "name": event_data.get("MemberName"),
        }

    def get_notification_type(self) -> str:
        return "QueueMemberRemoved"


@EventHandlerRegistry.register(["QueueMemberPause", "QueueMemberPaused"])
class AgentPauseHandler(BaseEventHandler):
    """
    Evento: QueueMemberPause / QueueMemberPaused
    --------------------------------------------
    Descripción: Agente pausado o despausado
    Cuándo: Al ejecutar pausa desde teléfono, CLI o AMI

    Campos:
    - Paused: 0 (despausado) o 1 (pausado)
    - Reason: Motivo de la pausa (opcional)
    - Status: Cambia a 5 (Unavailable) cuando pausado
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type in ["QueueMemberPause", "QueueMemberPaused"]

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        paused = AMIDataMapper.parse_bool(event_data.get("Paused"))

        return {
            "queue": event_data.get("Queue"),
            "interface": event_data.get("Interface"),
            "location": event_data.get("Location") or event_data.get("Interface"),
            "paused": paused,
            "reason": event_data.get("Reason", ""),
            "status": "5" if paused else "1",  # 5=Unavailable, 1=Available
            "member_name": event_data.get("MemberName"),
        }

    def get_notification_type(self) -> str:
        return "QueueMemberPause"


@EventHandlerRegistry.register(["AgentCalled"])
class AgentCalledHandler(BaseEventHandler):
    """
    Evento: AgentCalled
    -------------------
    Descripción: Un agente está siendo llamado (sonando su extensión)
    Cuándo: La cola intenta entregar llamada a un agente disponible

    Secuencia típica:
    1. AgentCalled (sonando)
    2. AgentConnect (contestó) O AgentRingNoAnswer (no contestó)

    Campos importantes:
    - Queue: Cola desde donde se llama
    - Interface: Agente que está sonando
    - CallerIDNum: Número del cliente
    - DestChannel: Canal del agente
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "AgentCalled"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "queue": event_data.get("Queue"),
            "interface": event_data.get("Interface"),
            "agent_name": event_data.get("MemberName"),
            "caller_id_num": event_data.get("CallerIDNum"),
            "caller_id_name": event_data.get("CallerIDName"),
            "channel": event_data.get("Channel"),
            "dest_channel": event_data.get("DestChannel"),
            "unique_id": event_data.get("Uniqueid"),
            "dest_unique_id": event_data.get("DestUniqueid"),
        }

    def get_notification_type(self) -> str:
        return "AgentCalled"


@EventHandlerRegistry.register(["AgentConnect"])
class AgentConnectHandler(BaseEventHandler):
    """
    Evento: AgentConnect
    --------------------
    Descripción: Agente contestó y fue conectado con el cliente
    Cuándo: Inmediatamente después de que el agente contesta

    CRÍTICO: Este es el evento más importante para trackear llamadas activas

    Campos importantes:
    - HoldTime: Tiempo que el cliente esperó en cola (segundos)
    - RingTime: Tiempo que sonó el agente (segundos)
    - Member: Interface del agente
    - Channel: Canal del cliente
    - Uniqueid: ID único de la llamada
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "AgentConnect"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "queue": event_data.get("Queue"),
            "interface": event_data.get("Interface"),
            "member": event_data.get("Member"),
            "member_name": event_data.get("MemberName"),
            "channel": event_data.get("Channel"),
            "caller_id_num": event_data.get("CallerIDNum"),
            "caller_id_name": event_data.get("CallerIDName"),
            "unique_id": event_data.get("Uniqueid"),
            "hold_time": AMIDataMapper.parse_int(event_data.get("HoldTime")),
            "ring_time": AMIDataMapper.parse_int(event_data.get("RingTime")),
            # Campos de canal destino
            "dest_channel": event_data.get("DestChannel"),
            "dest_unique_id": event_data.get("DestUniqueid"),
        }

    def get_notification_type(self) -> str:
        return "AgentConnect"


@EventHandlerRegistry.register(["AgentComplete"])
class AgentCompleteHandler(BaseEventHandler):
    """
    Evento: AgentComplete
    ---------------------
    Descripción: Llamada entre agente y cliente finalizó
    Cuándo: Cuando cualquiera de los dos cuelga

    IMPORTANTE: Este evento marca el FIN de una llamada atendida

    Campos importantes:
    - TalkTime: Tiempo total de conversación (segundos)
    - HoldTime: Tiempo que esperó el cliente (segundos)
    - Reason: caller (cliente colgó) o agent (agente colgó) o transfer

    NOTA: En Asterisk 11 a veces falta Uniqueid. Usar Channel para trackear.
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "AgentComplete"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "queue": event_data.get("Queue"),
            "interface": event_data.get("Interface"),
            "member": event_data.get("Member"),
            "member_name": event_data.get("MemberName"),
            "channel": event_data.get("Channel"),
            "caller_id_num": event_data.get("CallerIDNum"),
            "hold_time": AMIDataMapper.parse_int(event_data.get("HoldTime")),
            "talk_time": AMIDataMapper.parse_int(event_data.get("TalkTime")),
            "reason": event_data.get("Reason", ""),  # caller, agent, transfer
            "unique_id": event_data.get("Uniqueid"),  # Puede estar vacío en Asterisk 11
            # Campos adicionales de canal
            "dest_channel": event_data.get("DestChannel"),
            "dest_unique_id": event_data.get("DestUniqueid"),
        }

    def get_notification_type(self) -> str:
        return "AgentComplete"


@EventHandlerRegistry.register(["AgentRingNoAnswer"])
class AgentRingNoAnswerHandler(BaseEventHandler):
    """
    Evento: AgentRingNoAnswer
    -------------------------
    Descripción: El agente no contestó la llamada
    Cuándo: Después de que expira el timeout de ring

    Uso: Marcar agente como "no disponible temporalmente"

    Campos:
    - RingTime: Tiempo que sonó sin respuesta (segundos)
    - Interface: Agente que no contestó

    NOTA: En Issabel/Asterisk 11, este evento requiere:
           eventwhencalled=yes en queues.conf
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "AgentRingNoAnswer"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "queue": event_data.get("Queue"),
            "interface": event_data.get("Interface"),
            "member_name": event_data.get("MemberName"),
            "ring_time": AMIDataMapper.parse_int(event_data.get("RingTime")),
            "channel": event_data.get("Channel"),
            "unique_id": event_data.get("Uniqueid"),
        }

    def get_notification_type(self) -> str:
        return "AgentRingNoAnswer"


@EventHandlerRegistry.register(["AgentDump"])
class AgentDumpHandler(BaseEventHandler):
    """
    Evento: AgentDump
    -----------------
    Descripción: Agente colgó mientras escuchaba el anuncio de cola
    Cuándo: Si el agente cuelga antes de conectar con el cliente

    Uso: Trackear "rechazos" de llamadas por parte de agentes

    RARO: Este evento es poco común, solo en configuraciones específicas
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "AgentDump"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "queue": event_data.get("Queue"),
            "interface": event_data.get("Interface"),
            "member_name": event_data.get("MemberName"),
            "channel": event_data.get("Channel"),
            "unique_id": event_data.get("Uniqueid"),
        }

    def get_notification_type(self) -> str:
        return "AgentDump"


@EventHandlerRegistry.register(["Agentlogoff"])
class AgentLogoffHandler(BaseEventHandler):
    """
    Evento: Agentlogoff
    -------------------
    Descripción: Agente se deslogueó del sistema
    Cuándo: Al hacer logout desde teléfono o CLI

    NOTA: Este evento es para sistemas con AgentLogin (antiguo).
           En sistemas modernos con AddQueueMember se usa QueueMemberRemoved
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "Agentlogoff"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "agent": event_data.get("Agent"),
            "unique_id": event_data.get("Uniqueid"),
        }

    def get_notification_type(self) -> str:
        return "Agentlogoff"


@EventHandlerRegistry.register(["QueueMemberRinginuse"])
class AgentRingInUseHandler(BaseEventHandler):
    """
    Evento: QueueMemberRinginuse
    ----------------------------
    Descripción: Cambió configuración de "ringinuse" del agente
    Cuándo: Al modificar si el agente puede recibir llamadas mientras está en otra

    Campos:
    - Ringinuse: 0 o 1 (si puede recibir llamadas estando ocupado)

    AVANZADO: Solo relevante si usas ringinuse en queues.conf
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "QueueMemberRinginuse"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "queue": event_data.get("Queue"),
            "interface": event_data.get("Interface"),
            "member_name": event_data.get("MemberName"),
            "ringinuse": AMIDataMapper.parse_bool(event_data.get("Ringinuse")),
            "status": event_data.get("Status"),
            "paused": AMIDataMapper.parse_bool(event_data.get("Paused")),
        }

    def get_notification_type(self) -> str:
        return "QueueMemberRinginuse"


@EventHandlerRegistry.register(["ExtensionStatus"])
class ExtensionStatusHandler(BaseEventHandler):
    """
    Evento: ExtensionStatus
    -----------------------
    Descripción: Cambió el estado de una extensión/agente
    Cuándo: Al cambiar el estado (Disponible, Ocupado, Inalcanzable, etc.)

    Campos:
    - Exten: Número de extensión
    - Status: Nuevo estado (0=Desconocido, 1=Disponible, 2=Ocupado, 3=Inalcanzable, etc.)

    USO: Monitorizar estado de extensiones/agentes en tiempo real
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "ExtensionStatus"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "extension": event_data.get("Exten"),
            "status": AMIDataMapper.to_extension_status(
                event_data.get("Status")
            ).descripcion(),
        }

    def get_notification_type(self) -> str:
        return "ExtensionStatus"


@EventHandlerRegistry.register(["QueueMemberPenalty"])
class AgentPenaltyHandler(BaseEventHandler):
    """
    Evento: QueueMemberPenalty
    --------------------------
    Descripción: Cambió la penalidad/prioridad del agente
    Cuándo: Al modificar penalty del miembro

    Campos:
    - Penalty: Número (menor = mayor prioridad para recibir llamadas)

    USO: Agentes con penalty=0 reciben llamadas primero que penalty=1, etc.
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "QueueMemberPenalty"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "queue": event_data.get("Queue"),
            "interface": event_data.get("Interface"),
            "member_name": event_data.get("MemberName"),
            "penalty": AMIDataMapper.parse_int(event_data.get("Penalty")),
        }

    def get_notification_type(self) -> str:
        return "QueueMemberPenalty"


# ============================================================================
# ☎️ QUEUE CALLER EVENTS - Eventos de Llamadas en Cola
# ============================================================================


@EventHandlerRegistry.register(["QueueCallerJoin","Join"])
class CallJoinHandler(BaseEventHandler):
    """
    Evento: QueueCallerJoin
    -----------------------
    Descripción: Una llamada ingresó a la cola
    Cuándo: Cuando ejecuta Queue() en dialplan

    CRÍTICO: Punto de entrada de TODAS las llamadas

    Campos importantes:
    - Position: Posición en la cola (1 = primera)
    - Count: Total de llamadas en cola
    - CallerIDNum: Número del cliente
    - Uniqueid: ID único (GUARDAR para trackear)
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type in ["QueueCallerJoin","Join"]

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[CallData]:
        try:
            return CallData(
                unique_id=event_data.get("Uniqueid", ""),
                caller_id_num=event_data.get("CallerIDNum", ""),
                caller_id_name=event_data.get("CallerIDName", ""),
                queue=event_data.get("Queue", ""),
                position=AMIDataMapper.parse_int(event_data.get("Position")),
                channel=event_data.get("Channel", ""),
                state=CallState.QUEUED,
                # Campos adicionales de Asterisk 11
                connected_line_num=event_data.get("ConnectedLineNum", ""),
                connected_line_name=event_data.get("ConnectedLineName", ""),
            )
        except Exception as e:
            self._logger.error(f"Error extrayendo QueueCallerJoin: {e}")
            return None

    def get_notification_type(self) -> str:
        return "QueueCallerJoin"


@EventHandlerRegistry.register(["QueueCallerLeave"])
class CallLeaveHandler(BaseEventHandler):
    """
    Evento: QueueCallerLeave
    ------------------------
    Descripción: Una llamada salió de la cola (fue atendida)
    Cuándo: Cuando un agente contesta (después de AgentConnect)

    IMPORTANTE: Este evento indica que la llamada YA FUE ASIGNADA a un agente

    Campos:
    - Count: Llamadas restantes en cola
    - Position: Posición que tenía
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "QueueCallerLeave"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "queue": event_data.get("Queue"),
            "channel": event_data.get("Channel"),
            "caller_id_num": event_data.get("CallerIDNum"),
            "caller_id_name": event_data.get("CallerIDName"),
            "unique_id": event_data.get("Uniqueid"),
            "count": AMIDataMapper.parse_int(event_data.get("Count")),
            "position": AMIDataMapper.parse_int(event_data.get("Position")),
        }

    def get_notification_type(self) -> str:
        return "QueueCallerLeave"


@EventHandlerRegistry.register(["QueueCallerAbandon"])
class CallAbandonHandler(BaseEventHandler):
    """
    Evento: QueueCallerAbandon
    --------------------------
    Descripción: Cliente colgó mientras esperaba en cola
    Cuándo: Cliente se cansa de esperar y cuelga

    CRÍTICO: Indicador clave de servicio (llamadas perdidas)

    Campos importantes:
    - HoldTime: Tiempo que esperó antes de colgar (segundos)
    - Position: Posición en la que estaba
    - OriginalPosition: Posición inicial cuando entró

    KPI: Si HoldTime es alto = mal servicio
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "QueueCallerAbandon"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "queue": event_data.get("Queue"),
            "channel": event_data.get("Channel"),
            "caller_id_num": event_data.get("CallerIDNum"),
            "caller_id_name": event_data.get("CallerIDName"),
            "unique_id": event_data.get("Uniqueid"),
            "position": AMIDataMapper.parse_int(event_data.get("Position")),
            "original_position": AMIDataMapper.parse_int(
                event_data.get("OriginalPosition")
            ),
            "hold_time": AMIDataMapper.parse_int(event_data.get("HoldTime")),
        }

    def get_notification_type(self) -> str:
        return "QueueCallerAbandon"


@EventHandlerRegistry.register(["QueueEntry"])
class QueueEntryHandler(BaseEventHandler):
    """
    Evento: QueueEntry
    ------------------
    Descripción: Información de una llamada en cola (snapshot)
    Cuándo: Al ejecutar QueueStatus action, recibe un QueueEntry por cada llamada esperando

    USO: Obtener estado completo de llamadas en cola al conectar AMI

    Campos:
    - Wait: Tiempo actual de espera (segundos)
    - Priority: Prioridad de la llamada (default 0)
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "QueueEntry"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[CallData]:
        return CallData(
            unique_id=event_data.get("Uniqueid", ""),
            caller_id_num=event_data.get("CallerIDNum", ""),
            caller_id_name=event_data.get("CallerIDName", ""),
            queue=event_data.get("Queue", ""),
            position=AMIDataMapper.parse_int(event_data.get("Position")),
            wait_time=AMIDataMapper.parse_int(event_data.get("Wait")),
            channel=event_data.get("Channel", ""),
            priority=AMIDataMapper.parse_int(event_data.get("Priority")),
            connected_line_num=event_data.get("ConnectedLineNum", ""),
            connected_line_name=event_data.get("ConnectedLineName", ""),
        )

    def get_notification_type(self) -> str:
        return "QueueEntry"


# ============================================================================
# 📊 QUEUE STATISTICS EVENTS - Estadísticas de Colas
# ============================================================================


@EventHandlerRegistry.register(["QueueParams"])
class QueueParamsHandler(BaseEventHandler):
    """
    Evento: QueueParams
    -------------------
    Descripción: Estadísticas y parámetros de una cola
    Cuándo: Al ejecutar QueueStatus action, recibe un QueueParams por cada cola

    CRÍTICO: Contiene TODAS las métricas importantes de la cola

    Campos clave (KPIs):
    - Calls: Llamadas actualmente en cola
    - Completed: Total de llamadas completadas
    - Abandoned: Total de llamadas abandonadas
    - Holdtime: Tiempo promedio de espera (segundos)
    - TalkTime: Tiempo promedio de conversación (segundos)
    - ServicelevelPerf: % de llamadas dentro del SLA (ej: 80.5)
    - Strategy: Estrategia de distribución (ringall, leastrecent, etc.)
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "QueueParams"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[QueueData]:
        try:
            return QueueData(
                queue=event_data.get("Queue", ""),
                calls=AMIDataMapper.parse_int(event_data.get("Calls")),
                completed=AMIDataMapper.parse_int(event_data.get("Completed")),
                abandoned=AMIDataMapper.parse_int(event_data.get("Abandoned")),
                holdtime=AMIDataMapper.parse_int(event_data.get("Holdtime")),
                talk_time=AMIDataMapper.parse_int(event_data.get("TalkTime")),
                service_level=AMIDataMapper.parse_float(
                    event_data.get("ServicelevelPerf")
                ),
                strategy=AMIDataMapper.to_queue_strategy(
                    event_data.get("Strategy", "ringall")
                ),
                max_len=AMIDataMapper.parse_int(event_data.get("Max")),
                weight=AMIDataMapper.parse_int(event_data.get("Weight")),
            )
        except Exception as e:
            self._logger.error(f"Error extrayendo QueueParams: {e}")
            return None

    def get_notification_type(self) -> str:
        return "QueueParams"


@EventHandlerRegistry.register(["QueueMember"])
class QueueMemberHandler(BaseEventHandler):
    """
    Evento: QueueMember
    -------------------
    Descripción: Información de un miembro de cola (snapshot)
    Cuándo: Al ejecutar QueueStatus action, recibe un QueueMember por cada agente

    USO: Obtener lista completa de agentes al conectar AMI

    NOTA: Similar a QueueMemberStatus pero es parte de la respuesta de QueueStatus
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "QueueMember"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[AgentData]:
        return AgentData(
            agent=event_data.get("Location", ""),
            name=event_data.get("Name") or event_data.get("MemberName", "Unknown"),
            queue=event_data.get("Queue", ""),
            status=AMIDataMapper.to_agent_status(event_data.get("Status")),
            paused=AMIDataMapper.parse_bool(event_data.get("Paused")),
            in_call=AMIDataMapper.parse_bool(event_data.get("InCall")),
            penalty=AMIDataMapper.parse_int(event_data.get("Penalty")),
            calls_taken=AMIDataMapper.parse_int(event_data.get("CallsTaken")),
            last_call=event_data.get("LastCall"),
        )

    def get_notification_type(self) -> str:
        return "QueueMember"


@EventHandlerRegistry.register(["QueueStatusComplete"])
class QueueStatusCompleteHandler(BaseEventHandler):
    """
    Evento: QueueStatusComplete
    ---------------------------
    Descripción: Indica que terminó la respuesta de QueueStatus
    Cuándo: Al final de la secuencia de eventos de QueueStatus action

    Secuencia completa de QueueStatus:
    1. Response: Success
    2. N × QueueParams (una por cola)
    3. N × QueueMember (uno por agente)
    4. N × QueueEntry (uno por llamada en espera)
    5. QueueStatusComplete ← FIN

    USO: Marcar que ya se recibieron todos los datos
    """

    def can_handle(self, event_type: str) -> bool:
        return event_type == "QueueStatusComplete"

    def extract_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {
            "eventlist": event_data.get("EventList"),  # "Complete"
        }

    def get_notification_type(self) -> str:
        return "QueueStatusComplete"
