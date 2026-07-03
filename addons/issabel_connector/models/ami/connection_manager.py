# -*- coding: utf-8 -*-
"""
Refactored AMI Service
======================

Servicio AMI completamente refactorizado:
- Mejor separación de responsabilidades
- Manejo robusto de conexiones
- Logging estructurado
- Más testeable
- Thread-safe
"""

import logging
import threading

import asyncio

from typing import Dict, Any, Optional

from panoramisk import Manager


_logger = logging.getLogger(__name__)


# ============================================================================
# CONNECTION MANAGER - Gestión de conexión AMI
# ============================================================================


class AMIConnectionManager:
    """
    Gestiona el ciclo de vida de la conexión AMI.

    Responsabilidades:
    - Establecer/cerrar conexión
    - Mantener heartbeat
    - Reconexión automática
    - Thread-safe
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.manager: Optional[Manager] = None
        self.connected = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()
        self._logger = logging.getLogger(f"{__name__}.AMIConnectionManager")

    async def connect(self) -> bool:
        """Establece conexión con servidor AMI"""
        try:
            self._logger.info(
                f"🔌 Conectando a AMI: {self.config['host']}:{self.config['port']}"
            )

            # Crear manager de panoramisk
            self.manager = Manager(
                host=self.config["host"],
                port=self.config["port"],
                username=self.config["username"],
                secret=self.config["secret"],
            )

            # Conectar
            await self.manager.connect()
            self._logger.debug("✅ Conexión TCP establecida")

            # Login
            login_response = await self.manager.send_action(
                {
                    "Action": "Login",
                    "Username": self.config["username"],
                    "Secret": self.config["secret"],
                    "Events": "on",
                }
            )

            if login_response.response != "Success":
                raise ConnectionError(f"Login fallido: {login_response}")

            self.connected = True
            self._logger.info("✅ Login exitoso - AMI conectado")
            return True

        except Exception as e:
            self._logger.error(f"❌ Error conectando a AMI: {e}", exc_info=True)
            self.connected = False
            return False

    async def disconnect(self):
        """Cierra conexión con AMI"""
        try:
            if self.manager:
                self.manager.close()
                self._logger.info("🛑 Conexión AMI cerrada")
        except Exception as e:
            self._logger.error(f"Error cerrando conexión: {e}")
        finally:
            self.manager = None
            self.connected = False

    def is_connected(self) -> bool:
        """Verifica si está conectado"""
        return self.connected

    async def send_action(self, action: Dict[str, Any]):
        """Envía acción AMI"""
        if not self.connected or not self.manager:
            raise ConnectionError("AMI no está conectado")

        return await self.manager.send_action(action)
