/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export const chatHistoryService = {
  dependencies: ["orm"],

  start(env, services) {
    const state = reactive({
      isOpen: false,
      currentThread: null,
      messages: [],
      isLoading: false,
      error: null,
      lastSync: null,
      hasMore: false,
      nextPage: null,
    });

    function toggleHistoryPanel(thread) {
      if (state.isOpen && state.currentThread?.id === thread.id) {
        closeHistoryPanel();
      } else {
        openHistoryPanel(thread);
      }
    }

    async function openHistoryPanel(thread) {
      // Si hay un panel abierto para otro thread, lo cerramos primero
      if (state.isOpen && state.currentThread?.id !== thread.id) {
        closeHistoryPanel();
      }

      state.isOpen = true;
      state.currentThread = thread;
      state.error = null;
      await loadHistoryMessages(thread.id);
    }

    function closeHistoryPanel() {
      state.isOpen = false;
      state.currentThread = null;
      state.messages = [];
      state.error = null;
      state.lastSync = null;
      state.hasMore = false;
      state.nextPage = null;
    }

    function handleThreadChange(newThread) {
      if (
        state.isOpen &&
        state.currentThread &&
        state.currentThread.id !== newThread?.id
      ) {
        closeHistoryPanel();
      }
    }

    async function getChannelById(channelId) {
      try {
        const result = await services.orm.call(
          "discuss.channel",
          "search_read",
          [[["id", "=", channelId]]],
          {
            fields: [
              "id",
              "provider_metadata",
              "provider_name",
              "external_channel_id",
            ],
            limit: 1,
          }
        );
        return result.length > 0 ? result[0] : null;
      } catch (error) {
        return null;
      }
    }

    async function loadHistoryMessages(channelId, forceReload = false) {
      if (!channelId) {
        state.error = _t("ID de canal inválido");
        return;
      }

      state.error = null;
      state.isLoading = true;

      // Limpiar mensajes solo si no es recarga o es un canal diferente
      if (forceReload || state.currentThread?.id !== channelId) {
        state.messages = [];
      }

      try {
        const channel = await getChannelById(channelId);

        if (!channel) {
          updateStateFromData(
            { messages: [], has_more: false, next_page: null },
            false
          );
          state.isLoading = false;
          return;
        }

        // Comentado para pruebas - permitir canales sin proveedor
        if (!channel.provider_name) {
          updateStateFromData(
            { messages: [], has_more: false, next_page: null },
            false
          );
          state.isLoading = false;
          return;
          // No retornar aquí, continuar con datos mock
        }

        // consumir el servicio aqui
        //const response = await rpc(`/api/chat/history/${channelId}`, {
         // page: 1,
         // limit: 50,
          //force_refresh: false,
        //});

        
        const mockResponse = {
          messages: [
            {
              id: 1,
              author_name: "Asistente",
              author_avatar: null,
              timestamp: "2025-08-20T09:00:00Z",
              content:
                "¡Bienvenido al Centro de Salud Virtual! ¿En qué puedo ayudarte hoy?",
              message_type: "system",
              attachments: [],
            },
            {
              id: 2,
              author_name: "Juan Pérez",
              author_avatar: "/web/image/res.partner/5/avatar_128",
              timestamp: "2025-08-20T09:02:00Z",
              content:
                "Buenos días, quiero agendar una cita con medicina general.",
              message_type: "chat",
              attachments: [],
            },
            {
              id: 3,
              author_name: "Asistente",
              author_avatar: null,
              timestamp: "2025-08-20T09:04:00Z",
              content:
                "Claro Juan. ¿Eres afiliado a alguna EPS o es consulta particular?",
              message_type: "chat",
              attachments: [],
            },
            {
              id: 4,
              author_name: "Juan Pérez",
              author_avatar: "/web/image/res.partner/5/avatar_128",
              timestamp: "2025-08-20T09:05:30Z",
              content: "Sí, soy afiliado a la EPS SaludVida.",
              message_type: "chat",
              attachments: [],
            },
            {
              id: 5,
              author_name: "Asistente",
              author_avatar: null,
              timestamp: "2025-08-20T09:07:00Z",
              content:
                "Perfecto. ¿Tienes orden médica o deseas una consulta de control?",
              message_type: "chat",
              attachments: [],
            },
            {
              id: 6,
              author_name: "Juan Pérez",
              author_avatar: "/web/image/res.partner/5/avatar_128",
              timestamp: "2025-08-20T09:08:15Z",
              content: "Sí, tengo la orden médica. La adjunto aquí.",
              message_type: "chat",
              attachments: [
                {
                  id: 301,
                  filename: "orden_medica.pdf",
                  mimetype: "application/pdf",
                  size: 304800,
                  download_url: "/web/content/301?download=true",
                },
              ],
            },
            {
              id: 7,
              author_name: "Asistente",
              author_avatar: null,
              timestamp: "2025-08-20T09:10:00Z",
              content:
                "Orden recibida ✅. Tenemos disponibilidad el 25 de agosto a las 10:30 AM o el 26 de agosto a las 8:00 AM. ¿Cuál prefieres?",
              message_type: "chat",
              attachments: [],
            },
            {
              id: 8,
              author_name: "Juan Pérez",
              author_avatar: "/web/image/res.partner/5/avatar_128",
              timestamp: "2025-08-20T09:12:00Z",
              content: "El 25 de agosto a las 10:30 AM está perfecto.",
              message_type: "chat",
              attachments: [],
            },
            {
              id: 9,
              author_name: "Asistente",
              author_avatar: null,
              timestamp: "2025-08-20T09:14:00Z",
              content: "Muy bien 👌. Te enviaré el comprobante de la cita.",
              message_type: "chat",
              attachments: [],
            },
            {
              id: 10,
              author_name: "Asistente",
              author_avatar: null,
              timestamp: "2025-08-20T09:15:30Z",
              content:
                "Aquí tienes tu comprobante en PDF. Recuerda llegar 15 minutos antes con tu documento de identidad.",
              message_type: "file",
              attachments: [
                {
                  id: 302,
                  filename: "comprobante_cita_JuanPérez.pdf",
                  mimetype: "application/pdf",
                  size: 105000,
                  download_url: "/web/content/302?download=true",
                },
              ],
            },
            {
              id: 11,
              author_name: "Juan Pérez",
              author_avatar: "/web/image/res.partner/5/avatar_128",
              timestamp: "2025-08-20T09:18:00Z",
              content: "Muchas gracias por tu ayuda. 👍",
              message_type: "chat",
              attachments: [],
            },
            {
              id: 12,
              author_name: "Asistente",
              author_avatar: null,
              timestamp: "2025-08-24T18:00:00Z",
              content:
                "📅 Recordatorio: Mañana tienes tu cita con medicina general a las 10:30 AM en la sede principal.",
              message_type: "system",
              attachments: [],
            },
            {
              id: 13,
              author_name: "Juan Pérez",
              author_avatar: "/web/image/res.partner/5/avatar_128",
              timestamp: "2025-08-24T18:10:00Z",
              content: "Gracias por el recordatorio, asistiré puntualmente.",
              message_type: "chat",
              attachments: [],
            },
            {
              id: 14,
              author_name: "Asistente",
              author_avatar: null,
              timestamp: "2025-08-25T12:30:00Z",
              content:
                "Esperamos que tu cita haya sido satisfactoria. ¿Deseas responder una breve encuesta?",
              message_type: "chat",
              attachments: [],
            },
            {
              id: 15,
              author_name: "Juan Pérez",
              author_avatar: "/web/image/res.partner/5/avatar_128",
              timestamp: "2025-08-25T12:35:00Z",
              content: "Sí, claro. Envíamela.",
              message_type: "chat",
              attachments: [],
            },
            {
              id: 16,
              author_name: "Asistente",
              author_avatar: null,
              timestamp: "2025-08-25T12:40:00Z",
              content:
                "Aquí tienes el formulario de encuesta en PDF. ¡Gracias por tu tiempo!",
              message_type: "file",
              attachments: [
                {
                  id: 401,
                  filename: "encuesta_satisfaccion.pdf",
                  mimetype: "application/pdf",
                  size: 50000,
                  download_url: "/web/content/401?download=true",
                },
              ],
            },
            {
              id: 17,
              author_name: "Juan Pérez",
              author_avatar: "/web/image/res.partner/5/avatar_128",
              timestamp: "2025-08-25T12:50:00Z",
              content:
                "Listo, ya completé la encuesta. Gracias por la atención.",
              message_type: "chat",
              attachments: [],
            },
          ],
          has_more: false,
          next_page: null,
        };
        const responseData = mockResponse;

        if (responseData && responseData.messages) {
          saveToLocalStorage(channelId, responseData);
          updateStateFromData(responseData, false);
        
        } else {
          throw new Error("Respuesta inválida del API");
        }
      } catch (error) {
        console.error("Error cargando historial:", error);

        // Intentar cargar desde localStorage
        const cachedData = loadFromLocalStorage(channelId);
        if (cachedData) {
          console.log("Cargando datos desde localStorage");
          updateStateFromData(cachedData.data, true);
          state.lastSync = cachedData.timestamp;
        } else {
          console.log("No hay datos en caché, mostrando error");
          state.error = _t("No se pudo cargar el historial");
          state.messages = [];
        }
      } finally {
        state.isLoading = false;
        console.log(
          "Estado final - isLoading:",
          state.isLoading,
          "messages:",
          state.messages.length,
          "error:",
          state.error
        );
      }
    }

    function saveToLocalStorage(channelId, data) {
      try {
        const storageData = {
          data: data,
          timestamp: new Date().toISOString(),
          channel_id: channelId,
        };
        localStorage.setItem(
          `chat_history_${channelId}`,
          JSON.stringify(storageData)
        );
        console.log("Datos guardados en localStorage para canal:", channelId);
      } catch (error) {
        console.warn("Failed to save to localStorage:", error);
      }
    }

    function loadFromLocalStorage(channelId) {
      try {
        const stored = localStorage.getItem(`chat_history_${channelId}`);
        return stored ? JSON.parse(stored) : null;
      } catch (error) {
        console.warn("Failed to load from localStorage:", error);
        return null;
      }
    }

    function updateStateFromData(data, isFromCache = false) {
      console.log(
        "updateStateFromData llamado con:",
        data,
        "isFromCache:",
        isFromCache
      );
      state.messages = data.messages || [];
      state.hasMore = data.has_more || false;
      state.nextPage = data.next_page || null;
      if (!isFromCache) {
        state.lastSync = new Date().toISOString();
      }
      console.log("Estado actualizado - messages:", state.messages.length);
    }

    function clearHistory(channelId) {
      try {
        localStorage.removeItem(`chat_history_${channelId}`);
        if (state.currentThread?.id === channelId) {
          state.messages = [];
          state.lastSync = null;
          state.hasMore = false;
          state.nextPage = null;
        }
      } catch (error) {
        console.warn("Failed to clear history:", error);
      }
    }

    function formatTimestamp(timestamp) {
      try {
        const date = new Date(timestamp);
        const now = new Date();
        const today = new Date(
          now.getFullYear(),
          now.getMonth(),
          now.getDate()
        );
        const messageDate = new Date(
          date.getFullYear(),
          date.getMonth(),
          date.getDate()
        );

        if (messageDate.getTime() === today.getTime()) {
          return date.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          });
        } else {
          return (
            date.toLocaleDateString() +
            " " +
            date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
          );
        }
      } catch (error) {
        console.error("Error formatting timestamp:", error);
        return timestamp;
      }
    }

    return {
      state,
      toggleHistoryPanel,
      getChannelById,
      openHistoryPanel,
      closeHistoryPanel,
      loadHistoryMessages,
      clearHistory,
      formatTimestamp,
      handleThreadChange,
    };
  },
};

registry.category("services").add("mail.chat_history", chatHistoryService);
