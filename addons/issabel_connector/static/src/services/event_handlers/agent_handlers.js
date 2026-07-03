/** @odoo-module **/

import { BaseEventHandler, DataMapper, DataValidator } from "./base";

/**
 * ============================================================================
 * HANDLERS DE EVENTOS DE AGENTES
 * ============================================================================
 */

/**
 * Handler: QueueMemberStatus
 * Responsabilidad: Actualizar estado de agente existente
 */
export class QueueMemberStatusHandler extends BaseEventHandler {
  process(eventData) {
    const agentLocation = eventData.agent || eventData.interface;

    if (!agentLocation) {
      return null;
    }

    const agentIndex = this.findIndexedAgent(agentLocation);

    if (agentIndex !== -1) {
      const agent = this.state.agents[agentIndex];
      this.state.agents[agentIndex].status = eventData.status || agent.status;
      this.state.agents[agentIndex].status_code = eventData.status;
      this.state.agents[agentIndex].paused = eventData.paused;
      this.state.agents[agentIndex].in_call = eventData.in_call;
      this.state.agents[agentIndex].pause_reason = eventData.reason || "";

      return { updated: true, agent };
    }

    return null;
  }

  afterProcess(eventData, result) {
    console.log("👤 Estado de agente actualizado:", {
      name: result.agent.name,
      status: result.agent.status_code,
      paused: result.agent.paused,
    });
  }
}

/**
 * Handler: QueueMemberPause
 * Responsabilidad: Actualizar estado de pausa de agente
 */
export class QueueMemberPauseHandler extends BaseEventHandler {
  process(eventData) {
    console.log("Procesando QueueMemberPause con data:", eventData);
    const agentLocation = eventData.location || eventData.interface;

    if (!agentLocation) {
      return null;
    }

    const agentIndex = this.findIndexedAgent(agentLocation);

    if (agentIndex !== -1) {
      const paused = eventData.paused;
      this.state.agents[agentIndex].paused = paused;
      this.state.agents[agentIndex].status_code = eventData.status;
      this.state.agents[agentIndex].status = paused
        ? eventData.reason
        : "Disponible"; // 5=Unavailable, 1=Available
      this.state.agents[agentIndex].pause_reason = eventData.reason || "";
      return {
        updated: true,
        agent: this.state.agents[agentIndex],
        paused: paused,
      };
    }

    return null;
  }

  afterProcess(eventData, result) {
    const action = result.paused ? "pausado" : "despausado";
    console.log(`⏸️ Agente ${action}:`, result.agent.name);
  }
}

/**
 * Handler: QueueMemberAdded
 * Responsabilidad: Agregar nuevo agente a la cola
 */
export class QueueMemberAddedHandler extends BaseEventHandler {
  process(eventData) {
    const agentData = DataMapper.toAgentData(eventData);

    if (!DataValidator.isValidAgent(agentData)) {
      console.warn("⚠️ Datos de agente inválidos:", eventData);
      return null;
    }

    // Evitar duplicados
    const exists = this.state.agents.find(
      (a) => a.agent === agentData.agent && a.queue === agentData.queue
    );

    if (exists) {
      console.log("ℹ️ Agente ya existe:", agentData.agent);
      return null;
    }

    this.state.agents.push(agentData);
    return agentData;
  }

  afterProcess(eventData, result) {
    console.log("👤 Nuevo agente agregado:", {
      name: result.name,
      queue: result.queue,
    });
  }
}

/**
 * Handler: QueueMemberRemoved
 * Responsabilidad: Remover agente de la cola
 */
export class QueueMemberRemovedHandler extends BaseEventHandler {
  process(eventData) {
    const agentLocation = eventData.Location || eventData.Interface;
    const queue = eventData.Queue;

    if (!agentLocation || !queue) {
      return null;
    }

    const initialCount = this.state.agents.length;

    this.removeAgent(agentLocation, queue);

    const removed = initialCount > this.state.agents.length;

    return removed ? { agent: agentLocation, queue, removed: true } : null;
  }

  afterProcess(eventData, result) {
    console.log("👤 Agente removido:", {
      agent: result.agent,
      queue: result.queue,
    });
  }
}

/**
 * Handler: AgentConnect
 * Responsabilidad: Marcar agente como "en llamada"
 */
export class AgentConnectHandler extends BaseEventHandler {
  process(eventData) {
    const agentInterface = eventData.Interface || eventData.Member;

    if (!agentInterface) {
      return null;
    }

    const agent = this.findAgent(agentInterface);

    if (agent) {
      agent.in_call = true;
      agent.status_code = 2; // InUse

      return {
        agent,
        connected: true,
        caller: eventData.CallerIDNum,
      };
    }

    return null;
  }

  afterProcess(eventData, result) {
    console.log("📞 Agente conectado:", {
      agent: result.agent.name,
      caller: result.caller,
    });
  }
}

/**
 * Handler: AgentComplete
 * Responsabilidad: Marcar agente como disponible después de llamada
 */
export class AgentCompleteHandler extends BaseEventHandler {
  process(eventData) {
    const agentInterface = eventData.Interface || eventData.Member;

    if (!agentInterface) {
      return null;
    }

    const agent = this.findAgent(agentInterface);

    if (agent) {
      agent.in_call = false;
      agent.calls_taken++;
      agent.status_code = 1; // Available

      return {
        agent,
        completed: true,
        talkTime: DataMapper.parseInt(eventData.TalkTime),
      };
    }

    return null;
  }

  afterProcess(eventData, result) {
    console.log("✅ Llamada completada:", {
      agent: result.agent.name,
      talkTime: result.talkTime,
      totalCalls: result.agent.calls_taken,
    });
  }
}

/**
 * Handler: QueueMember (Snapshot)
 * Responsabilidad: Actualizar/agregar agente desde snapshot
 */
export class QueueMemberHandler extends BaseEventHandler {
  process(eventData) {
    const agentData = DataMapper.toAgentData(eventData);

    if (!DataValidator.isValidAgent(agentData)) {
      return null;
    }

    const existingAgent = this.state.agents.find(
      (a) => a.agent === agentData.agent && a.queue === agentData.queue
    );

    if (existingAgent) {
      Object.assign(existingAgent, agentData);
      return { updated: true, agent: existingAgent };
    } else {
      this.state.agents.push(agentData);
      return { updated: false, agent: agentData };
    }
  }
}
