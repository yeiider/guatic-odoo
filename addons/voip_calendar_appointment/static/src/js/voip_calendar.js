/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

/**
 * Widget para integración VoIP-Calendar
 */
class VoipCalendarWidget extends Component {
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    /**
     * Método para agendar cita rápida desde JavaScript
     */
    async quickScheduleAppointment(partnerId = null, phoneNumber = null) {
        try {
            const context = {
                default_user_id: this.env.services.user.userId,
                default_name: 'Cita telefónica',
            };

            if (partnerId) {
                const partner = await this.orm.read("res.partner", [partnerId], ["name"]);
                context.default_partner_ids = [[6, 0, [partnerId]]];
                context.default_name = `Cita con ${partner[0].name}`;
            }

            if (phoneNumber) {
                context.default_description = `Teléfono: ${phoneNumber}`;
            }

            return this.actionService.doAction({
                type: 'ir.actions.act_window',
                name: 'Agendar Cita',
                res_model: 'calendar.event',
                view_mode: 'form',
                target: 'new',
                context: context,
            });

        } catch (error) {
            this.notification.add(
                "Error al agendar cita: " + error.message,
                { type: "danger" }
            );
        }
    }
}

registry.category("public_components").add("voip_calendar_widget", VoipCalendarWidget);