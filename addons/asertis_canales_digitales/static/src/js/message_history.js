// static/src/js/message_history.js
/** @odoo-module **/

import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class MessageHistoryModal extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        this.state = useState({
            messages: [],
            loading: false
        });
    }

    async openMediaFile(mediaUrl, filename) {
        if (mediaUrl) {
            // Abrir archivo multimedia en nueva pestaña
            window.open(mediaUrl, '_blank');
        } else {
            this.notification.add("URL del archivo no disponible", {
                type: "warning"
            });
        }
    }

    async openLocation(latitude, longitude, locationName) {
        if (latitude && longitude) {
            // Abrir en Google Maps
            const mapsUrl = `https://www.google.com/maps?q=${latitude},${longitude}`;
            window.open(mapsUrl, '_blank');
        } else {
            this.notification.add("Coordenadas no disponibles", {
                type: "warning"
            });
        }
    }

    getMessageIcon(messageType) {
        const icons = {
            'text': 'fa-comment',
            'image': 'fa-image',
            'video': 'fa-video-camera',
            'audio': 'fa-volume-up',
            'file': 'fa-file-o',
            'location': 'fa-map-marker',
            'sticker': 'fa-smile-o'
        };
        return icons[messageType] || 'fa-comment';
    }
}

// Registrar el componente
registry.category("components").add("MessageHistoryModal", MessageHistoryModal);

// Funcionalidad adicional para el chat
export class MessageHistoryService {
    static serviceDependencies = ["orm", "notification"];

    constructor(...args) {
        this.setup(...args);
    }

    setup(env, { orm, notification }) {
        this.env = env;
        this.orm = orm;
        this.notification = notification;
    }

    async showMessageHistory(channelId) {
        try {
            // Crear registro transitorio
            const historyId = await this.orm.create("message.history", [{
                channel_id: channelId
            }]);

            // Ejecutar acción para mostrar modal
            return this.orm.call("message.history", "get_message_history", [historyId[0]]);
        } catch (error) {
            this.notification.add("Error al cargar historial de mensajes", {
                type: "danger"
            });
            console.error("Error loading message history:", error);
        }
    }
}

registry.category("services").add("messageHistory", MessageHistoryService);