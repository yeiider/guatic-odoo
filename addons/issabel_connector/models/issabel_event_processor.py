# -*- coding: utf-8 -*-
import logging
import time
from collections import defaultdict

from typing import Dict, Any

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class IssabelEventProcessor(models.Model):
    _name = "issabel.event.processor"
    _description = "Procesador de Eventos AMI - Real-time Dashboard"

    name = fields.Char(string="Nombre", default="Event Processor")
    _metrics = defaultdict(
        lambda: {"count": 0, "errors": 0, "last_reset": time.time()})
    _rate_limiter = defaultdict(list)

    # ========================================================================
   
    RATE_LIMIT_CONFIG = {
        "QueueMemberStatus": 10, 
        "QueueParams": 5,
        "QueueEntry": 5,
        "AgentConnect": 20,
        "QueueCallerJoin": 50,
        "PeerStatus": 3,  # Menos frecuente
        "ExtensionStatus": 3,
        "default": 100,  # Default para otros eventos
    }

    # Eventos críticos que siempre se notifican (bypass rate limit)
    CRITICAL_EVENTS = {
        "QueueCallerAbandon",
        "AgentComplete",
        "Hangup",
        "QueueMemberRemoved",
        "QueueMemberAdded",
    }

    @api.model
    def _initialize_runtime(self):
        """Inicializa métricas y rate limiter en memoria (por instancia)."""
        if not hasattr(self, "_metrics"):
            self._metrics = defaultdict(
                lambda: {"count": 0, "errors": 0, "last_reset": time.time()}
            )
        if not hasattr(self, "_rate_limiter"):
            self._rate_limiter = defaultdict(list)

    # ========================================================================
    # MÉTODO PRINCIPAL
    # ========================================================================

    def process_ami_event(self, event_type: str, event_data: Dict[str, Any]):
        """
        Método principal que procesa eventos AMI.

        Args:
            event_type: Tipo de evento AMI (ej: "QueueMemberStatus")
            event_data: Datos del evento

        Flujo:
        1. Validar evento
        2. Aplicar rate limiting
        3. Usar handler registrado del EventHandlerRegistry (si existe)
        4. Fallback a handlers legacy
        5. Registrar métricas
        """
        self._initialize_runtime()
        start_time = time.time()

        try:
            _logger.debug(f"🎯 Procesando: {event_type}")

            # 1. Validación básica
            if not self._validate_event(event_type, event_data):
                return False

            # 2. Rate limiting (excepto eventos críticos)
            if not self._check_rate_limit(event_type):
                _logger.debug(f"⏱️ Rate limit aplicado a {event_type}")
                self._record_metric(event_type, True, time.time() - start_time)
                return True  # No es error, solo rate limited

            # 3. Intentar procesar con EventHandlerRegistry
            success = self._process_with_registry(event_type, event_data)

            # 5. Registrar métricas
            self._record_metric(event_type, success, time.time() - start_time)

            return success

        except Exception as e:
            self._record_metric(event_type, False, time.time() - start_time)
            _logger.error(
                f"❌ Error procesando {event_type}: {e}",
                exc_info=True,
                extra={"event_type": event_type, "has_data": bool(event_data)},
            )
            raise

    # ========================================================================
    # PROCESAMIENTO CON REGISTRY
    # ========================================================================

    def _process_with_registry(
        self, event_type: str, event_data: Dict[str, Any]
    ) -> bool:
        """
        Intenta procesar el evento usando el EventHandlerRegistry.

        Returns:
            True si fue procesado exitosamente
            False si no hay handler o falló
        """
        try:
            # Importar registry (lazy import para evitar circular)
            from .base import EventHandlerRegistry

            # Obtener handler registrado
            registry = EventHandlerRegistry()
            handler = registry.get_handler(self.env, event_type)

            if not handler:
                _logger.debug(
                    f"ℹ️ No hay handler registrado para {event_type}")
                return False

            # Procesar con el handler
            # El handler ya se encarga de:
            # - Extraer datos
            # - Validar
            # - Notificar al dashboard
            success = handler.process(event_type, event_data)

            if success:
                _logger.debug(f"✅ {event_type} procesado por registry")
            else:
                _logger.warning(f"⚠️ Registry no pudo procesar {event_type}")

            return success

        except ImportError:
            _logger.debug(
                "ℹ️ EventHandlerRegistry no disponible, usando handlers legacy"
            )
            return False
        except Exception as e:
            _logger.error(f"❌ Error en registry para {event_type}: {e}")
            return False

    # ========================================================================
    # VALIDACIÓN Y RATE LIMITING
    # ========================================================================

    def _validate_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Valida que el evento tiene datos mínimos"""
        if not event_type:
            _logger.warning("⚠️ Evento sin tipo")
            return False

        if not isinstance(event_data, dict):
            _logger.warning(
                f"⚠️ Datos inválidos para {event_type}: no es dict")
            return False

        if not event_data:
            _logger.debug(
                f"ℹ️ Evento {event_type} sin datos (puede ser normal)")
            # Algunos eventos pueden venir vacíos, no es necesariamente error
            return True

        return True

    def _check_rate_limit(self, event_type: str) -> bool:
        """
        Verifica si el evento puede ser procesado según rate limit.

        Returns:
            True si puede procesar, False si debe ser descartado
        """
        # Eventos críticos siempre pasan
        if event_type in self.CRITICAL_EVENTS:
            return True

        # Obtener límite para este tipo de evento
        limit = self.RATE_LIMIT_CONFIG.get(
            event_type, self.RATE_LIMIT_CONFIG["default"]
        )

        # Obtener timestamps de eventos recientes
        now = time.time()
        recent_events = self._rate_limiter[event_type]

        # Limpiar eventos antiguos (> 1 segundo)
        recent_events[:] = [ts for ts in recent_events if now - ts < 1.0]

        # Verificar límite
        if len(recent_events) >= limit:
            return False

        # Agregar timestamp actual
        recent_events.append(now)
        return True

    # ========================================================================
    # MÉTRICAS
    # ========================================================================

    def _record_metric(self, event_type: str, success: bool, duration: float):
        """Registra métricas de procesamiento"""
        metric = self._metrics[event_type]
        metric["count"] += 1

        if not success:
            metric["errors"] += 1

        # Acumular duración
        if "total_duration" not in metric:
            metric["total_duration"] = 0
        metric["total_duration"] += duration

        # Log periódico de métricas (cada 100 eventos)
        if metric["count"] % 100 == 0:
            self._log_metrics(event_type, metric)

    def _log_metrics(self, event_type: str, metric: Dict[str, Any]):
        """Logea métricas acumuladas"""
        avg_duration = metric["total_duration"] / metric["count"]
        error_rate = (metric["errors"] / metric["count"]) * 100

        _logger.info(
            f"📊 Métricas {event_type}: "
            f"count={metric['count']}, "
            f"errors={metric['errors']} ({error_rate:.1f}%), "
            f"avg_duration={avg_duration*1000:.2f}ms"
        )

    @api.model
    def get_processing_metrics(self) -> Dict[str, Any]:
        """
        Retorna métricas de procesamiento (para debugging/monitoring).

        Uso: desde shell Odoo o endpoint HTTP custom
        """
        return {
            event_type: {
                "count": metrics["count"],
                "errors": metrics["errors"],
                "error_rate": (
                    (metrics["errors"] / metrics["count"] * 100)
                    if metrics["count"] > 0
                    else 0
                ),
                "avg_duration_ms": (
                    (metrics.get("total_duration", 0) /
                     metrics["count"] * 1000)
                    if metrics["count"] > 0
                    else 0
                ),
            }
            for event_type, metrics in self._metrics.items()
        }

    @api.model
    def reset_metrics(self):
        """Resetea métricas (útil para testing)"""
        self._metrics.clear()
        self._rate_limiter.clear()
        _logger.info("🔄 Métricas reseteadas")

    # ========================================================================
    # MANTENIMIENTO Y LIMPIEZA
    # ========================================================================

    def clean_ami_queue_jobs(self):
        """
        Elimina los registros procesados o fallidos del canal 'ami_events'.
        """
        try:
            job_model = self.env["queue.job"].sudo()

            domain = [
                ("channel", "=", "ami_events"),
                ("state", "in", ["done", "cancelled"]),
            ]

            jobs_to_delete = job_model.search(domain, limit=5000)

            if jobs_to_delete:
                count = len(jobs_to_delete)
                jobs_to_delete.unlink()
                _logger.info(f"🧹 {count} jobs eliminados del canal ami_events")
                return count
            else:
                _logger.debug("🧹 No hay jobs para limpiar")
                return 0

        except Exception as e:
            _logger.error(f"❌ Error limpiando jobs: {e}", exc_info=True)
            return 0

    @api.model
    def cron_cleanup_old_jobs(self):
        """
        Cron para limpiar jobs antiguos automáticamente.

        Programar este cron cada hora:
        - Modelo: issabel.event.processor
        - Método: cron_cleanup_old_jobs
        - Intervalo: 1 hora
        """
        _logger.info("🧹 Iniciando limpieza automática de jobs...")
        count = self.clean_ami_queue_jobs()
        _logger.info(f"🧹 Limpieza completada: {count} jobs eliminados")
