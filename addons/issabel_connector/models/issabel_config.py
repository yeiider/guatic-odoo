from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class IssabelConfig(models.Model):
    _name = "issabel.config"
    _description = "Configuración Issabel/Asterisk"

    name = fields.Char(string="Nombre", default="Configuración Issabel", required=True)
    ami_host = fields.Char(string="Host AMI", default="127.0.0.1", required=True)
    ami_port = fields.Integer(string="Puerto AMI", default=5038, required=True)
    ami_user = fields.Char(string="Usuario AMI", required=True)
    ami_password = fields.Char(string="Contraseña AMI", password=True, required=True)

    state = fields.Selection(
        [("connected", "Conectado"), ("disconnected", "Desconectado")],
        string="Estado",
        default="disconnected",
        readonly=True,
        tracking=True,
    )

    last_connection = fields.Datetime(string="Última conexión", readonly=True)
    last_test_result = fields.Selection(
        [("success", "Éxito"), ("failed", "Fallido")],
        string="Resultado Última Prueba",
        readonly=True,
    )
    last_test_message = fields.Text(string="Mensaje de Prueba", readonly=True)

    # Control de servicio
    auto_connect = fields.Boolean(
        string="Conectar Automáticamente",
        default=False,
        help="Conectar automáticamente al iniciar Odoo",
    )

    _sql_constraints = [
        ("unique_config", "unique(name)", "Solo puede existir una configuración")
    ]

    def _get_ami_service(self):
        """Obtiene instancia del servicio AMI"""
        from ..services.ami_service import AMIService

        return AMIService(self.env)

    def action_test_connection(self):
        """Prueba de conexión rápida con ping"""
        self.ensure_one()

        try:
            import asyncio
            from panoramisk import Manager

            # Crear event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            async def test_ami():
                manager = Manager(
                    host=self.ami_host,
                    port=self.ami_port,
                    username=self.ami_user,
                    secret=self.ami_password,
                )
                await manager.connect()
                response = await manager.send_action({"Action": "Ping"})
                manager.close()
                return response

            response = loop.run_until_complete(test_ami())

            if response and response.response == "Success":
                self.write(
                    {
                        "last_connection": fields.Datetime.now(),
                        "last_test_result": "success",
                        "last_test_message": "✅ Conexión exitosa. Ping respondido correctamente.",
                    }
                )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("✅ Éxito"),
                        "message": _("Conexión exitosa con Asterisk/Issabel."),
                        "type": "success",
                        "sticky": False,
                    },
                }
            else:
                raise Exception("Respuesta inválida del servidor")

        except Exception as e:
            error_msg = f"❌ Error de conexión: {str(e)}"
            self.write(
                {
                    "last_test_result": "failed",
                    "last_test_message": error_msg,
                }
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("❌ Error"),
                    "message": error_msg,
                    "type": "danger",
                    "sticky": True,
                },
            }

    def action_connect_ami(self):
        """Conectar al servicio AMI y comenzar a escuchar eventos"""
        self.ensure_one()

        try:
            ami_service = self._get_ami_service()

            if ami_service.is_connected():
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("⚠️ Advertencia"),
                        "message": _("El servicio AMI ya está conectado."),
                        "type": "warning",
                    },
                }

            # Conectar
            success = ami_service.connect()

            if success:
                self.write(
                    {
                        "state": "connected",
                        "last_connection": fields.Datetime.now(),
                    }
                )

                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("✅ Conectado"),
                        "message": _(
                            "Servicio AMI conectado. Escuchando eventos en tiempo real."
                        ),
                        "type": "success",
                    },
                }
            else:
                raise Exception("No se pudo establecer conexión")

        except Exception as e:
            _logger.exception("Error conectando AMI")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("❌ Error"),
                    "message": f"Error: {str(e)}",
                    "type": "danger",
                    "sticky": True,
                },
            }

    def action_disconnect_ami(self):
        """Desconectar del servicio AMI"""
        self.ensure_one()

        try:
            ami_service = self._get_ami_service()
            ami_service.disconnect()

            self.write({"state": "disconnected"})

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("🛑 Desconectado"),
                    "message": _("Servicio AMI desconectado."),
                    "type": "info",
                },
            }

        except Exception as e:
            _logger.exception("Error desconectando AMI")
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("❌ Error"),
                    "message": f"Error: {str(e)}",
                    "type": "danger",
                },
            }

    @api.model
    def cron_auto_connect(self):
        """Cron para reconectar automáticamente si se pierde la conexión"""
        configs = self.search([("auto_connect", "=", True)])

        for config in configs:
            try:
                ami_service = config._get_ami_service()

                if not ami_service.is_connected():
                    _logger.info("🔄 Reconectando AMI automáticamente...")
                    ami_service.connect()

            except Exception as e:
                _logger.error(f"Error en auto-reconexión: {e}")

    def get_values(self):
        """Método de compatibilidad - retorna dict con configuración"""
        self.ensure_one()
        return {
            "ami_host": self.ami_host,
            "ami_port": self.ami_port,
            "ami_user": self.ami_user,
            "ami_password": self.ami_password,
        }
