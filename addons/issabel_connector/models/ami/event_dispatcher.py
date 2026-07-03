import logging
import threading
import time
from typing import Dict, Any
from panoramisk import Manager, Message
from ..base import EventPriorityManager


class AMIEventDispatcher:
    """
    Dispatcher de eventos AMI a Queue Jobs.

    Responsabilidades:
    - Filtrar eventos relevantes
    - Determinar prioridad
    - Encolar en Queue Jobs
    - Rate limiting (evitar sobrecarga)
    """

    # Eventos relevantes para el sistema
    RELEVANT_EVENTS = {
        "QueueMemberStatus",
        "QueueMemberAdded",
        "QueueMemberRemoved",
        "QueueMemberPause",
        "QueueMemberPaused",
        "AgentCalled",
        "AgentConnect",
        "AgentComplete",
        "Agentlogoff",
        "QueueCallerJoin",
        "QueueCallerLeave",
        "QueueCallerAbandon",
        "Hangup",
        "QueueParams",
        "QueueEntry",
        "QueueMember",
        "PeerStatus",
        "ExtensionStatus",
        "SoftHangupRequest",
        "Join",
    }

    # Eventos que NO se loguean (ruido)
    SILENT_EVENTS = {
        "RTCPReceived",
        "RTCPSent",
    }

    def __init__(self, env):
        self.env = env
        self._logger = logging.getLogger(f"{__name__}.AMIEventDispatcher")
        self._event_count = 0
        self._last_log_time = time.time()

    def handle_event(self, manager: Manager, event: Message):
        """
        Callback principal para eventos AMI.

        IMPORTANTE: Este método debe ser MUY rápido para no bloquear
        el event loop de asyncio.
        """
        try:
            event_type = event.get("Event", "")

            # Filtrar eventos relevantes
            if not self._is_relevant_event(event_type):

                return

            # Encolar de forma asíncrona (no bloquea asyncio)
            threading.Thread(
                target=self._enqueue_event_sync,
                args=(event_type, dict(event)),
                daemon=True,
            ).start()

            # Logging periódico
            self._log_event_stats()

        except Exception as e:
            self._logger.error(f"❌ Error manejando evento: {e}")

    def _is_relevant_event(self, event_type: str) -> bool:
        """Determina si el evento es relevante"""
        if event_type in self.RELEVANT_EVENTS:
            return True

        # Log eventos desconocidos (para debugging)
        if event_type not in self.SILENT_EVENTS:
            self._logger.debug(f"ℹ️ Evento no manejado: {event_type}")

        return False

    def _enqueue_event_sync(self, event_type: str, event_data: Dict[str, Any]):
        """
        Encola evento en Queue Job (ejecución sincrónica en thread separado).

        Usa nuevo cursor para evitar conflictos con la transacción principal.
        """
        try:
            # Crear nuevo cursor
            with self.env.registry.cursor() as new_cr:
                new_env = self.env(cr=new_cr)

                # Obtener prioridad
                priority = EventPriorityManager.get_priority(event_type)

                # Crear job
                new_env["issabel.event.processor"].with_delay(
                    priority=priority,
                    max_retries=2,
                    channel="ami_events",
                ).process_ami_event(event_type, event_data)

                new_cr.commit()
                self._event_count += 1

        except Exception as e:
            self._logger.error(
                f"❌ Error encolando evento {event_type}: {e}", exc_info=True
            )

    def _log_event_stats(self):
        """Log estadísticas periódicas de eventos"""
        current_time = time.time()
        elapsed = current_time - self._last_log_time

        # Log cada 60 segundos
        if elapsed >= 60:
            rate = self._event_count / elapsed
            self._logger.info(
                f"📊 Eventos procesados: {self._event_count} "
                f"(tasa: {rate:.2f} eventos/seg)"
            )
            self._event_count = 0
            self._last_log_time = current_time
