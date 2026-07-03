/** @odoo-module **/

/**
 * ============================================================================
 * FRONTEND EVENT HANDLERS - Arquitectura Limpia
 * ============================================================================
 * 
 * Patrón Strategy + Registry (igual que el backend)
 * Cada handler es responsable de UN SOLO tipo de evento
 */

/**
 * Clase base abstracta para handlers de eventos (Patrón Template Method)
 */
export class BaseEventHandler {
    constructor(state) {
        this.state = state;
    }

    /**
     * Template Method: flujo común de procesamiento
     */
    handle(eventData) {
        try {
            if (!this.canHandle(eventData)) {
                return false;
            }

            const processed = this.process(eventData);
            
            if (processed) {
                this.afterProcess(eventData, processed);
            }

            return true;
        } catch (error) {
            console.error(`❌ Error en ${this.constructor.name}:`, error);
            return false;
        }
    }

    /**
     * Valida si puede manejar el evento
     */
    canHandle(eventData) {
        return true;
    }

    /**
     * Procesa el evento y actualiza el estado
     * @abstract - Debe ser implementado por clases hijas
     */
    process(eventData) {
        throw new Error('Método process() debe ser implementado');
    }

    /**
     * Hook ejecutado después del procesamiento
     */
    afterProcess(eventData, result) {
        console.log(`✅ ${this.constructor.name} procesado:`, result);
    }

    /**
     * Helpers para actualización de estado
     */
    findAgent(identifier) {
        return this.state.agents.find(
            a => a.agent === identifier || a.agent.includes(identifier)
        );
    }
    findIndexedAgent(identifier) {
        return this.state.agents.findIndex(
            a => a.agent === identifier || a.agent.includes(identifier)
        );
    }

    findCall(uniqueId) {
        return this.state.calls.find(c => c.unique_id === uniqueId);
    }

    findQueue(queueName) {
        return this.state.queues.find(q => q.queue === queueName);
    }

    removeCall(uniqueId) {
        this.state.calls = this.state.calls.filter(
            c => c.unique_id !== uniqueId
        );
    }

    removeAgent(agentId, queueName) {
        this.state.agents = this.state.agents.filter(
            a => !(a.agent === agentId && a.queue === queueName)
        );
    }
}

/**
 * ============================================================================
 * EVENT HANDLER REGISTRY - Patrón Registry + Factory
 * ============================================================================
 */
export class EventHandlerRegistry {
    constructor() {
        this._handlers = new Map();
    }

    /**
     * Registra un handler para un tipo de evento
     */
    register(eventType, HandlerClass) {
        this._handlers.set(eventType, HandlerClass);
       
    }

    /**
     * Obtiene el handler apropiado para un evento
     */
    getHandler(eventType, state) {
        const HandlerClass = this._handlers.get(eventType);
        return HandlerClass ? new HandlerClass(state) : null;
    }

    /**
     * Lista todos los eventos registrados
     */
    getRegisteredEvents() {
        return Array.from(this._handlers.keys());
    }
}

/**
 * ============================================================================
 * DATA MAPPERS - Patrón Mapper
 * ============================================================================
 */
export class DataMapper {
    /**
     * Convierte datos crudos a estructura de llamada
     */
    static toCallData(rawData) {
        return {
            unique_id: rawData.Uniqueid || '',
            caller_id_num: rawData.CallerIDNum || '',
            caller_id_name: rawData.CallerIDName || '',
            queue: rawData.Queue || '',
            position: parseInt(rawData.Position) || 0,
            wait_time: parseInt(rawData.Wait) || 0,
            channel: rawData.Channel || '',
        };
    }

    /**
     * Convierte datos crudos a estructura de agente
     */
    static toAgentData(rawData) {
        return {
            agent: rawData.Location || rawData.Interface || '',
            name: rawData.MemberName || rawData.Name || 'Unknown',
            queue: rawData.Queue || '',
            status: rawData.Status || '',
            status_code: parseInt(rawData.Status) || 0,
            paused: rawData.Paused === '1' || rawData.Paused === 1,
            in_call: rawData.InCall === '1' || rawData.InCall === 1,
            penalty: parseInt(rawData.Penalty) || 0,
            calls_taken: parseInt(rawData.CallsTaken) || 0,
        };
    }

    /**
     * Convierte datos crudos a estructura de cola
     */
    static toQueueData(rawData) {
        return {
            queue: rawData.Queue || '',
            calls: parseInt(rawData.Calls) || 0,
            completed: parseInt(rawData.Completed) || 0,
            abandoned: parseInt(rawData.Abandoned) || 0,
            holdtime: parseInt(rawData.Holdtime) || 0,
            talk_time: parseInt(rawData.TalkTime) || 0,
            service_level: parseFloat(rawData.ServicelevelPerf) || 0,
            strategy: rawData.Strategy || '',
        };
    }

    /**
     * Parsea booleano de forma segura
     */
    static parseBoolean(value) {
        return value === '1' || value === 1 || value === true;
    }

    /**
     * Parsea entero de forma segura
     */
    static parseInt(value, defaultValue = 0) {
        const parsed = parseInt(value);
        return isNaN(parsed) ? defaultValue : parsed;
    }
}

/**
 * ============================================================================
 * VALIDATORS - Validación de datos
 * ============================================================================
 */
export class DataValidator {
    /**
     * Valida estructura de evento básico
     */
    static isValidEvent(eventData) {
        return eventData && typeof eventData === 'object';
    }

    /**
     * Valida datos de llamada
     */
    static isValidCall(callData) {
        return callData && callData.unique_id && callData.queue;
    }

    /**
     * Valida datos de agente
     */
    static isValidAgent(agentData) {
        return agentData && agentData.agent && agentData.queue;
    }

    /**
     * Valida datos de cola
     */
    static isValidQueue(queueData) {
        return queueData && queueData.queue;
    }
}