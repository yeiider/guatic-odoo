/** @odoo-module **/

import { BaseEventHandler, DataMapper, DataValidator } from "./base";

/**
 * ============================================================================
 * HANDLERS DE EVENTOS DE LLAMADAS
 * ============================================================================
 * Cada handler se especializa en UN tipo de evento
 */

/**
 * Handler: QueueCallerJoin
 * Responsabilidad: Agregar nueva llamada a la cola
 */
export class QueueCallerJoinHandler extends BaseEventHandler {
  process(eventData) {
    const callData ={...eventData};
    if (!DataValidator.isValidCall(callData)) {
      console.warn("⚠️ Datos de llamada inválidos:", eventData);
      return null;
    }

    // Evitar duplicados
    if (this.findCall(callData.unique_id)) {
      console.log("ℹ️ Llamada ya existe:", callData.unique_id);
      return null;
    }

    this.state.calls.push(callData);
    return callData;
  }

  afterProcess(eventData, result) {
    console.log("📞 Nueva llamada agregada:", {
      caller: result.caller_id_num,
      queue: result.queue,
      position: result.position,
    });
  }
}

/**
 * Handler: QueueCallerLeave
 * Responsabilidad: Remover llamada cuando es atendida
 */
export class QueueCallerLeaveHandler extends BaseEventHandler {
  process(eventData) {
    const uniqueId = eventData.Uniqueid;

    if (!uniqueId) {
      return null;
    }

    const call = this.findCall(uniqueId);

    if (call) {
      this.removeCall(uniqueId);
      return { uniqueId, removed: true };
    }

    return null;
  }

  afterProcess(eventData, result) {
    console.log("📴 Llamada atendida/removida:", result.uniqueId);
  }
}

/**
 * Handler: QueueCallerAbandon
 * Responsabilidad: Remover llamada cuando cliente cuelga
 */
export class QueueCallerAbandonHandler extends BaseEventHandler {
  process(eventData) {
    const uniqueId = eventData.Uniqueid;
    const holdTime = DataMapper.parseInt(eventData.HoldTime);

    if (!uniqueId) {
      return null;
    }

    const call = this.findCall(uniqueId);

    if (call) {
      this.removeCall(uniqueId);
      return {
        uniqueId,
        abandoned: true,
        holdTime,
      };
    }

    return null;
  }

  afterProcess(eventData, result) {
    console.log("🔴 Llamada abandonada:", {
      id: result.uniqueId,
      waitTime: result.holdTime,
    });
  }
}

/**
 * Handler: Hangup
 * Responsabilidad: Limpiar llamadas por canal o unique_id
 */
export class HangupHandler extends BaseEventHandler {
  process(eventData) {
    const channel = eventData.Channel;
    const uniqueId = eventData.Uniqueid;

    const initialCount = this.state.calls.length;

    this.state.calls = this.state.calls.filter(
      (c) => c.channel !== channel && c.unique_id !== uniqueId
    );

    const removed = initialCount - this.state.calls.length;

    return removed > 0 ? { channel, uniqueId, removed } : null;
  }

  afterProcess(eventData, result) {
    console.log("📴 Hangup procesado:", {
      channel: result.channel,
      removed: result.removed,
    });
  }
}

/**
 * Handler: QueueEntry (Snapshot de llamadas)
 * Responsabilidad: Actualizar lista completa de llamadas
 */
export class QueueEntryHandler extends BaseEventHandler {
  process(eventData) {
    const callData = DataMapper.toCallData(eventData);

    if (!DataValidator.isValidCall(callData)) {
      return null;
    }

    const existingCall = this.findCall(callData.unique_id);

    if (existingCall) {
      // Actualizar llamada existente
      Object.assign(existingCall, callData);
      return { updated: true, call: existingCall };
    } else {
      // Agregar nueva llamada
      this.state.calls.push(callData);
      return { updated: false, call: callData };
    }
  }
}
