from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from .payloads.base_event import ContactMetadata
from .utils.res_partner import ContactFormatter, PartnerSearchCriteria
from .utils.retry import retry_on_transient_error
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    provider_user_id = fields.Char(
        string="Provider User ID",
        help="Unique user ID from the chat provider",
        index=True,
        copy=False,
    )
    provider_name = fields.Char(
        string="Provider Name",
        help="Name of the chat provider",
        index=True,
    )
    is_provider_chat_user = fields.Boolean(
        string="Is Provider Chat User",
        default=False,
        help="Indicates this partner is linked to a chat provider",
        index=True,
    )

    provider_skill_ids = fields.Many2many(
        "provider.skill",
        "partner_provider_skill_rel",
        "partner_id",
        "skill_id",
        string="Habilidades del Proveedor",
        help="Habilidades asignadas a este contacto",
        domain=[("active", "=", True)],
    )

    skill_count = fields.Integer(
        string="Número de Habilidades",
        compute="_compute_skill_count",
    )
    active_skill_ids = fields.Many2many(
        "provider.skill",
        compute="_compute_active_skills",
        string="Habilidades Activas",
    )

    _sql_constraints = [
        (
            "unique_provider_user_id",
            "UNIQUE(provider_user_id)",
            "Provider user ID must be unique.",
        )
    ]

    # --------------------------
    # Computes
    # --------------------------

    @api.depends("provider_skill_ids")
    def _compute_skill_count(self):
        for partner in self:
            partner.skill_count = len(partner.provider_skill_ids)

    @api.depends("provider_skill_ids.active")
    def _compute_active_skills(self):
        for partner in self:
            partner.active_skill_ids = partner.provider_skill_ids.filtered("active")

    # --------------------------
    # Public methods
    # --------------------------

    def action_view_provider_skills(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Habilidades de %s") % self.name,
            "res_model": "provider.skill",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.provider_skill_ids.ids)],
            "context": {"create": False, "edit": False},
        }

    def get_skills_by_provider(self, provider_code):
        return self.provider_skill_ids.filtered(
            lambda s: s.provider_id.code == provider_code and s.active
        )

    def has_skill(self, skill_code, provider_code=None):
        domain = [("code", "=", skill_code), ("active", "=", True)]
        if provider_code:
            domain.append(("provider_id.code", "=", provider_code))
        return bool(self.provider_skill_ids.filtered_domain(domain))

    def find_or_create_partner(self, provider_data, contact_metadata=None):
        self._validate_provider_data(provider_data)

        user_id = provider_data.get("user_id")
        _logger.info("No partner found with contact_metadata: %s", contact_metadata)

        partner = self._find_by_provider_user_id(user_id)
        if partner:
            self._enqueue_updates(partner, provider_data, contact_metadata)
            return partner

        if contact_metadata:
            partner = self._find_by_contact_metadata(contact_metadata)
            if partner:
                self._enqueue_updates(partner, provider_data, contact_metadata)
                return partner

        return self._create_new_partner(provider_data, contact_metadata)

    def _enqueue_updates(self, partner, provider_data, contact_metadata=None):
        try:
            if contact_metadata:
                self.with_delay(
                    channel="root.partner_update.contact",
                    description=f"Update contact info for partner {partner.id}",
                    priority=5,
                ).update_partner_contact_info_job(partner, contact_metadata.to_json())

            self.with_delay(
                channel="root.partner_update.provider",
                description=f"Link partner {partner.id} to provider {provider_data.get('provider_name')}",
                priority=10,
            ).link_partner_to_provider_job(partner, provider_data)

            _logger.info("Queued update jobs for partner %s", partner.id)
        except Exception as e:
            _logger.warning("Async update failed: %s. Falling back to sync.", e)
            if contact_metadata:
                self._update_partner_contact_info(partner, contact_metadata)
            self._link_provider_fields(partner, provider_data)

    def link_partner_to_provider_job(self, partner, provider_data):
        return self._link_provider_fields(partner, provider_data)

    def update_partner_contact_info_job(self, partner, contact_metadata_json):
        contact_metadata = ContactMetadata.from_json(contact_metadata_json)
        return self._update_partner_contact_info(partner, contact_metadata)

    # --------------------------
    # Private search helpers
    # --------------------------

    def _find_by_provider_user_id(self, user_id):
        if not user_id:
            return self.env["res.partner"]
        return self.sudo().search([("provider_user_id", "=", user_id)], limit=1)

    def _find_by_contact_metadata(self, contact_metadata):
        domain = PartnerSearchCriteria.build_contact_search_domain(contact_metadata)
        if not domain:
            _logger.info("No valid search domain could be built.")
            return self.env["res.partner"]
        try:
            res = self.search(domain, limit=1)
            _logger.info("Found partner %s using contact metadata", res.id if res else "None")
            return res
        except Exception as e:
            _logger.warning("Contact search failed: %s", e)
            return self.env["res.partner"]

    # --------------------------
    # Creation & Updates
    # --------------------------

    @retry_on_transient_error(
        max_retries=3, initial_delay=0.1, catch_integrity_error=True
    )
    def _create_new_partner(self, provider_data, contact_metadata=None):
        user_id = provider_data.get("user_id")

        self.env.cr.flush()
        existing_partner = self._find_by_provider_user_id(user_id)
        if existing_partner:
            return existing_partner

        # Usar cursor separado para commit inmediato
        with self.env.registry.cursor() as new_cr:
            new_env = self.env(cr=new_cr)
            partner_data = self._prepare_partner_data(provider_data, contact_metadata)
            partner = new_env["res.partner"].sudo().create(partner_data)
            new_cr.commit()
            partner_id = partner.id

        # Refrescar en el entorno actual
        partner = self.env["res.partner"].browse(partner_id)
        _logger.info(
            "Created partner %s from provider %s",
            partner.id,
            provider_data.get("provider_name"),
        )
        return partner

    def _prepare_partner_data(self, provider_data, contact_metadata=None):
        partner_data = {
            "provider_user_id": provider_data.get("user_id"),
            "provider_name": provider_data.get("provider_name"),
            "is_provider_chat_user": True,
        }

        if contact_metadata:
            return self._add_contact_metadata(
                partner_data, contact_metadata, provider_data
            )
        else:
            partner_data["name"] = self._build_fallback_name(provider_data)
            return partner_data

    def _add_contact_metadata(self, partner_data, metadata, provider_data):
        partner_data["name"] = self._build_full_name(metadata) or provider_data.get(
            "user_name"
        )

        if metadata.phone_number:
            normalized = ContactFormatter.normalize_phone_number(metadata.phone_number)
            if normalized:
                partner_data["mobile"] = normalized

        if metadata.email:
            partner_data["email"] = metadata.email

        if metadata.profile_picture_url:
            partner_data["image_1920"] = metadata.profile_picture_url

        return partner_data

    def _update_partner_contact_info(self, partner, metadata):
        updates = {}
        partner = partner.sudo()

        if metadata.phone_number and not partner.mobile:
            normalized = ContactFormatter.normalize_phone_number(metadata.phone_number)
            if normalized:
                updates["mobile"] = normalized

        if metadata.email and not partner.email:
            updates["email"] = metadata.email

        full_name = self._build_full_name(metadata)
        if full_name and full_name != partner.name:
            updates["name"] = full_name

        if metadata.profile_picture_url and not partner.image_1920:
            updates["image_1920"] = metadata.profile_picture_url

        if updates:
            partner.write(updates)
            _logger.info("Partner %s updated with: %s", partner.id, updates.keys())
            return {"status": "update", "message": "Update applied"}
        return {"status": "noop", "message": "No updates needed"}

    def _link_provider_fields(self, partner, provider_data):
        updates = {}
        partner = partner.sudo()
        if not partner.provider_user_id and provider_data.get("user_id"):
            updates["provider_user_id"] = provider_data["user_id"]
        if not partner.provider_name and provider_data.get("provider_name"):
            updates["provider_name"] = provider_data["provider_name"]
        if not partner.is_provider_chat_user:
            updates["is_provider_chat_user"] = True

        if updates:
            partner.write(updates)
            _logger.info("Linked partner %s to provider: %s", partner.id, updates)
            return {"status": "update", "message": "Linked"}
        return {"status": "noop", "message": "Already linked"}

    def _build_full_name(self, metadata):
        return f"{metadata.first_name or ''} {metadata.last_name or ''}".strip() or None

    def _build_fallback_name(self, provider_data):
        return provider_data.get("user_name") or _(
            "Unknown User %s"
        ) % provider_data.get("provider_name", "")

    def _validate_provider_data(self, data):
        if not data or not data.get("user_id"):
            raise ValidationError(_("Missing provider user ID"))

    def init(self):
        super().init()
        self._create_indexes()

    def _create_indexes(self):
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_partner_provider ON res_partner(provider_name, is_provider_chat_user)
            WHERE is_provider_chat_user = true
        """
        )
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_partner_email ON res_partner(email)
            WHERE email IS NOT NULL
        """
        )
        self.env.cr.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_partner_phone_mobile ON res_partner(phone, mobile)
            WHERE phone IS NOT NULL OR mobile IS NOT NULL
        """
        )
