/** @odoo-module **/

import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { EventProcessor } from "../../services/event_handlers/event_processor";

/**
 * ============================================================================
 * ISSABEL DASHBOARD - Componente Principal Refactorizado
 * ============================================================================
 */
export class IssabelDashboard extends Component {
  static template = "issabel_dashboard.Template";

  setup() {
    // ========== SERVICIOS ==========
    this.orm = useService("orm");
    this.busService = useService("bus_service");

    // ========== ESTADO REACTIVO ==========
    this.state = useState({
      queues: [],
      agents: [],
      calls: [],
      isLoading: true,
      lastUpdate: null,
      connectionStatus: "connecting",
    });

    // ========== PROCESADOR DE EVENTOS ==========
    this.eventProcessor = new EventProcessor(this.state);

    // ========== METADATA ==========
    this._userId = undefined;
    this._busListener = null;

    // ========== HOOKS DE CICLO DE VIDA ==========
    onWillStart(async () => {
      await this._initialize();
    });

    onWillUnmount(() => {
      this._cleanup();
    });
  }

  // ========================================================================
  // INICIALIZACIÓN
  // ========================================================================

  /**
   * Inicializa el componente
   */
  async _initialize() {
    try {
      console.log("🚀 Inicializando Issabel Dashboard...");

      // 1. Cargar datos iniciales
      await this._loadInitialData();

      // 2. Configurar listeners del bus
      this._setupBusListeners();

      // 3. Marcar como conectado
      this.state.connectionStatus = "connected";

      console.log("✅ Dashboard inicializado correctamente");
      console.log("📊 Estado inicial:", {
        queues: this.state.queues.length,
        agents: this.state.agents.length,
        calls: this.state.calls.length,
      });
    } catch (error) {
      console.error("❌ Error inicializando dashboard:", error);
      this.state.connectionStatus = "disconnected";
    } finally {
      // ✅ Quitar loader DESPUÉS de todo
      this.state.isLoading = false;
    }
  }

  /**
   * Carga datos iniciales desde el backend
   */
  async _loadInitialData() {
    try {
      const data = await this.orm.call(
        "issabel.dashboard",
        "get_dashboard_data",
        []
      );

      // Actualizar estado con datos iniciales
      this.state.queues = data.queues || [];
      this.state.agents = data.agents || [];
      this.state.calls = data.calls || [];
      this._userId = data.user_id;
      this.state.lastUpdate = data.last_update || new Date().toISOString();

    } catch (error) {
      console.error("❌ Error cargando datos iniciales:", error);
      // Mantener arrays vacíos por defecto
      this.state.queues = [];
      this.state.agents = [];
      this.state.calls = [];
    }
  }

  // ========================================================================
  // BUS DE EVENTOS
  // ========================================================================

  /**
   * Configura listeners del bus de comunicación
   */
  _setupBusListeners() {
    this._busListener = (payload) => {
      this._onBusNotification(payload);
    };

    this.busService.subscribe("issabel_ami_event", this._busListener);
    this.busService.start();

    console.log("🔌 Bus listener configurado");
  }

  /**
   * Handler de notificaciones del bus
   */
  _onBusNotification(payload) {
    // Delegar procesamiento al EventProcessor
    const success = this.eventProcessor.processEvent(payload);

    // Actualizar timestamp de última actualización
    if (success) {
      this.state.lastUpdate = new Date().toISOString();
    }
  }

  /**
   * Limpia listeners del bus
   */
  _cleanup() {
    if (this._busListener) {
      this.busService.unsubscribe("issabel_ami_event", this._busListener);
      this.busService.deleteChannel("issabel_dashboard");
      console.log("🔌 Bus listener desconectado");
    }
  }

  // ========================================================================
  // ACCIONES DEL USUARIO
  // ========================================================================

  /**
   * Pausa/despausa un agente
   */
  async pauseAgent(agent, paused, reason = "") {
    try {
      await this.orm.call("issabel.dashboard", "pause_agent", [
        agent.agent,
        agent.queue,
        paused,
        reason,
      ]);
    } catch (error) {
      console.error("❌ Error pausando agente:", error);
    }
  }

  /**
   * Refresca datos manualmente
   */
  async refreshData() {
    if (this.state.isLoading) return; // Prevenir múltiples clicks
    
    console.log("🔄 Refrescando datos...");
    this.state.isLoading = true;
    
    try {
      await this._loadInitialData();
      console.log("✅ Datos refrescados correctamente");
    } catch (error) {
      console.error("❌ Error refrescando datos:", error);
    } finally {
      this.state.isLoading = false;
    }
  }

  /**
   * Obtiene estadísticas de procesamiento
   */
  getProcessingStats() {
    return this.eventProcessor.getStats();
  }

  /**
   * Obtiene clase CSS basada en el código de estado del agente
   */
  getStatusClass(statusCode) {
    const classes = {
      1: 'status-success',
      2: 'status-info',
      3: 'status-warning'
    };
    return classes[statusCode] || 'status-error';
  }

  /**
   * Formatea la fecha de última actualización
   */
  formatLastUpdate(isoDate) {
    if (!isoDate) return '-';
    
    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    
    if (diffSecs < 10) return 'Ahora mismo';
    if (diffSecs < 60) return `Hace ${diffSecs} segundos`;
    if (diffSecs < 3600) return `Hace ${Math.floor(diffSecs / 60)} minutos`;
    
    return date.toLocaleString('es-CO', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }
}

// Registrar componente en el registro de acciones de Odoo
registry.category("actions").add("issabel_dashboard", IssabelDashboard);
