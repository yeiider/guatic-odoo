from odoo import models, fields, api, _


class ChatChannelType(models.Model):
    """
    Represents a type of chat channel in the system.

    This model is used to define different types of chat channels, such as WhatsApp, Telegram, etc.
    Each channel type has a unique name and code, and can be marked as active or inactive.

    Attributes:
        name (Char): The display name of the chat channel type. Required.
        code (Char): The unique code identifier for the channel type (e.g., 'whatsapp', 'telegram'). Required.
        active (Boolean): Indicates whether the channel type is active. Defaults to True.
    """

    _name = "chat.channel.type"
    _description = "Tipo de Canal"

    name = fields.Char(string="Nombre del Canal", required=True)
    code = fields.Char(
        string="Código", required=True, help="Ej: whatsapp, telegram, etc."
    )

    active = fields.Boolean(string="Activo", default=True)
