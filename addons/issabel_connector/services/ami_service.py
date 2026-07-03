import logging
import threading
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from ..models.ami.connection_manager import AMIConnectionManager
from ..models.ami.event_dispatcher import AMIEventDispatcher
from ..models.ami.query_executor import AMIQueryExecutor

_logger = logging.getLogger(__name__)


class AMIService:
    """
    Servicio principal AMI (Singleton).

    Orquesta todos los componentes:
    - ConnectionManager: gestión de conexión
    - EventDispatcher: manejo de eventos
    - QueryExecutor: ejecución de queries

    Thread-safe y singleton.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, env):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, env):
        if self._initialized:
            self.env = env
            return

        self.env = env
        self.connection: Optional[AMIConnectionManager] = None
        self.dispatcher: Optional[AMIEventDispatcher] = None
        self.executor: Optional[AMIQueryExecutor] = None
        self.listener_thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
        self._initialized = True

        _logger.info("🔧 AMIService inicializado (Singleton)")

    def connect(self) -> bool:
        """Conecta al servidor AMI e inicia listener"""
        if self.is_connected():
            _logger.warning("⚠️ Ya existe una conexión activa")
            return True

        try:
            # Obtener configuración
            config = self._get_config()

            # Crear componentes
            self.connection = AMIConnectionManager(
                {
                    "host": config.ami_host,
                    "port": config.ami_port,
                    "username": config.ami_user,
                    "secret": config.ami_password,
                }
            )

            self.dispatcher = AMIEventDispatcher(self.env)
            self.executor = AMIQueryExecutor(self.connection)

            # Iniciar listener thread
            self.stop_flag.clear()
            self.listener_thread = threading.Thread(
                target=self._run_async_listener, daemon=True
            )
            self.listener_thread.start()

            # Esperar conexión
            time.sleep(5)

            if self.is_connected():
                # Actualizar estado en BD
                self._update_connection_state("connected")
                _logger.info("✅ AMI Service conectado exitosamente")
                return True

            raise ConnectionError("No se pudo establecer conexión")

        except Exception as e:
            _logger.error(f"❌ Error conectando: {e}", exc_info=True)
            self.disconnect()
            return False

    def _run_async_listener(self):
        """Ejecuta event loop en thread separado"""
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            if not self.connection:
                raise ConnectionError("No se pudo conectar")
            self.connection.loop = loop

            loop.run_until_complete(self._async_listener())
        except Exception as e:
            _logger.exception(f"❌ Error en listener: {e}")
        finally:

            if loop and not loop.is_closed():
                loop.close()

    async def _async_listener(self):
        """Listener asíncrono principal"""
        try:
            # Conectar
            if not self.connection:
                raise ConnectionError("No se pudo conectar")
            connected = await self.connection.connect()
            if not connected:
                raise ConnectionError("No se pudo conectar")

            # Registrar callback de eventos
            if not self.connection.manager:
                raise ConnectionError("Manager AMI no disponible")
            if not self.dispatcher:
                raise ConnectionError("Dispatcher AMI no disponible")
            self.connection.manager.register_event("*", self.dispatcher.handle_event)

            _logger.info("👂 Escuchando eventos AMI...")

            # Mantener conexión activa
            while not self.stop_flag.is_set():
                await asyncio.sleep(1)

        except Exception as e:
            _logger.exception(f"❌ Error en listener: {e}")
        finally:
            if self.connection:
                await self.connection.disconnect()

    def disconnect(self):
        """Desconecta del servidor AMI"""
        try:
            _logger.info("🛑 Desconectando AMI...")
            self.stop_flag.set()

            if self.listener_thread and self.listener_thread.is_alive():
                self.listener_thread.join(timeout=5)

            self._update_connection_state("disconnected")
            _logger.info("✅ Desconectado correctamente")

        except Exception as e:
            _logger.error(f"Error desconectando: {e}")

    def is_connected(self) -> bool:
        """Verifica si está conectado"""
        return self.connection and self.connection.is_connected()

    def get_realtime_dashboard_data(self) -> Dict[str, Any]:
        """Obtiene datos del dashboard en tiempo real"""
        if not self.is_connected():
            _logger.warning("⚠️ AMI no conectado")
            return {"queues": [], "agents": [], "calls": []}

        try:
            if not self.executor:
                raise ConnectionError("Executor AMI no disponible")
            data = self.executor.query_queue_status()
            data["last_update"] = datetime.now().isoformat()
            data["user_id"] = self.env.user.id
            return data
        except Exception as e:
            _logger.error(f"Error obteniendo datos: {e}")
            return {"queues": [], "agents": [], "calls": []}

    def _get_config(self):
        """Obtiene configuración de Odoo"""
        config = self.env["issabel.config"].sudo().search([], limit=1)
        if not config:
            raise ValueError("No existe configuración de Issabel")
        return config

    def _update_connection_state(self, state: str):
        """Actualiza estado de conexión en BD"""
        try:
            with self.env.registry.cursor() as new_cr:
                config = (
                    self.env["issabel.config"]
                    .with_env(self.env(cr=new_cr))
                    .sudo()
                    .search([], limit=1)
                )
                if config:
                    config.write(
                        {
                            "state": state,
                            "last_connection": (
                                datetime.now() if state == "connected" else False
                            ),
                        }
                    )
                    new_cr.commit()
        except Exception as e:
            _logger.error(f"Error actualizando estado: {e}")
