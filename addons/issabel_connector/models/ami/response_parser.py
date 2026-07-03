import logging

from typing import Dict, Any


class AMIResponseParser:
    """
    Parser de respuestas AMI.

    Convierte respuestas crudas de AMI en estructuras de datos tipificadas.
    """

    def __init__(self):
        self._logger = logging.getLogger(f"{__name__}.AMIResponseParser")

    def parse_queue_status_response(self, response) -> Dict[str, Any]:
        """
        Parsea respuesta de QueueStatus.

        QueueStatus retorna múltiples eventos:
        - QueueParams: estadísticas de cola
        - QueueMember: datos de agentes
        - QueueEntry: llamadas en espera
        """
        queues = []
        agents = []
        calls = []

        # Convertir respuesta a lista de eventos
        events = response if isinstance(response, list) else [response]

        for event in events:
            event_dict = self._parse_message_object(event)
            event_type = event_dict.get("Event")

            if event_type == "QueueParams":
                queues.append(self._parse_queue_params(event_dict))
            elif event_type == "QueueMember":
                agents.append(self._parse_queue_member(event_dict))
            elif event_type == "QueueEntry":
                calls.append(self._parse_queue_entry(event_dict))

        self._logger.info(
            f"✅ Parsed: {len(queues)} colas, {len(agents)} agentes, {len(calls)} llamadas"
        )

        return {
            "queues": queues,
            "agents": agents,
            "calls": calls,
        }

    def _parse_queue_params(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parsea evento QueueParams"""
        from ..base import AMIDataMapper

        strategy_code = event.get("Strategy", "ringall").lower()
        strategy = AMIDataMapper.to_queue_strategy(strategy_code)

        return {
            "queue": event.get("Queue", ""),
            "calls": AMIDataMapper.parse_int(event.get("Calls")),
            "completed": AMIDataMapper.parse_int(event.get("Completed")),
            "abandoned": AMIDataMapper.parse_int(event.get("Abandoned")),
            "holdtime": AMIDataMapper.parse_int(event.get("Holdtime")),
            "talk_time": AMIDataMapper.parse_int(event.get("TalkTime")),
            "service_level": AMIDataMapper.parse_float(event.get("ServicelevelPerf")),
            "strategy": strategy.display_name,
            "max": AMIDataMapper.parse_int(event.get("Max")),
            "weight": AMIDataMapper.parse_int(event.get("Weight")),
        }

    def _parse_queue_member(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parsea evento QueueMember"""
        from ..base import AMIDataMapper

        status = AMIDataMapper.to_agent_status(event.get("Status"))

        return {
            "agent": event.get("Location", ""),
            "name": event.get("Name") or event.get("MemberName", "Unknown"),
            "queue": event.get("Queue", ""),
            "status": status.display_name,
            "status_code": status.value,
            "paused": AMIDataMapper.parse_bool(event.get("Paused")),
            "in_call": AMIDataMapper.parse_bool(event.get("InCall")),
            "penalty": AMIDataMapper.parse_int(event.get("Penalty")),
            "calls_taken": AMIDataMapper.parse_int(event.get("CallsTaken")),
        }

    def _parse_queue_entry(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parsea evento QueueEntry"""
        from ..base import AMIDataMapper

        return {
            "unique_id": event.get("Uniqueid", ""),
            "caller_id_num": event.get("CallerIDNum", ""),
            "caller_id_name": event.get("CallerIDName", ""),
            "queue": event.get("Queue", ""),
            "position": AMIDataMapper.parse_int(event.get("Position")),
            "wait_time": AMIDataMapper.parse_int(event.get("Wait")),
            "channel": event.get("Channel", ""),
        }

    def _parse_message_object(self, message) -> Dict[str, Any]:
        """Convierte objeto Message de panoramisk a dict"""
        if message is None:
            return {}

        try:
            if hasattr(message, "items"):
                return dict(message.items())

            if hasattr(message, "keys"):
                return {key: message[key] for key in message.keys()}

            if hasattr(message, "__dict__"):
                return {
                    k: v for k, v in message.__dict__.items() if not k.startswith("_")
                }

            return {}

        except Exception as e:
            self._logger.error(f"Error parseando mensaje: {e}")
            return {}
