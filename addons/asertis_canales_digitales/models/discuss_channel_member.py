from odoo import models, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class DiscussChannelMember(models.Model):
    _inherit = "discuss.channel.member"

    @api.model_create_multi
    def create(self, vals_list):
        try:
            return super().create(vals_list)
        except UserError as e:
            if "No puede agregar más miembros a este chat" in str(e):
                if self._is_external_chat_from_error(vals_list):
                    _logger.warning("Bypassing 2-member limit for external chat")
                    return self._create_without_validation(vals_list)
            raise  # otros errores se relanzan

    def _is_external_chat_from_error(self, vals_list):
        try:
            for vals in vals_list:
                if isinstance(vals, dict) and "channel_id" in vals:
                    channel = self.env["discuss.channel"].browse(vals["channel_id"])
                    if channel.exists() and (
                        channel.provider_name or channel.external_channel_id
                    ):
                        return True
            return False
        except Exception as e:
            _logger.error(f"Error checking external chat: {e}")
            return False

    def _create_without_validation(self, vals_list):
        try:
            return self.env["mail.channel.member"].create(vals_list)
        except Exception as e:
            _logger.error(
                f"Fallback to SQL due to error in mail.channel.member.create: {e}"
            )
            return self._create_direct_sql(vals_list)

    def add_members_directly(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        created_ids = []
        Bus = self.env["bus.bus"]

        for vals in vals_list:
            try:
                channel_id = vals.get("channel_id")
                partner_id = vals.get("partner_id")

                if channel_id and partner_id:
                    # Verificar si ya existe en discuss_channel_member
                    existing = self.search(
                        [
                            ("channel_id", "=", channel_id),
                            ("partner_id", "=", partner_id),
                        ]
                    )
                    if not existing:
                        # 1. Verificar si existe en mail_channel_member
                        self.env.cr.execute(
                            """
                            SELECT id FROM mail_channel_member
                            WHERE channel_id = %s AND partner_id = %s
                        """,
                            (channel_id, partner_id),
                        )
                        exists_mail = self.env.cr.fetchone()

                        if not exists_mail:
                            # 2. Insertar en mail_channel_member
                            self.env.cr.execute(
                                """
                                INSERT INTO mail_channel_member (
                                    channel_id, partner_id, create_date, write_date, create_uid, write_uid)
                                VALUES (%s, %s, NOW(), NOW(), %s, %s)
                            """,
                                (channel_id, partner_id, self.env.uid, self.env.uid),
                            )

                        # 3. Insertar en discuss_channel_member
                        self.env.cr.execute(
                            """
                            INSERT INTO discuss_channel_member (
                                channel_id, partner_id, create_date, write_date, create_uid, write_uid)
                            VALUES (%s, %s, NOW(), NOW(), %s, %s)
                            RETURNING id
                        """,
                            (channel_id, partner_id, self.env.uid, self.env.uid),
                        )

                        created_id = self.env.cr.fetchone()[0]
                        created_ids.append(created_id)

                        # 4. Notificar al partner vía bus
                        Bus.sendone(
                            (self._cr.dbname, "res.partner", partner_id),
                            {
                                "type": "discuss_channel_joined",
                                "channel_id": channel_id,
                                "partner_id": partner_id,
                            },
                        )
                    else:
                        created_ids.append(existing.id)

            except Exception as e:
                _logger.error(f"Error in direct SQL member creation: {e}")

        return self.browse(created_ids)

    def _create_direct_sql(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        created_ids = []
        for vals in vals_list:
            try:
                if "channel_id" in vals and "partner_id" in vals:
                    existing = self.search(
                        [
                            ("channel_id", "=", vals["channel_id"]),
                            ("partner_id", "=", vals["partner_id"]),
                        ]
                    )
                    if not existing:
                        self.env.cr.execute(
                            """
                            INSERT INTO discuss_channel_member (channel_id, partner_id, create_date, write_date, create_uid, write_uid)
                            VALUES (%s, %s, NOW(), NOW(), %s, %s)
                            RETURNING id
                        """,
                            (
                                vals["channel_id"],
                                vals["partner_id"],
                                self.env.uid,
                                self.env.uid,
                            ),
                        )
                        created_id = self.env.cr.fetchone()[0]
                        created_ids.append(created_id)
                    else:
                        created_ids.append(existing.id)
            except Exception as e:
                _logger.error(f"SQL error creating member: {e}")

        return self.browse(created_ids)
