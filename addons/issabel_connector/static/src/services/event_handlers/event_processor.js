/** @odoo-module **/

import { EventHandlerRegistry } from './base';

// Importar todos los handlers
import { 
    QueueCallerJoinHandler,
    QueueCallerLeaveHandler,
    QueueCallerAbandonHandler,
    HangupHandler,
    QueueEntryHandler
} from './call_handlers';

import {
    QueueMemberStatusHandler,
    QueueMemberPauseHandler,
    QueueMemberAddedHandler,
    QueueMemberRemovedHandler,
    AgentConnectHandler,
    AgentCompleteHandler,
    QueueMemberHandler
} from './agent_handlers';

import {
    QueueParamsHandler,
    QueueStatusCompleteHandler
} from './queue_handlers';

/**
 * ============================================================================
 * EVENT PROCESSOR - Orquestador de eventos (Patrón Facade + Chain of Responsibility)
 * ============================================================================
 * 
 * Responsabilidades:
 * 1. Registrar todos los handlers disponibles
 * 2. Rutear eventos al handler correcto
 * 3. Manejar eventos no reconocidos
 * 4. Logging centralizado
 */
export class EventProcessor {
    constructor(state) {
        this.state = state;
        this.registry = new EventHandlerRegistry();
        this._setupHandlers();
        this._stats = {
            processed: 0,
            errors: 0,
            unhandled: 0
        };
    }

    /**
     * Registra todos los handlers disponibles
     */
    _setupHandlers() {
        // ========== LLAMADAS ==========
        this.registry.register('QueueCallerJoin', QueueCallerJoinHandler);
        this.registry.register('QueueCallerLeave', QueueCallerLeaveHandler);
        this.registry.register('QueueCallerAbandon', QueueCallerAbandonHandler);
        this.registry.register('Hangup', HangupHandler);
        this.registry.register('QueueEntry', QueueEntryHandler);

        // ========== AGENTES ==========
        this.registry.register('QueueMemberStatus', QueueMemberStatusHandler);
        this.registry.register('QueueMemberPause', QueueMemberPauseHandler);
        this.registry.register('QueueMemberPaused', QueueMemberPauseHandler); // Alias
        this.registry.register('QueueMemberAdded', QueueMemberAddedHandler);
        this.registry.register('QueueMemberRemoved', QueueMemberRemovedHandler);
        this.registry.register('AgentConnect', AgentConnectHandler);
        this.registry.register('AgentComplete', AgentCompleteHandler);
        this.registry.register('QueueMember', QueueMemberHandler);

        // ========== COLAS ==========
        this.registry.register('QueueParams', QueueParamsHandler);
        this.registry.register('QueueStatusComplete', QueueStatusCompleteHandler);

        console.log('✅ Event Processor inicializado con', 
            this.registry.getRegisteredEvents().length, 
            'handlers'
        );
    }

    /**
     * Procesa un evento (método principal)
     */
    processEvent(payload) {
        const { type, data } = payload;

        if (!type) {
            console.warn('⚠️ Evento sin tipo:', payload);
            this._stats.errors++;
            return false;
        }

        console.log(`🔔 Procesando evento: ${type}`);

        try {
            const handler = this.registry.getHandler(type, this.state);

            if (handler) {
                const success = handler.handle(data);
                
                if (success) {
                    this._stats.processed++;
                    return true;
                } else {
                    console.warn(`⚠️ Handler ${type} retornó false`);
                    return false;
                }
            } else {
                this._handleUnknownEvent(type, data);
                return false;
            }
        } catch (error) {
            console.error(`❌ Error procesando ${type}:`, error);
            this._stats.errors++;
            return false;
        }
    }

    /**
     * Maneja eventos no reconocidos
     */
    _handleUnknownEvent(type, data) {
        console.log(`⚠️ Evento no manejado: ${type}`, data);
        this._stats.unhandled++;

        // Aquí puedes agregar lógica para eventos futuros
        // Por ejemplo, enviar a un logger externo
    }

    /**
     * Obtiene estadísticas de procesamiento
     */
    getStats() {
        return { ...this._stats };
    }

    /**
     * Resetea estadísticas
     */
    resetStats() {
        this._stats = {
            processed: 0,
            errors: 0,
            unhandled: 0
        };
    }

    /**
     * Lista eventos soportados
     */
    getSupportedEvents() {
        return this.registry.getRegisteredEvents();
    }
}