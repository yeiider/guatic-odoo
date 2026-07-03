from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProviderSkill(models.Model):
    """
    Modelo para gestionar habilidades de proveedores de chat
    """

    _name = "provider.skill"
    _description = "Gestión de Habilidades"
    _rec_name = "name"
    _order = "provider_id, priority, name"

    # Campos básicos
    name = fields.Char(
        string="Nombre de la Habilidad",
        required=True,
        help="Nombre descriptivo de la habilidad (ej: comercial, soporte, ventas)",
    )

    code = fields.Char(
        string="Código", help="Código único para identificar la habilidad"
    )

    description = fields.Text(
        string="Descripción", help="Descripción detallada de la habilidad"
    )

    active = fields.Boolean(
        string="Activo", default=True, help="Indica si la habilidad está activa"
    )

    # Relación con proveedor
    provider_id = fields.Many2one(
        "chat.provider",
        string="Proveedor",
        required=True,
        ondelete="cascade",
        help="Proveedor al que pertenece esta habilidad",
    )

    # Campos adicionales
    priority = fields.Integer(
        string="Prioridad",
        default=10,
        help="Orden de prioridad de la habilidad (menor número = mayor prioridad)",
    )

    # Restricciones
    _sql_constraints = [
        (
            "unique_skill_provider",
            "unique(name, provider_id)",
            "El nombre de la habilidad debe ser único por proveedor",
        ),
        (
            "unique_code_provider",
            "unique(code, provider_id)",
            "El código de la habilidad debe ser único por proveedor",
        ),
    ]

    @api.constrains("code")
    def _check_code_format(self):
        """Validar formato del código"""
        for record in self:
            if record.code:
                # Solo permitir letras, números y guiones bajos
                import re

                if not re.match(r"^[a-zA-Z0-9_]+$", record.code):
                    raise ValidationError(
                        "El código solo puede contener letras, números y guiones bajos"
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") and vals.get("name"):
                vals["code"] = vals["name"].lower().replace(" ", "_")
        return super().create(vals_list)
