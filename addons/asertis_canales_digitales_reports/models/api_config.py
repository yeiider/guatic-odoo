from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
import json
import base64
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
import logging
import pytz

_logger = logging.getLogger(__name__)


class ApiConfig(models.Model):
    _name = "api.config"
    _description = "Configuración de API Externa"
    _rec_name = "name"

    name = fields.Char("Nombre de Configuración", required=True)
    api_url = fields.Char("URL de la API", required=True)
    auth_url = fields.Char("URL de Autenticación", required=True)
    username = fields.Char("Usuario", required=True)
    password = fields.Char(
        string="Contraseña",
        compute="_get_password",
        inverse="_set_password",
        store=False,
    )
    password_encrypted = fields.Char(string="Encrypted Password", readonly=True)
    token = fields.Text("Token de Acceso")
    token_expiry = fields.Datetime("Expiración del Token")
    is_active = fields.Boolean("Activo", default=True)
    last_sync = fields.Datetime("Última Sincronización")
    _encryption_key = fields.Text(string="Encryption Key", readonly=True)

    def _generate_key(self):
        """
        Genera o recupera una clave Fernet segura de 32 bytes y la almacena en ir.config_parameter.
        """
        param = self.env["ir.config_parameter"].sudo()
        key = param.get_param("api_config_encryption_key")
        if not key:
            key = Fernet.generate_key().decode()  # clave en string
            param.set_param("api_config_encryption_key", key)
        return key.encode()  # convertir de nuevo a bytes para Fernet

    def _get_password(self):
        """
        Desencripta el valor de `password_encrypted` y lo pone en `password` (campo visible).
        """
        for rec in self:
            if rec.password_encrypted:
                try:
                    fernet = Fernet(rec._generate_key())
                    rec.password = fernet.decrypt(
                        rec.password_encrypted.encode()
                    ).decode()
                except Exception:
                    rec.password = ""
            else:
                rec.password = ""

    def _set_password(self):
        """
        Encripta el valor de `password` y lo guarda en `password_encrypted` (campo protegido).
        """
        for rec in self:
            if rec.password:
                fernet = Fernet(rec._generate_key())
                rec.password_encrypted = fernet.encrypt(rec.password.encode()).decode()
            else:
                rec.password_encrypted = ""

    def authenticate(self):
        """Autentica con la API y obtiene el token"""
        try:
            password = self.password

            auth_data = {"name": self.username, "password": password}

            response = requests.post(
                self.auth_url,
                json=auth_data,
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )

            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get("token", "")
                # Asume que el token expira en 24 horas
                self.token_expiry = fields.Datetime.now().replace(
                    hour=23, minute=59, second=59
                )
                self.last_sync = fields.Datetime.now()
                return True
            else:
                _logger.error(
                    f"Error en autenticación: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            _logger.error(f"Error en autenticación: {e}")
            return False

    def test_connection(self):
        """Prueba la conexión con la API"""
        if self.authenticate():
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Conexión Exitosa",
                    "message": "La conexión con la API se estableció correctamente",
                    "type": "success",
                },
            }
        else:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error de Conexión",
                    "message": "No se pudo conectar con la API. Verifica las credenciales.",
                    "type": "danger",
                },
            }

    def remove_token_api(self):
        from datetime import datetime, timedelta

        expiry_threshold = datetime.now() + timedelta(hours=2)
        configs_to_refresh = self.search(
            [("is_active", "=", True), ("token_expiry", "<=", expiry_threshold)]
        )
        for config in configs_to_refresh:
            config.authenticate()

    def is_token_valid(self):
        """Verifica si el token sigue siendo válido"""
        if not self.token or not self.token_expiry:
            return False
        return fields.Datetime.now() < self.token_expiry

    def _get_api_data_realtime(self, period=None):
        """Obtiene datos directamente de la API sin almacenar"""
        # Verificar o renovar token
        if not self.is_token_valid():
            if not self.authenticate():
                raise Exception(
                    f"No se pudo autenticar con la configuración {self.name}"
                )

        # Realizar petición a la API
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        now = datetime.now(pytz.UTC)

        # Intervalo de 30 días atrás
        from_date = now - timedelta(days=30)
        to_date = now

        # Formato ISO 8601 con 'Z'
        from_str = from_date.isoformat().replace("+00:00", "Z")
        to_str = to_date.isoformat().replace("+00:00", "Z")

        if period:
            
            from_period = period["start_date"]
            to_period = period["end_date"]
            from_str = from_period.isoformat().replace("+00:00", "Z")
            to_str = to_period.isoformat().replace("+00:00", "Z")

        params = {
            "from": from_str,
            "to": to_str,
            "allClients": False,
            "sessionReport": True,
        }
        try:
            response = requests.get(
                self.api_url, headers=headers, params=params, timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                _logger.error(f"Error en API: {response.status_code} - {response.text}")
                raise Exception(f"Error en API: {response.status_code}")

        except Exception as e:
            _logger.error(f"Error en petición API: {e}")
            raise Exception(f"Error conectando con la API: {e}")
