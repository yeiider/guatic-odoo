/** @odoo-module **/
import {
  Component,
  onWillStart,
  onMounted,
  onWillUpdateProps,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { HistoryMessage } from "../history_message/history_message";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

export class ChatHistoryPanel extends Component {
  static template = "discuss.ChatHistoryPanel";
  static props = ["thread"];
  static components = { HistoryMessage, ActionPanel };

  setup() {
    this.chatHistoryService = useService("mail.chat_history");
    
    // Cargar mensajes al inicializar
    onWillStart(async () => {
      if (this.props.thread && this.props.thread.id) {
        await this.chatHistoryService.loadHistoryMessages(this.props.thread.id);
      }
    });

    // Manejar cambios de thread
    onWillUpdateProps(async (nextProps) => {
      const currentThreadId = this.props.thread?.id;
      const nextThreadId = nextProps.thread?.id;
      
      if (nextThreadId && nextThreadId !== currentThreadId) {
        await this.chatHistoryService.loadHistoryMessages(nextThreadId);
      }
    });

    onMounted(() => {
      this.scrollToBottom();
    });
  }

  get state() {
    return this.chatHistoryService.state;
  }

  get hasMessages() {
    return this.state.messages && this.state.messages.length > 0;
  }

  get showLastSyncInfo() {
    return this.state.lastSync && !this.state.isLoading;
  }

  get lastSyncFormatted() {
    if (!this.state.lastSync) return "";
    return this.chatHistoryService.formatTimestamp(this.state.lastSync);
  }

  onClose() {
    this.chatHistoryService.closeHistoryPanel();
  }

  async onRefresh() {
    if (this.props.thread && this.props.thread.id) {
      await this.chatHistoryService.loadHistoryMessages(this.props.thread.id);
    }
  }

  onClearHistory() {
    if (this.props.thread && this.props.thread.id) {
      this.chatHistoryService.clearHistory(this.props.thread.id);
    }
  }

  scrollToBottom() {
    const container = this.el?.querySelector(".o-mail-ChatHistoryPanel-messages");
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }
}