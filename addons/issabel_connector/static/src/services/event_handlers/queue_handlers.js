/** @odoo-module **/

import { BaseEventHandler, DataMapper, DataValidator } from './base';

/**
 * ============================================================================
 * HANDLERS DE EVENTOS DE COLAS
 * ============================================================================
 */

/**
 * Handler: QueueParams
 * Responsabilidad: Actualizar estadísticas de cola
 */
export class QueueParamsHandler extends BaseEventHandler {
    process(eventData) {
        const queueData = DataMapper.toQueueData(eventData);
        
        if (!DataValidator.isValidQueue(queueData)) {
            console.warn('⚠️ Datos de cola inválidos:', eventData);
            return null;
        }

        const queue = this.findQueue(queueData.queue);
        
        if (queue) {
            // Actualizar cola existente
            Object.assign(queue, queueData);
            return { updated: true, queue };
        } else {
            // Agregar nueva cola
            this.state.queues.push(queueData);
            return { updated: false, queue: queueData };
        }
    }

    afterProcess(eventData, result) {
        console.log('📊 Estadísticas de cola actualizadas:', {
            queue: result.queue.queue,
            calls: result.queue.calls,
            completed: result.queue.completed,
            sla: result.queue.service_level
        });
    }
}

/**
 * Handler: QueueStatusComplete
 * Responsabilidad: Marcar fin de sincronización inicial
 */
export class QueueStatusCompleteHandler extends BaseEventHandler {
    process(eventData) {
        console.log('✅ Sincronización inicial completada');
        
        // Aquí puedes agregar lógica adicional si necesitas
        // Por ejemplo, actualizar un flag de "sincronizado"
        
        return {
            completed: true,
            timestamp: new Date().toISOString()
        };
    }

    afterProcess(eventData, result) {
        console.log('📋 Estado actual del sistema:', {
            queues: this.state.queues.length,
            agents: this.state.agents.length,
            calls: this.state.calls.length
        });
    }
}