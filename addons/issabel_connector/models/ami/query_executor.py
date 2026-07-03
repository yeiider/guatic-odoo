
import logging
import asyncio
from typing import Dict,  Any
from .connection_manager import AMIConnectionManager
from .response_parser import AMIResponseParser


class AMIQueryExecutor:
    """
    Ejecutor de queries AMI en tiempo real.

    Responsabilidades:
    - Ejecutar acciones AMI
    - Parsear respuestas
    - Thread-safe para llamadas desde HTTP threads
    """

    def __init__(self, connection_manager: AMIConnectionManager):
        self.connection = connection_manager
        self._logger = logging.getLogger(f"{__name__}.AMIQueryExecutor")

    def query_queue_status(self, timeout: int = 10) -> Dict[str, Any]:
        """
        Consulta estado completo de colas vía QueueStatus.

        Thread-safe: puede llamarse desde HTTP threads usando
        run_coroutine_threadsafe.
        """
        if not self.connection.is_connected() or not self.connection.loop:
            raise ConnectionError("AMI no está conectado")

        try:
            # Ejecutar query desde thread HTTP
            future = asyncio.run_coroutine_threadsafe(
                self._query_queue_status_async(),
                self.connection.loop
            )

            # Esperar resultado con timeout
            result = future.result(timeout=timeout)
            return result

        except Exception as e:
            self._logger.error(f"❌ Error consultando estado de colas: {e}")
            return {'queues': [], 'agents': [], 'calls': []}

    async def _query_queue_status_async(self) -> Dict[str, Any]:
        """Query asíncrono de QueueStatus"""
        try:
            # Enviar acción QueueStatus
            response = await self.connection.send_action({'Action': 'QueueStatus'})

            # Parsear eventos resultantes
            parser = AMIResponseParser()
            return parser.parse_queue_status_response(response)

        except Exception as e:
            self._logger.error(f"Error en query asíncrono: {e}")
            raise
