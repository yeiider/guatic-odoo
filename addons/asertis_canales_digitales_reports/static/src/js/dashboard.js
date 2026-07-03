/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

// Variables globales para los gráficos
let sessionsChart, messagesChart, waitingTimeChart;

class DashboardManager {
  constructor() {
    this.initialized = false;
    this.loadData = false;
    this.syncDate = new Date();

    this.init();
  }

  async init() {
    // Wait for DOM to be ready
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => this.setup());
    } else {
      this.setup();
    }
  }

  setup() {
    // Wait a bit more to ensure jQuery and other dependencies are loaded
    setTimeout(() => {
      this.initializeDashboard();
      this.loadConfigurations();
      this.setupEventListeners();
      this.setupAutoRefresh();
    }, 100);
  }

  setupEventListeners() {
    // Use vanilla JS for event listeners since jQuery might not be available
    const syncBtn = document.getElementById("sync_btn");
    const realtimeBtn = document.getElementById("realtime_btn");
    const periodSelector = document.getElementById("period_selector");
    const configSelector = document.getElementById("config_selector");


    if (syncBtn) {
      syncBtn.addEventListener("click", () => this.loadRealtimeData());
    }

    if (realtimeBtn) {
      realtimeBtn.addEventListener("click", () => this.loadRealtimeData(true));
    }
    if (periodSelector) {
      periodSelector.addEventListener("change", () => this.loadRealtimeData());
    }
    if (configSelector) {
      configSelector.addEventListener("change", () => this.loadRealtimeData());
    }

  }

  initializeDashboard() {
    // Inicializar Chart.js
    if (typeof Chart !== "undefined") {
      Chart.defaults.font.family =
        "'Helvetica Neue', 'Helvetica', 'Arial', sans-serif";
      Chart.defaults.font.size = 12;
    }

    this.initialized = true;
  }

  async loadConfigurations() {
    try {
      const configs = await rpc("/web/dataset/call_kw", {
        model: "api.config",
        method: "search_read",
        args: [[], ["id", "name"]],
        kwargs: {},
      });

      const selector = document.getElementById("config_selector");
      if (selector) {
        selector.innerHTML =
          '<option value="">Todas las configuraciones</option>';
        configs.forEach(function (config) {
          const option = document.createElement("option");
          option.value = config.id;
          option.textContent = config.name;
          selector.appendChild(option);
        });

        // Si hay al menos una configuración, selecciona la primera real
        if (configs.length > 0) {
          selector.value = configs[0].id;
        }

        await this.loadRealtimeData();
      }
    } catch (error) {
      console.error("Error loading configurations:", error);
    }
  }

  async loadDashboardData() {
    try {
      this.loadData = true;
      this.toggleLoader(this.loadData);

      const configSelector = document.getElementById("config_selector");
      const periodSelector = document.getElementById("period_selector");

      const configId = configSelector?.value || "0";
      const periodType = periodSelector?.value || "last_month";

      const response = await rpc("/api_reporting/get_data", {
        config_id: parseInt(configId),
        period_type: periodType,
        force_sync: false,
      });

      if (response.success) {
        console.log("Datos cargados:", response.data);
        this.updateDashboard(response.data);
        this.syncDate = new Date();
        this.updateSyncStatus(this.syncDate);
      } else {
        this.showError("Error cargando datos: " + response.error);
      }
    } catch (error) {
      this.showError("Error de conexión: " + error.message);
    } finally {
      this.loadData = false;
      this.toggleLoader(this.loadData);
    }
  }

  async syncData() {
    try {
      this.loadData = true;

      const configSelector = document.getElementById("config_selector");
      const configId = configSelector?.value || null;

      const response = await rpc("/api_reporting/sync_now", {
        config_id: configId,
      });

      if (response.success) {
        this.showSuccess("Sincronización completada");
        await this.loadDashboardData();
      } else {
        this.showError("Error en sincronización: " + response.error);
      }
    } catch (error) {
      this.showError("Error de conexión: " + error.message);
    } finally {
      this.loadData = false;
      this.toggleLoader(this.loadData);
      this.hideLoading();
    }
  }

  async loadRealtimeData(isRealTime = false) {
    try {
      this.loadData = true;
      let isLoad = false;
      this.toggleLoader(this.loadData);

      const configSelector = document.getElementById("config_selector");
      const periodSelector = document.getElementById("period_selector");

      const configId = configSelector?.value || "0";
      let periodType = periodSelector?.value || "last_month";

      if (!configId) {
        this.showError(
          "Selecciona una configuración para datos en tiempo real"
        );

        return false;
      }
      if (isRealTime) {
        periodType = "today";
      }

      this.showLoading();

      const response = await rpc("/api_reporting/get_realtime_data", {
        config_id: parseInt(configId),
        period_type: periodType,
      });
      let realTimeText =isRealTime?" en tiempo real":"";
      

      if (response.success) {
        this.updateDashboard(response.data, true);
        this.syncDate = new Date();
        this.updateSyncStatus(this.syncDate);

        this.showSuccess( `Datos ${realTimeText} cargados`);
        return false;
      } else {
        this.showError(
          "Error cargando datos: " + response.error
        );
        return false;
      }
    } catch (error) {
      this.showError("Error de conexión: " + error.message);
      return false;
    } finally {
      this.loadData = false;
      this.toggleLoader(this.loadData);
      this.hideLoading();
      return true;
    }
  }

  updateDashboard(data, isRealtime = false) {
    // Actualizar tarjetas de resumen
    this.updateElement(
      "total_sessions",
      data.summary.total_sessions.toLocaleString()
    );
    this.updateElement(
      "total_messages",
      data.summary.total_messages.toLocaleString()
    );
    this.updateElement(
      "total_contacts",
      data.summary.total_contacts.toLocaleString()
    );
    this.updateElement(
      "avg_waiting_time",
      this.formatTime(data.summary.avg_waiting_time || 0)
    );

    // Actualizar displays en headers de gráficos
    this.updateElement(
      "sessions_total_display",
      data.summary.total_sessions.toLocaleString()
    );
    this.updateElement(
      "messages_total_display",
      data.summary.total_messages.toLocaleString()
    );
    this.updateElement(
      "waiting_time_display",
      this.formatTime(data.summary.avg_waiting_time || 0)
    );

    // Actualizar gráficos y detalles
    if (isRealtime && data.chart_data) {
      this.updateChartsRealtime(data.chart_data);
      this.updateDetails(data.bot_details || []);
      this.updateTable(data.bot_details || []);
    } else if (data.charts) {
      this.updateCharts(data.charts);
      this.updateDetails(data.bot_details || []);
      this.updateTable(data.bot_details || []);
    }
  }

  updateElement(id, content) {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = content;
    }
  }

  updateCharts(charts) {
    // Gráfico de sesiones por categoría
    this.updateSessionsChart(charts.sessions_by_platform);

    // Gráfico de mensajes entrantes vs salientes
    this.updateMessagesChart(charts.messages_comparison);

    // Gráfico de tiempos de espera
    this.updateWaitingTimeChart(charts.waiting_times);
  }

  updateChartsRealtime(chartData) {
    // Adaptar datos en tiempo real para los gráficos
    const sessionsData = [
      {
        name: "Panel",
        value: chartData.reduce(
          (sum, item) => sum + item.sessions_with_panel,
          0
        ),
      },
      {
        name: "Bot",
        value: chartData.reduce(
          (sum, item) => sum + (item.total_sessions - item.sessions_with_panel),
          0
        ),
      },
      {
        name: "Abandonadas",
        value: chartData.reduce(
          (sum, item) => sum + item.abandoned_sessions,
          0
        ),
      },
    ];

    const messagesData = [
      {
        name: "Entrantes",
        value: chartData.reduce((sum, item) => sum + item.incoming_messages, 0),
        type: "incoming",
      },
      {
        name: "Salientes",
        value: chartData.reduce((sum, item) => sum + item.outgoing_messages, 0),
        type: "outgoing",
      },
    ];

    const waitingData = chartData.map((item) => ({
      name: item.bot_name,
      avg_waiting_time: item.avg_waiting_time,
    }));

    this.updateSessionsChart(sessionsData);
    this.updateMessagesChart(messagesData);
    this.updateWaitingTimeChart(waitingData);
  }

  updateSessionsChart(data) {
    const canvas = document.getElementById("sessions_chart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (sessionsChart) {
      sessionsChart.destroy();
    }

    const colors = ["#4285f4", "#ff9800", "#f44336"]; // Azul, Naranja, Rojo

    sessionsChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: data.map((item) => item.name),
        datasets: [
          {
            data: data.map((item) => item.value),
            backgroundColor: colors.slice(0, data.length),
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((context.raw / total) * 100).toFixed(1);
                return (
                  context.label + ": " + context.raw + " (" + percentage + "%)"
                );
              },
            },
          },
        },
      },
    });
  }

  updateMessagesChart(data) {
    const canvas = document.getElementById("messages_chart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (messagesChart) {
      messagesChart.destroy();
    }

    messagesChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: data.map((item) => item.name),
        datasets: [
          {
            data: data.map((item) => item.value),
            backgroundColor: ["#4285f4", "#ea4335"], // Azul para entrantes, Rojo para salientes
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((context.raw / total) * 100).toFixed(1);
                return (
                  context.label + ": " + context.raw + " (" + percentage + "%)"
                );
              },
            },
          },
        },
      },
    });
  }

  updateWaitingTimeChart(data) {
    const canvas = document.getElementById("waiting_time_chart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (waitingTimeChart) {
      waitingTimeChart.destroy();
    }

    if (!data || !Array.isArray(data) || data.length === 0) return;

    // Filtrar datos válidos
    const validData = data.filter(
      (item) =>
        item &&
        typeof item.avg_waiting_time === "number" &&
        !isNaN(item.avg_waiting_time) &&
        item.name
    );

    if (validData.length === 0) return;

    const colors = this.generateColors(validData.length);

    waitingTimeChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: validData.map((item) => item.name),
        datasets: [
          {
            data: validData.map((item) =>
              Math.round(Math.max(0, item.avg_waiting_time) / 1000)
            ), // Convertir a segundos
            backgroundColor: colors,
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                return (
                  context.label + ": " + this.formatTime(context.raw * 1000)
                );
              },
            },
          },
        },
      },
    });
  }

  updateDetails(botDetails) {
    this.updateSessionsDetails(botDetails);
    this.updateMessagesDetails(botDetails);
    this.updateWaitingTimeDetails(botDetails);
  }

  updateSessionsDetails(botDetails) {
    const container = document.getElementById("sessions_details");
    if (!container) return;

    container.innerHTML = "";

    botDetails.forEach((bot) => {
      if (bot.sessions > 0) {
        const div = document.createElement("div");
        div.className = "mb-2";
        div.innerHTML = `
          <div class="d-flex align-items-center mb-1">
            <i class="fa fa-user-circle text-primary mr-2"></i>
            <strong>${bot.name}</strong>
          </div>
          <div class="small text-muted ml-4">
            Sesiones: ${bot.sessions}<br>
            Sesiones abandonadas: ${bot.sessions_abandoned}<br>
            Sesiones con panel: ${bot.sessions_with_panel}<br>
            Contactos únicos: ${bot.unique_contacts}
          </div>
        `;
        container.appendChild(div);
      }
    });
  }

  updateMessagesDetails(botDetails) {
    const container = document.getElementById("messages_details");
    if (!container) return;

    container.innerHTML = "";

    botDetails.forEach((bot) => {
      if (bot.incoming_messages > 0 || bot.outgoing_messages > 0) {
        const div = document.createElement("div");
        div.className = "mb-2";
        div.innerHTML = `
          <div class="d-flex align-items-center mb-1">
            <i class="fa fa-comment text-success mr-2"></i>
            <strong>${bot.name}</strong>
          </div>
          <div class="small text-muted ml-4">
            Mensajes entrantes: ${bot.incoming_messages}<br>
            Mensajes salientes: ${bot.outgoing_messages}
          </div>
        `;
        container.appendChild(div);
      }
    });
  }

  updateWaitingTimeDetails(botDetails) {
    const container = document.getElementById("waiting_time_details");
    if (!container) return;

    container.innerHTML = "";

    botDetails.forEach((bot) => {
      if (bot.avg_waiting_time > 0) {
        const div = document.createElement("div");
        div.className = "mb-2";
        div.innerHTML = `
          <div class="d-flex align-items-center mb-1">
            <i class="fa fa-clock-o text-warning mr-2"></i>
            <strong>${bot.name}</strong>
          </div>
          <div class="small text-muted ml-4">
            Tiempo de espera promedio: ${this.formatTime(
              bot.avg_waiting_time
            )}<br>
            Tiempo promedio de sesión: ${this.formatTime(
              bot.avg_session_length
            )}
          </div>
        `;
        container.appendChild(div);
      }
    });
  }

  updateTable(botDetails) {
    const tbody = document.querySelector("#details_table tbody");
    if (!tbody) return;

    tbody.innerHTML = "";

    botDetails.forEach((bot) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${bot.name}</td>
        <td>${bot.platform_id}</td>
        <td>${bot.sessions.toLocaleString()}</td>
        <td>${bot.incoming_messages.toLocaleString()}</td>
        <td>${bot.outgoing_messages.toLocaleString()}</td>
        <td>${bot.unique_contacts.toLocaleString()}</td>
        <td>${bot.sessions_abandoned.toLocaleString()}</td>
        <td>${bot.sessions_with_panel.toLocaleString()}</td>
        <td>${this.formatTime(bot.avg_waiting_time)}</td>
        <td>${this.formatTime(bot.avg_session_length)}</td>
      `;
      tbody.appendChild(row);
    });
  }

  generateColors(count) {
    const colors = [
      "#4285f4",
      "#ea4335",
      "#fbbc04",
      "#34a853",
      "#9aa0a6",
      "#ff6d01",
      "#46bdc6",
      "#7627bb",
      "#ff4081",
      "#795548",
    ];

    const result = [];
    for (let i = 0; i < count; i++) {
      result.push(colors[i % colors.length]);
    }
    return result;
  }

  formatTime(milliseconds) {
    if (!milliseconds || milliseconds === 0) return "00:00:00";

    const seconds = Math.floor(milliseconds / 1000);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    return (
      String(hours).padStart(2, "0") +
      ":" +
      String(minutes).padStart(2, "0") +
      ":" +
      String(secs).padStart(2, "0")
    );
  }

  showLoading() {
    const modal = document.getElementById("loadingModal");
    if (modal) {
      // Try Bootstrap 5 first, then Bootstrap 4
      if (window.bootstrap?.Modal) {
        const bsModal = new window.bootstrap.Modal(modal);
        bsModal.show();
      } else if (window.jQuery && window.jQuery.fn.modal) {
        window.jQuery(modal).modal("show");
      }
    }
  }

  hideLoading() {
    const modal = document.getElementById("loadingModal");
    if (modal) {
      // Try Bootstrap 5 first, then Bootstrap 4
      if (window.bootstrap?.Modal) {
        const bsModal = window.bootstrap.Modal.getInstance(modal);
        if (bsModal) bsModal.hide();
      } else if (window.jQuery && window.jQuery.fn.modal) {
        window.jQuery(modal).modal("hide");
      }
    }
  }
  updateSyncStatus(lastSyncInput) {
    const lastSyncDate =
      typeof input === "string" ? new Date(lastSyncInput) : lastSyncInput;
    if (isNaN(lastSyncDate)) {
      document.getElementById("last_sync_time").textContent = "Fecha inválida";
      return;
    }

    const now = new Date();

    const isToday =
      lastSyncDate.getDate() === now.getDate() &&
      lastSyncDate.getMonth() === now.getMonth() &&
      lastSyncDate.getFullYear() === now.getFullYear();

    // Formateo de hora
    const formattedDate = isToday
      ? "Hoy " +
        lastSyncDate.toLocaleTimeString("es-CO", {
          hour: "2-digit",
          minute: "2-digit",
          hour12: true,
        })
      : lastSyncDate.toLocaleString("es-CO", {
          day: "2-digit",
          month: "long",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          hour12: true,
        });

    // Actualizar fecha
    document.getElementById("last_sync_time").textContent = formattedDate;

    // Actualizar estado visual
    const dot = document.getElementById("sync_dot");
    const text = document.getElementById("sync_text");

    if (isToday) {
      dot.classList.remove("bg-danger");
      dot.classList.add("bg-success");
      text.classList.remove("text-danger");
      text.classList.add("text-success");
      text.textContent = "Sincronizado";
    } else {
      dot.classList.remove("bg-success");
      dot.classList.add("bg-danger");
      text.classList.remove("text-success");
      text.classList.add("text-danger");
      text.textContent = "Desincronizado";
    }
  }

  toggleLoader(show) {
    const loaderOverlay = document.getElementById("loader-overlay");
    if (loaderOverlay) {
      loaderOverlay.style.display = show ? "flex" : "none";
    }
    const loader = document.getElementById("loader-data");
    if (loader) {
      loader.style.display = show ? "inline-block" : "none";
    }
  }

  // ✅ SOLUCIÓN AL ERROR: Métodos de notificación corregidos
  showSuccess(message) {
    try {
      // Intentar usar el servicio de notificación de Odoo de forma segura
      if (
        typeof odoo !== "undefined" &&
        odoo.env &&
        odoo.env.services &&
        odoo.env.services.notification
      ) {
        odoo.env.services.notification.add(message, {
          type: "success",
          sticky: false,
        });
      } else {
        // Fallback: usar notificación personalizada
        this.showCustomNotification(message, "success");
      }
    } catch (error) {
      console.log("Success:", message);
      // Último fallback
      this.showCustomNotification(message, "success");
    }
  }

  showError(message) {
    try {
      // Intentar usar el servicio de notificación de Odoo de forma segura
      if (
        typeof odoo !== "undefined" &&
        odoo.env &&
        odoo.env.services &&
        odoo.env.services.notification
      ) {
        odoo.env.services.notification.add(message, {
          type: "danger",
          sticky: true,
        });
      } else {
        // Fallback: usar notificación personalizada
        this.showCustomNotification(message, "error");
      }
    } catch (error) {
      console.error("Error:", message);
      // Último fallback
      this.showCustomNotification(message, "error");
    }
  }

  // Método de notificación personalizada como fallback
  showCustomNotification(message, type) {
    // Crear una notificación personalizada
    const notification = document.createElement("div");
    const alertType = type === "success" ? "success" : "danger";

    notification.className = `alert alert-${alertType} alert-dismissible position-fixed`;
    notification.style.cssText = `
      top: 40px; 
      right: 20px; 
      z-index: 9999; 
      min-width: 300px;
      max-width: 500px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;

    notification.innerHTML = `
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      <div>${message}</div>
    `;

    document.body.appendChild(notification);

    // Auto-remove después de unos segundos
    const timeout = type === "success" ? 3000 : 5000;
    setTimeout(() => {
      if (notification.parentNode) {
        notification.remove();
      }
    }, timeout);

    // Permitir cerrar manualmente
    const closeBtn = notification.querySelector(".btn-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        if (notification.parentNode) {
          notification.remove();
        }
      });
    }
  }

  setupAutoRefresh() {
    // Auto-refresh cada 10 minutos
    setInterval(() => {
      if (this.initialized && !this.loadData) {
        this.loadRealtimeData();
      }
    }, 3600000); // 10 minutos = 600000 ms
  }
}

// Initialize the dashboard manager
const dashboardManager = new DashboardManager();

// Export functions for external use
export const loadDashboardData = () => dashboardManager.loadDashboardData();
export const syncData = () => dashboardManager.syncData();
export const loadRealtimeData = () => dashboardManager.loadRealtimeData();
