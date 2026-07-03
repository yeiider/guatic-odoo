from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
from datetime import datetime, timedelta
import logging
import pytz

_logger = logging.getLogger(__name__)


class ApiReport(models.Model):
    _name = "api.report"
    _description = "Reportes de API Externa"
    _order = "create_date desc"

    name = fields.Char("Nombre del Reporte", compute="_compute_name", store=True)
    config_id = fields.Many2one(
        "api.config", "Configuración API", required=True, ondelete="cascade"
    )
    data = fields.Json("Datos del Reporte", help="Datos crudos del reporte")
    sync_date = fields.Datetime("Fecha de Sincronización", default=fields.Datetime.now)

    @api.depends("sync_date")
    def _compute_name(self):
        for record in self:
            if record.sync_date:
                record.name = f"Plataforms Reports - {record.sync_date.strftime('%Y-%m-%d %H:%M')}"
            else:
                record.name = "Reporte sin nombre"

    @api.model
    def get_period_domain(self, period_type):
        """Obtiene el dominio para filtrar por período"""
        period = self.get_period_report(period_type)
        return [
            ("sync_date", ">=", period["start_date"]),
            ("sync_date", "<=", period["end_date"]),
        ]

    def get_period_report(self, period_type):
        """Obtiene el dominio para filtrar por período"""
        now = datetime.now(pytz.UTC)

        if period_type == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period_type == "week":
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)
        elif period_type == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end_date = now.replace(year=now.year + 1, month=1, day=1) - timedelta(
                    microseconds=1
                )
            else:
                end_date = now.replace(month=now.month + 1, day=1) - timedelta(
                    microseconds=1
                )
        elif period_type == "last_month":
            if now.month == 1:
                start_date = now.replace(
                    year=now.year - 1,
                    month=12,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
                end_date = now.replace(day=1) - timedelta(microseconds=1)
            else:
                start_date = now.replace(
                    month=now.month - 1,
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
                end_date = now.replace(day=1) - timedelta(microseconds=1)
        else:  # default to last 30 days
            start_date = now - timedelta(days=30)
            end_date = now

        return {"start_date": start_date, "end_date": end_date}

    @api.model
    def sync_reports(self, config_id=None, to_date=None, from_date=None):
        """Sincroniza reportes desde la API"""
        configs = self.env["api.config"].search([("is_active", "=", True)])
        if config_id:
            configs = self.env["api.config"].search(
                [("id", "=", config_id), ("is_active", "=", True)]
            )
            if not configs:
                raise UserError(f"Configuración con ID {config_id} no encontrada")

        if not configs:
            raise UserError("No hay configuraciones de API activas")

        for config in configs:
            try:
                self._sync_config_reports(config)
            except Exception as e:
                _logger.error(f"Error sincronizando reportes para {config.name}: {e}")
                raise UserError(f"Error sincronizando reportes para {config.name}: {e}")

    def _sync_config_reports(self, config):
        """Sincroniza reportes para una configuración específica"""
        # Verificar o renovar token
        if not config.is_token_valid():
            if not config.authenticate():
                raise UserError(
                    f"No se pudo autenticar con la configuración {config.name}"
                )

        # Realizar petición a la API
        headers = {
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/json",
        }

        now = datetime.now(pytz.UTC)

        # Intervalo de 30 días atrás
        from_date = now - timedelta(days=30)
        to_date = now

        # Formato ISO 8601 con 'Z'
        from_str = from_date.isoformat().replace("+00:00", "Z")
        to_str = to_date.isoformat().replace("+00:00", "Z")
        params = {
            "from": from_str,
            "to": to_str,
            "allClients": False,
            "sessionReport": True,
        }

        try:
            response = requests.get(
                config.api_url, headers=headers, params=params, timeout=30
            )
            _logger.info(
                f"Respuesta de la API para {config.name}: {response.status_code}",
            )

            if response.status_code == 200:
                _logger.info(
                    f"Datos obtenidos correctamente de la API para {config.name}"
                )
                data = response.json()
                self._process_api_data(data, config)
            else:
                _logger.error(f"Error en API: {response.status_code} - {response.text}")
                raise UserError(
                    f"Error en API: {response.status_code} - {response.text}"
                )

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error en petición API: {e}")
            raise UserError(f"Error conectando con la API: {e}")

    def _process_api_data(self, data, config):
        """Procesa los datos recibidos de la API"""
        _logger.info(f"Procesando datos para configuración {config}")

        return self._create_report_from_data(data, config)

    def _create_report_from_data(
        self,
        data,
        config,
    ):
        """Crea un reporte desde los datos de la API"""
        if not config or not config.id:
            _logger.error("Config is required to create report")
            return
        report_data = self._process__data(data)
        return self.create_report(config.id, report_data)

    def create_report(self, config_id, data):
        vals = {
            "config_id": config_id,
            "data": data,
        }

        # Verificar duplicados antes de crear
        existing = self.search(
            [
                ("config_id", "=", config_id),
                (
                    "sync_date",
                    ">=",
                    fields.Datetime.now().replace(hour=0, minute=0, second=0),
                ),
            ]
        )

        if existing:

            existing.write({"data": data, "sync_date": fields.Datetime.now()})
            return existing

        try:
            report = self.create(vals)
            _logger.info("Reporte creado para esta configuracion ")
            return report
        except Exception as e:
            _logger.error(f"Error creando reporte: {e}, vals: {vals}")
            raise

    @api.model
    def clean_old_reports(self):
        """Limpia reportes antiguos, manteniendo solo los últimos 30 días"""
        cutoff_date = datetime.now() - timedelta(days=30)
        old_reports = self.search([("sync_date", "<", cutoff_date)])
        if old_reports:
            old_reports.unlink()
            _logger.info(f"Eliminados {len(old_reports)} reportes antiguos")

    def action_sync_now(self):
        """Acción para sincronizar reportes manualmente"""
        if not self.config_id:
            raise UserError("Debe especificar una configuración de API")

        self.sync_reports(self.config_id.id)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Sincronización Completa",
                "message": "Los reportes se han sincronizado correctamente",
                "type": "success",
            },
        }

    @api.model
    def get_dashboard_data(self, config_id=None, period_type="last_month"):
        """Obtiene datos para el dashboard con filtro de período"""
        _logger.info(
            f"Obteniendo datos para dashboard api report con config_id: {config_id}"
        )
        domain = []
        if config_id:
            domain.append(("config_id", "=", config_id))

        # Agregar filtro de período
        period_domain = self.get_period_domain(period_type)
        domain.extend(period_domain)

        reports = self.search(domain, limit=100, order="sync_date desc")

        if not reports:
            return {
                "summary": {
                    "total_sessions": 0,
                    "total_messages": 0,
                    "total_contacts": 0,
                    "avg_session_length": 0,
                    "avg_waiting_time": 0,
                },
                "charts": {
                    "sessions_by_platform": [],
                    "messages_comparison": [],
                    "session_trends": [],
                    "waiting_times": [],
                },
                "bot_details": [],
            }

        return reports.data

    @api.model
    def get_last_report(self, config_id=None):
        """Obtiene el último reporte insertado, opcionalmente filtrando por config_id"""
        domain = []
        if config_id:
            domain.append(("config_id", "=", config_id))

        last_report = self.search(domain, order="sync_date desc", limit=1)
        return last_report or False

    def _process__data(self, api_data):
        """Procesa datos de la base de datos para el dashboard"""
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
