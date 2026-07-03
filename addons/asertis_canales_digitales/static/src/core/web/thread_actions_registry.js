/** @odoo-module **/
import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { _t } from "@web/core/l10n/translation";
import { ChatHistoryPanel } from "../../components/chat_history_panel/chat_history_panel";

threadActionsRegistry.add("chat-history", {
  component: ChatHistoryPanel,
  condition: async (component) => {
    const thread = component.thread;

    if (thread?.model !== "discuss.channel") {
      return false;
    }

    if (thread?.channel_type !== "chat") {
      return false;
    }
    try {
      // Usar el servicio de chat history que ya tienes
      const chatHistoryService = component.env?.services?.["mail.chat_history"];
      if (!chatHistoryService) {
        return false;
      }

      // Usar la función getChannelById del servicio existente
      const channelData = await chatHistoryService.getChannelById(thread.id);

      if (!channelData) {
        return false;
      }

      if (!channelData.provider_metadata) {
        return false;
      }


      return !component.props.chatWindow || component.props.chatWindow.isOpen;
    } catch (error) {
      return false;
    }
  },
  panelOuterClass: "o-discuss-ChatHistoryPanel bg-inherit",
  icon: "fa  fa-fw fa-lg fa-history",
  name: _t("Historial del Chat"),

  sequence: 60,
  sequenceGroup: 10,

  onClick: (component) => {
    const chatHistoryService = component.env.services["mail.chat_history"];
    chatHistoryService.toggleHistoryPanel(component.thread);
  },
  toggle: true,
});
