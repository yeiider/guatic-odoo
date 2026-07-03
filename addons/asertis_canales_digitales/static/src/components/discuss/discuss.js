/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

import { ChatHistoryPanel } from "../chat_history_panel/chat_history_panel";

import { Discuss } from "@mail/core/public_web/discuss";



patch(Discuss.prototype, {
  setup() {
    super.setup();
    this.chatHistoryService = useService("mail.chat_history");

  },

  get chatHistoryState() {
    return this.chatHistoryService.state;
  },
});

patch(Discuss, {
  components: {
    ...Discuss.components,
    ChatHistoryPanel,
  },
});
