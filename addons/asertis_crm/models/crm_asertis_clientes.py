from odoo import models, fields, tools, api


class CrmAsertisClientes(models.Model):
    _name = "crm_asertis_clientes"
    _description = "CRM Asertis clientes"
    _inherit = ["mail.thread", "mail.activity.mixin", "image.mixin"]

    nombre = fields.Char(string="Nombre del cliente", required=True, tracking=True)
    tipo_documento = fields.Selection(
        selection=[("C.C.", "C.C."), ("NIT", "NIT"), ("C.E.", "C.E.")],
        default="C.C.",
        string="Tipo documento",
        required=True,
        tracking=True,
    )
    documento = fields.Char(string="Número documento", tracking=True)
    direccion_1 = fields.Char(string="Dirección 1", tracking=True)
    direccion_2 = fields.Char(string="Dirección 2", tracking=True)
    phone = fields.Char(string="Teléfono", tracking=True)
    ciudad = fields.Char(string="Ciudad", tracking=True)
    email = fields.Char(string="Correo electrónico", tracking=True)
    descripcion = fields.Html("Notas")
    responsable = fields.Many2one(
        "res.users", string="Responsable", index=True, tracking=True
    )
    area = fields.Selection(
        selection=[("Asertis", "Asertis"), ("Fenalsistemas", "Fenalsistemas")],
        string="Área",
        default=lambda self: self.env.user.area,
    )

    oportunidades_count = fields.Integer(
        "Oportunidades", compute="contador_oportunidades"
    )

    _sql_constraints = [
        (
            "unique_documento",
            "UNIQUE(documento)",
            "Ya existe un cliente con este número de documento.",
        )
    ]

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.nombre}"

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = [("nombre", operator, name)]
        results = self.search(domain + args, limit=limit)
        return [(result.id, result.name_get()[0][1]) for result in results]

    def contador_oportunidades(self):
        for rec in self:
            rec.oportunidades_count = (
                self.env["crm_asertis"].sudo().search_count([("cliente", "=", rec.id)])
            )

    def ver_oportunidades(self):
        return {
            "name": ("Oportunidades"),
            "res_model": "crm_asertis",
            "view_mode": "kanban,form",
            "context": {},
            "domain": [("cliente", "=", self.id)],
            "target": "current",
            "type": "ir.actions.act_window",
        }
