from time import sleep
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class ApiReportDashboardController(http.Controller):

    @http.route("/api_reporting/dashboard", type="http", auth="user", website=True)
    def dashboard(self, **kwargs):
        """Renderiza el dashboard principal"""
        # Verificar que existe al menos una configuración activa
        config = request.env["api.config"].search([("is_active", "=", True)], limit=1)
        _logger.info(f"Configuración activa encontrada: {config}")
        if not config:
            return request.render(
                "web.error_page",
                {
                    "error_title": "Configuración Requerida",
                    "error_message": "No hay configuraciones de API activas. Configure al menos una API antes de acceder al dashboard.",
                },
            )

        return request.render(
            "asertis_canales_digitales_reports.dashboard_template",
            {
                "default_config_id": config.id,
                "available_configs": request.env["api.config"].search(
                    [("is_active", "=", True)]
                ),
            },
        )

    @http.route("/api_reporting/get_data", type="json", auth="user")
    def get_dashboard_data(self, config_id, period_type="last_month", force_sync=False):
        """Obtiene datos para el dashboard con filtro de período"""
        try:
            _logger.info(f"Obteniendo datos dashboard para config_id: {config_id}")
            # Validar config_id
            if not config_id:
                config = request.env["api.config"].search(
                    [("is_active", "=", True)], limit=1
                )
                if not config:
                    return {
                        "success": False,
                        "error": "No hay configuraciones de API disponibles",
                    }
                config_id = config.id

            # Verificar que la configuración existe
            config = request.env["api.config"].browse(config_id)
            # sleep(2)
            if not config.exists():
                return {"success": False, "error": "Configuración no encontrada"}

            # Si force_sync=True, sincroniza antes de obtener datos
            if force_sync:
                request.env["api.report"].sync_reports(config_id)

            # Obtener datos procesados con filtro de período
            data = request.env["api.report"].get_dashboard_data(config_id, period_type)
            return {"success": True, "data": data}
        except Exception as e:
            _logger.error(f"Error obteniendo datos dashboard: {e}")
            return {"success": False, "error": str(e)}

    @http.route("/api_reporting/sync_now", type="json", auth="user")
    def sync_now(self, config_id=None):
        """Sincroniza datos inmediatamente"""
        try:
            # Validar config_id
            if not config_id:
                config = request.env["api.config"].search(
                    [("is_active", "=", True)], limit=1
                )
                if not config:
                    return {
                        "success": False,
                        "error": "No hay configuraciones de API disponibles",
                    }
                config_id = config.id
            _logger.info(f"Sincronizando configuración ID: {config_id}")

            request.env["api.report"].sync_reports(config_id)
            return {
                "success": True,
                "message": "Sincronización completada exitosamente",
            }
        except Exception as e:
            _logger.error(f"Error en sincronización: {e}")
            return {"success": False, "error": str(e)}

    @http.route("/api_reporting/get_realtime_data", type="json", auth="user")
    def get_realtime_data(self, config_id, period_type="last_month"):
        """Obtiene datos en tiempo real sin guardar en BD"""
        try:
            # Validar config_id
            if not config_id:
                return {"success": False, "error": "config_id es requerido"}

            config = request.env["api.config"].browse(config_id)
            if not config.exists():
                return {"success": False, "error": "Configuración no encontrada"}
            period = request.env["api.report"].get_period_report(period_type)
            _logger.info(
                f"Obteniendo datos en tiempo real para config_id: {config_id} para el periodo de {period}"
            )
            # Obtener datos directamente de la API
            data = config._get_api_data_realtime(period)

            # Procesar datos para el dashboard
            processed_data = self._process_realtime_data(data)
            
            request.env["api.report"].create_report(config_id, processed_data)

            return {"success": True, "data": processed_data, "is_realtime": True}
        except Exception as e:
            _logger.error(f"Error obteniendo datos en tiempo real: {e}")
            # Si es un error de autenticación, devolverlo directamente
            if "Unauthorized" in str(e):
                return {"success": False, "error": str(e), "is_realtime": True}
            # Obtener el ultomo reporte instertado en base de datos
            last_report = request.env["api.report"].get_last_report(config_id)
            if last_report:
                # Si hay un reporte, devolverlo
                return {
                    "success": True,
                    "data": last_report.data,
                    "is_realtime": False,
                }
            return {"success": False, "error": str(e)}

    def _process_realtime_data(self, api_data):
        """Procesa datos de la API para el dashboard"""
        if not api_data:
            return {}

        # Si es un array, procesamos todos los elementos
        if isinstance(api_data, list):
            total_sessions = sum(item.get("totalSessions", 0) for item in api_data)
            total_messages = sum(item.get("totalMessages", 0) for item in api_data)
            total_contacts = sum(item.get("uniqueContacts", 0) for item in api_data)

            chart_data = []
            bot_details = []

            for item in api_data:
                chart_item = {
                    "platform_id": item.get("platformId", "Unknown"),
                    "total_sessions": item.get("totalSessions", 0),
                    "total_messages": item.get("totalMessages", 0),
                    "incoming_messages": item.get("totalIncomingMessages", 0),
                    "outgoing_messages": item.get("totalOutcomingMessages", 0),
                    "unique_contacts": item.get("uniqueContacts", 0),
                    "avg_session_length": item.get("avgSessionLength", 0),
                    "avg_waiting_time": item.get("avgWaitingTime", 0),
                    "abandoned_sessions": item.get("totalAbandoned", 0),
                    "sessions_with_panel": item.get("totalSessionPannel", 0),
                    "bot_name": item.get("bot", {}).get("name", "Unknown Bot"),
                }
                chart_data.append(chart_item)

                # Agregar a detalles de bot
                bot_details.append(
                    {
                        "name": chart_item["bot_name"],
                        "platform_id": chart_item["platform_id"],
                        "sessions": chart_item["total_sessions"],
                        "sessions_abandoned": chart_item["abandoned_sessions"],
                        "sessions_with_panel": chart_item["sessions_with_panel"],
                        "unique_contacts": chart_item["unique_contacts"],
                        "incoming_messages": chart_item["incoming_messages"],
                        "outgoing_messages": chart_item["outgoing_messages"],
                        "avg_waiting_time": chart_item["avg_waiting_time"],
                        "avg_session_length": chart_item["avg_session_length"],
                    }
                )
        else:
            # Si es un solo objeto
            total_sessions = api_data.get("totalSessions", 0)
            total_messages = api_data.get("totalMessages", 0)
            total_contacts = api_data.get("uniqueContacts", 0)

            chart_data = [
                {
                    "platform_id": api_data.get("platformId", "Unknown"),
                    "total_sessions": total_sessions,
                    "total_messages": total_messages,
                    "incoming_messages": api_data.get("totalIncomingMessages", 0),
                    "outgoing_messages": api_data.get("totalOutcomingMessages", 0),
                    "unique_contacts": total_contacts,
                    "avg_session_length": api_data.get("avgSessionLength", 0),
                    "avg_waiting_time": api_data.get("avgWaitingTime", 0),
                    "abandoned_sessions": api_data.get("totalAbandoned", 0),
                    "sessions_with_panel": api_data.get("totalSessionPannel", 0),
                    "bot_name": api_data.get("bot", {}).get("name", "Unknown Bot"),
                }
            ]

            bot_details = [
                {
                    "name": api_data.get("bot", {}).get("name", "Unknown Bot"),
                    "platform_id": api_data.get("platformId", "Unknown"),
                    "sessions": total_sessions,
                    "sessions_abandoned": api_data.get("totalAbandoned", 0),
                    "sessions_with_panel": api_data.get("totalSessionPannel", 0),
                    "unique_contacts": total_contacts,
                    "incoming_messages": api_data.get("totalIncomingMessages", 0),
                    "outgoing_messages": api_data.get("totalOutcomingMessages", 0),
                    "avg_waiting_time": api_data.get("avgWaitingTime", 0),
                    "avg_session_length": api_data.get("avgSessionLength", 0),
                }
            ]

        return {
            "summary": {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "total_contacts": total_contacts,
                "avg_waiting_time": (
                    sum(item.get("avg_waiting_time", 0) for item in chart_data)
                    / len(chart_data)
                    if chart_data
                    else 0
                ),
            },
            "chart_data": chart_data,
            "bot_details": bot_details,
        }
