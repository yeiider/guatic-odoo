import json
import base64
from cryptography.fernet import Fernet
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ChatProvider(models.Model):
    """
    ChatProvider Odoo Model
    This model represents the configuration for different chat providers integrated into the system.
    It securely manages authentication tokens using encryption, supports multiple provider types,
    and allows for advanced configuration via JSON. It also enforces constraints to ensure only one
    active provider per type and requires at least one allowed channel.
    Attributes:
        name (Char): Display name of the provider.
        provider_type (Selection): Type of chat provider (e.g., HeyNow, Botpress, Twilio, etc.).
        is_active (Boolean): Indicates if the provider configuration is active.
        _auth_token_encrypted (Text): Encrypted authentication token (internal use).
        _encryption_key (Text): Encryption key for the token (internal use).
        auth_token (Char): Computed field for the decrypted authentication token (not stored).
        base_url (Char): Base URL for sending messages via the provider.
        allowed_channel_ids (Many2many): Channels that this provider can handle.
        config_extra (Text): Additional configuration in JSON format.
    Methods:
        _compute_auth_token(): Computes the decrypted authentication token for display.
        _inverse_auth_token(): Encrypts and stores the authentication token when set.
        _encrypt_token(token): Encrypts a given token using Fernet symmetric encryption.
        _decrypt_token(encrypted_token): Decrypts an encrypted token using Fernet.
        set_auth_token(token): Securely sets the authentication token.
        get_auth_token(): Retrieves the decrypted authentication token.
        get_config_extra_dict(): Parses the JSON configuration into a Python dictionary.
        _check_allowed_channels(): Ensures at least one allowed channel is selected.
        _check_unique_active_provider(): Ensures only one active provider per type exists.
        toggle_active(): Toggles the active state of the provider.
    Raises:
        ValidationError: If JSON configuration is invalid, no allowed channels are selected,
                        or more than one active provider per type is set.
    """

    _name = "chat.provider"
    _description = "Configuración de Proveedor de Chat"
    _order = "provider_type"

    name = fields.Char(
        string="Nombre visible", required=True, help="Nombre del proveedor"
    )
    provider_type = fields.Selection(
        [
            ("heynow", "HeyNow"),
            ("botpress", "Botpress"),
            ("twilio", "Twilio"),
            ("meta", "Meta"),
            ("viber", "Viber"),
            ("whatsapp", "WhatsApp"),
            ("telegram", "Telegram"),
            ("line", "Line"),
            ("messenger", "Messenger"),
            ("instagram", "Instagram"),
            ("facebook", "Facebook"),
            ("google", "Google"),
        ],
        string="Tipo de Proveedor",
        required=True,
    )

    is_active = fields.Boolean(string="Activo", default=True)
    _auth_token_encrypted = fields.Text(string="Encrypted Token", readonly=True)
    _encryption_key = fields.Text(string="Encryption Key", readonly=True)

    auth_token = fields.Char(
        string="Token de Autenticación",
        compute="_compute_auth_token",
        inverse="_inverse_auth_token",
        store=False,
        help="Token de autenticación del proveedor (se guarda cifrado)",
    )

    base_url = fields.Char(
        string="URL Base",
        required=True,
        help="URL Base del proveedor para envíos de mensajes",
    )

    allowed_channel_ids = fields.Many2many(
        "chat.channel.type",
        string="Canales Permitidos",
        help="Selecciona los canales que este proveedor manejará.",
    )

    config_extra = fields.Text(
        string="Configuración adicional (JSON)",
        help="Puedes definir configuraciones avanzadas aquí",
    )
    skill_ids = fields.One2many(
        'provider.skill',
        'provider_id',
        string='Habilidades',
        help="Habilidades disponibles para este proveedor"
    )
    
    skill_count = fields.Integer(
        string='Número de Habilidades',
        compute='_compute_skill_count',
        store=True,
    )
    historial_config = fields.Text(
        string="Historial de Configuración",
        help="Historial de cambios en la configuración del proveedor"
    )

    @api.depends('skill_ids')
    def _compute_skill_count(self):
        for provider in self:
            provider.skill_count = len(provider.skill_ids)

    @api.depends("_auth_token_encrypted")
    def _compute_auth_token(self):
        """Compute method para mostrar el token descifrado"""
        for record in self:
            if record._auth_token_encrypted and record._encryption_key:
                record.auth_token = record._decrypt_token(record._auth_token_encrypted)
            else:
                record.auth_token = ""

    def _inverse_auth_token(self):
        """Inverse method para guardar el token cifrado"""
        for record in self:
            if record.auth_token:
                record._auth_token_encrypted = record._encrypt_token(record.auth_token)
            else:
                record._auth_token_encrypted = ""

    def _encrypt_token(self, token):
        """Cifra un token usando Fernet"""
        if not token:
            return ""

        if not self._encryption_key:
            key = Fernet.generate_key()
            self._encryption_key = base64.b64encode(key).decode()
        else:
            key = base64.b64decode(self._encryption_key.encode())

        f = Fernet(key)
        encrypted_token = f.encrypt(token.encode())
        return base64.b64encode(encrypted_token).decode()

    def _decrypt_token(self, encrypted_token):
        """Descifra un token usando Fernet"""
        if not encrypted_token or not self._encryption_key:
            return ""

        try:
            key = base64.b64decode(self._encryption_key.encode())
            f = Fernet(key)
            decrypted_data = base64.b64decode(encrypted_token.encode())
            return f.decrypt(decrypted_data).decode()
        except Exception:
            return ""

    def set_auth_token(self, token):
        """Establece el token de autenticación de forma segura"""
        self.ensure_one()
        if token:
            self._auth_token_encrypted = self._encrypt_token(token)
        else:
            self._auth_token_encrypted = ""

    def get_auth_token(self):
        """Obtiene el token de autenticación descifrado"""
        self.ensure_one()
        if self._auth_token_encrypted:
            return self._decrypt_token(self._auth_token_encrypted)
        return ""

    def get_config_extra_dict(self):
        """Convierte config_extra de JSON string a diccionario"""
        self.ensure_one()
        if self.config_extra:
            try:
                return json.loads(self.config_extra)
            except json.JSONDecodeError:
                raise ValidationError(
                    _(
                        "El campo de configuración adicional debe tener formato JSON válido."
                    )
                )
        return {}

    @api.constrains("allowed_channel_ids")
    def _check_allowed_channels(self):
        """Valida que se seleccione al menos un canal"""
        for record in self:
            if not record.allowed_channel_ids:
                raise ValidationError(
                    _("Debes seleccionar al menos un canal permitido.")
                )

    @api.constrains("provider_type", "is_active")
    def _check_unique_active_provider(self):
        """Valida que solo haya un proveedor activo por tipo"""
        for record in self:
            if record.is_active:
                existing = self.search(
                    [
                        ("provider_type", "=", record.provider_type),
                        ("is_active", "=", True),
                        ("id", "!=", record.id),
                    ]
                )
                if existing:
                    raise ValidationError(
                        _(
                            "Ya existe una configuración activa para el proveedor '%s'. Solo puede haber una activa."
                        )
                        % record.provider_type
                    )

    def toggle_active(self):
        """Alterna el estado activo del proveedor"""
        for rec in self:
            rec.is_active = not rec.is_active
    
    _sql_constraints = [
        ('unique_code', 'unique(code)', 'El código del proveedor debe ser único'),
        ('unique_name', 'unique(name)', 'El nombre del proveedor debe ser único')
    ]