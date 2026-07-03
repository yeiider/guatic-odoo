from odoo import models, fields, api, tools, SUPERUSER_ID
from odoo.exceptions import ValidationError


class CrmAsertis(models.Model):
    _name = "crm_asertis"
    _description = "CRM Asertis"
    _inherit = ["mail.thread", "mail.activity.mixin", "image.mixin"]

    name = fields.Char("Nombre", required=True)

    area = fields.Selection(
        selection=[("Asertis", "Asertis"), ("Fenalsistemas", "Fenalsistemas")],
        string="Área",
        default=lambda self: self.env.user.area,
    )

    estado_id = fields.Many2one(
        "crm_asertis_stages",
        string="Estado",
        index=True,
        group_expand="_read_group_estado_ids",
        ondelete="restrict",
        domain="[('name', 'not in', ('Ganado', 'Perdido'))]",
        tracking=True,
    )

    company_currency = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id.id,
        readonly=True,
    )
    venta_proyectada = fields.Monetary(
        "Venta proyectada", currency_field="company_currency", tracking=True
    )

    # Información del cliente
    cliente = fields.Many2one(
        "crm_asertis_clientes", string="Cliente", index=True, tracking=True
    )
    cliente_correo = fields.Char(
        "Correo",
        tracking=True,
        compute="_compute_correo",
        inverse="_inverse_correo",
        readonly=False,
        store=True,
    )
    telefono = fields.Char(
        "Teléfono", tracking=True, related="cliente.phone", readonly=True, store=True
    )

    responsable = fields.Many2one(
        "res.users",
        string="Responsable",
        default=lambda self: self.env.user,
        index=True,
        tracking=True,
        required=True,
    )
    fecha_cierre = fields.Date("Fecha cierre", help="Fecha estimada de cierre")
    prioridad = fields.Selection(
        selection=[("0", "Baja"), ("1", "Media"), ("2", "Alta"), ("3", "Muy alta")],
        string="Prioridad",
        index=True,
        default="0",
        tracking=True,
    )
    servicios = fields.Many2many(
        "crm_asertis_servicios",  # Modelo relacionado (el de servicios)
        "crm_asertis_servicios_rel",  # Nombre de la tabla relacional
        "asertis_id",  # Campo que apunta a crm_asertis.id
        "servicio_id",  # Campo que apunta a crm_asertis.servicio.id
        string="Servicios",
    )
    descripcion = fields.Html("Notas")

    probabilidad = fields.Float(
        "Probabilidad", aggregator="avg", copy=False, readonly=False, store=True
    )

    actividades_ids = fields.One2many(
        "crm_asertis_actividades", "crm_id", string="Actividades"
    )

    estado_ganado = fields.Boolean(
        string="¿Estado ganado?", compute="_compute_estado_cerrado", store=True
    )
    estado_perdido = fields.Boolean(
        string="¿Estado perdido?", compute="_compute_estado_cerrado", store=True
    )

    @api.depends("estado_id")
    def _compute_estado_cerrado(self):
        """Valida si el lead está cerrado"""
        for rec in self:
            rec.estado_ganado = rec.estado_id.name == "Ganado"
            rec.estado_perdido = rec.estado_id.name == "Perdido"

    def establecer_ganado(self):
        estado_ganado = self.env["crm_asertis_stages"].search(
            [("name", "=", "Ganado")], limit=1
        )
        if not estado_ganado:
            raise ValidationError(
                "No se encontró el estado 'Ganado'. Verifica que exista en crm_asertis_stages."
            )
        for rec in self:
            rec.estado_id = estado_ganado.id
            rec.probabilidad = 100

    def establecer_perdido(self):
        estado_perdido = self.env["crm_asertis_stages"].search(
            [("name", "=", "Perdido")], limit=1
        )
        if not estado_perdido:
            raise ValidationError(
                "No se encontró el estado 'Perdido'. Verifica que exista en crm_asertis_stages."
            )
        for rec in self:
            rec.estado_id = estado_perdido.id
            rec.probabilidad = 0

    @api.model
    def _read_group_estado_ids(self, stages, domain):
        """Expande dinámicamente las columnas en la vista kanban."""
        return self.env["crm_asertis_stages"].search([], order="sequence, name")

    #####
    # Funciones para validar el correo del cliente y actualizar en res.partner en caso de haber un cambio en el CRM o viceversa
    #####

    @api.depends("cliente.email")
    def _compute_correo(self):
        for lead in self:
            if lead.cliente.email and lead._get_partner_email_update():
                lead.cliente_correo = lead.cliente.email

    def _inverse_correo(self):
        for lead in self:
            if lead._get_partner_email_update():
                lead.cliente.email = lead.cliente_correo

    def _get_partner_email_update(self):
        """Calculate if we should write the email on the related partner. When
        the email of the lead / partner is an empty string, we force it to False
        to not propagate a False on an empty string.

        Done in a separate method so it can be used in both ribbon and inverse
        and compute of email update methods.
        """
        self.ensure_one()
        if self.cliente and self.cliente_correo != self.cliente.email:
            lead_email_normalized = (
                tools.email_normalize(self.cliente_correo)
                or self.cliente_correo
                or False
            )
            partner_email_normalized = (
                tools.email_normalize(self.cliente.email) or self.cliente.email or False
            )
            return lead_email_normalized != partner_email_normalized
        return False

    def action_abrir_wizard_actividad(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "crm_asertis_actividades_wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_crm_id": self.id,
            },
        }
