import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { ChatHistoryPanel } from "../../components/chat_history_panel/chat_history_panel";
import { _t } from "@web/core/l10n/translation";

threadActionsRegistry.add("history-messages", {
  component: ChatHistoryPanel,
  condition(component) {
    const thread = component.thread;
    console.log("Thread data:", { thread });

    // Verificar que es un canal de discusión
    if (thread?.model !== "discuss.channel") {
      return false;
    }

    // Diferentes formas de verificar que es un canal de tipo "chat"
    // Opción 1: Por channel_type
    console.log("Channel type:", thread?.channel_type);
    console.log("Is Chat Provider ", thread?.is_chat_provider);
    if (thread?.channel_type !== "chat") {
      return false;
    }

    return (
      !component.props.chatWindow || component.props.chatWindow.isOpen
    );
  },

  icon: "fa fa-fw fa-history",
  iconLarge: "fa fa-fw fa-lg fa-history",
  name: _t("Chat History"),

  sequence: 50,
  sequenceGroup: 10,

  toggle: true,
});
