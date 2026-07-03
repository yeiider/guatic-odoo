import { Component, useEffect, useRef, useState } from "@odoo/owl";

import { DeviceSelectionDialog } from "@voip/mobile/device_selection_dialog";
import { TransferPopover } from "@voip/softphone/transfer_popover";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class CorrespondenceDetails extends Component {
  static props = ["extraClass?", "correspondence"];
  static defaultProps = { extraClass: "" };
  static template = "voip.CorrespondenceDetails";

  setup() {
    this.action = useService("action");
    this.callService = useService("voip.call");
    this.dialog = useService("dialog");
    this.orm = this.env.services.orm;
    this.userAgent = useState(useService("voip.user_agent"));
    this.voip = useService("voip");
    this.softphone = this.voip.softphone;
    this.transferButtonRef = useRef("transferButton");
    this.transferPopover = usePopover(TransferPopover, { position: "top" });
    useEffect(
      () => this.userAgent.updateTracks(),
      () => [this.userAgent.session?.isMute, this.userAgent.session?.isOnHold]
    );
  }

  /** @returns {import("@mail/activity/activity_model").Activity | undefined} */
  get activity() {
    return this.props.correspondence.activity;
  }

  /** @returns {boolean} */
  get areInCallActionsDisabled() {
    return this.call?.state !== "ongoing" || !this.userAgent.session;
  }

  /** @returns {string} */
  get bgStyleClasses() {
    if (!this.call?.isInProgress) {
      return "";
    }
    return `bg-opacity-25 bg-${this.isOnHold ? "info" : "success"}`;
  }

  /** @returns {import("@voip/core/call_model").Call | undefined} */
  get call() {
    return this.props.correspondence.call;
  }

  /** @returns {string} */
  get callStatus() {
    if (this.userAgent.session?.inviteState === "ringing") {
      return _t("Ringing…");
    }
    if (this.call.state === "ongoing") {
      const minutes = `${Math.floor(this.call.timer.time / 60)}`.padStart(
        2,
        "0"
      );
      const seconds = `${this.call.timer.time % 60}`.padStart(2, "0");
      return _t("In call for: %(minutes)s:%(seconds)s", { minutes, seconds });
    }
    return "";
  }

  /** @returns {string} */
  get displayName() {
    if (this.call) {
      return this.call.displayName;
    }
    return this.activity?.name ?? "";
  }

  /** @returns {boolean} */
  get isMobileOs() {
    return isMobileOS();
  }

  /** @returns {boolean} */
  get isOnHold() {
    return this.userAgent.session?.isOnHold ?? false;
  }

  /** @returns {string} */
  get landlineNumber() {
    if (this.call) {
      if (
        !this.partner ||
        this.partner.mobileNumber !== this.call.phoneNumber
      ) {
        return this.call.phoneNumber;
      }
      return "";
    }
    if (this.activity) {
      return this.activity.phone;
    }
    return this.partner.landlineNumber || "";
  }

  /** @returns {string} */
  get mobileNumber() {
    if (this.activity) {
      return this.activity.mobile;
    }
    if (!this.partner && !this.call) {
      return "";
    }
    if (this.call && this.call.phoneNumber === this.partner?.mobileNumber) {
      return this.call.phoneNumber;
    }
    return this.partner?.mobileNumber || "";
  }

  /** @returns {string} */
  get muteText() {
    return !this.userAgent.session?.isMute ? _t("Mute") : _t("Unmute");
  }

  /** @returns {import("@mail/core/persona_model").Persona | undefined} */
  get partner() {
    return this.props.correspondence.partner;
  }

  /** @returns {string} */
  get putOnHoldText() {
    return this.isOnHold ? _t("Resume") : _t("Hold");
  }

  /** @param {MouseEvent} ev */
  onClickActivity(ev) {
    this.softphone.fold();
    const action = {
      type: "ir.actions.act_window",
      res_id: false,
      res_model: "mail.activity",
      views: [[false, "form"]],
      view_mode: "form",
      target: "new",
      context: {},
    };
    if (this.activity) {
      action.context.default_res_id = this.activity.res_id;
      action.context.default_res_model = this.activity.res_model;
    } else {
      action.context.default_res_id = this.partner.id;
      action.context.default_res_model = "res.partner";
    }
    this.action.doAction(action);
  }

  /** @param {MouseEvent} ev */
  async onClickCancel(ev) {
    await this.orm.call("mail.activity", "unlink", [[this.activity.id]]);
    this.activity.remove();
    this.softphone.selectedCorrespondence = null;
    if (this.softphone.isInAutoCallMode) {
      this.softphone.selectNextActivity();
    }
  }

  /** @param {MouseEvent} ev */
  async onClickChangeInputDevice(ev) {
    this.dialog.add(DeviceSelectionDialog);
  }

  /** @param {MouseEvent} ev */
  onClickClose(ev) {
    this.softphone.selectedCorrespondence = null;
    this.softphone.isInAutoCallMode = false;
    this.voip.resetMissedCalls();
  }

  /** @param {MouseEvent} ev */
  onClickEdit(ev) {
    this.softphone.fold();
    this.action.doAction({
      type: "ir.actions.act_window",
      res_id: this.activityId,
      res_model: "mail.activity",
      views: [[false, "form"]],
      view_mode: "form",
      target: "new",
      context: {
        default_res_id: this.activity.res_id,
        default_res_model: this.activity.res_model,
      },
    });
  }

  /** @param {MouseEvent} ev */
  onClickEmail(ev) {
    this.softphone.fold();
    if (this.partner) {
      this.action.doAction({
        type: "ir.actions.act_window",
        res_model: "mail.compose.message",
        views: [[false, "form"]],
        target: "new",
        context: {
          default_res_ids: [this.partner.id],
          default_model: "res.partner",
          default_partner_ids: [this.partner.id],
          default_composition_mode: "comment",
          default_use_template: true,
        },
      });
    }
  }

  /** @param {MouseEvent} ev */
  async onClickMarkAsDone(ev) {
    await this.activity.markAsDone();
    this.activity.delete();
    this.softphone.selectedCorrespondence = null;
    if (this.softphone.isInAutoCallMode) {
      this.softphone.selectNextActivity();
    }
  }

  /** @param {MouseEvent} ev */
  onClickMute(ev) {
    if (this.areInCallActionsDisabled) {
      return;
    }
    this.userAgent.session.isMute = !this.userAgent.session.isMute;
  }

  /** @param {MouseEvent} ev */
  onClickHold(ev) {
    if (this.areInCallActionsDisabled) {
      return;
    }
    this.userAgent.setHold(!this.isOnHold);
  }

  /** @param {MouseEvent} ev */
  onClickPartner(ev) {
    this.softphone.fold();
    const action = {
      type: "ir.actions.act_window",
      res_model: "res.partner",
      views: [[false, "form"]],
      target: "new",
    };
    if (this.partner) {
      action.res_id = this.partner.id;
    }
    // TODO: Missing features from the previous code:
    // ─ if no partner but activity: prefill form with data from activity
    this.action.doAction(action);
  }

  /** @param {MouseEvent} ev */
  onClickSalesOrder(ev) {
    this.softphone.fold();
    const action = {
      type: "ir.actions.act_window",
      res_model: "sale.order",
      views: [[false, "form"]],
      target: "target",
    };

    if (this.partner) {
      action.context = {
        default_partner_id: this.partner.id, // reemplaza 1 con el ID del partner deseado
      };
    }
    // TODO: Missing features from the previous code:
    // ─ if no partner but activity: prefill form with data from activity
    this.action.doAction(action);
  }
    /** @param {MouseEvent} ev */
    onClickViewPartnerCalendar(ev) {
        if (!this.partner) {
            // Si no hay partner, mostrar mensaje o abrir calendario general
            this.notification.add("No hay contacto seleccionado para filtrar el calendario", {
                type: "warning"
            });
            return;
        }

        this.softphone.fold();
        
        const action = {
            type: "ir.actions.act_window",
            res_model: "calendar.event",
            name: `Calendario de ${this.partner.name}`,
            views: [
                [false, "calendar"],  // Vista de calendario
                [false, "list"],      // Vista de lista
                [false, "form"]       // Vista de formulario
            ],
            target: "current",
            domain: [
                '|',
                ['partner_ids', 'in', [this.partner.id]],
                ['attendee_ids.partner_id', '=', this.partner.id]
            ],
            context: {
                // Contexto para filtrar por el partner
                default_partner_ids: [[6, 0, [this.partner.id]]],
                search_default_partner_id: this.partner.id,
            }
        };

        this.action.doAction(action);
    }

  /** @param {MouseEvent} ev */
  onClickScheduleAppointment(ev) {
    this.softphone.fold();

    // Configuración base para crear una cita
    const action = {
      type: "ir.actions.act_window",
      res_model: "calendar.event", // Modelo para eventos de calendario
      views: [[false, "form"]],
      target: "current", // Abrir en ventana modal (recomendado para citas)
    };

    // Contexto con valores por defecto para la cita
    const defaultContext = {
      // Campos básicos requeridos
      default_name: "Nueva Cita ", // Nombre/título de la cita
      default_start: this.getCurrentDateTime(), // Fecha y hora de inicio
      default_stop: this.getEndDateTime(), // Fecha y hora de fin

      // Configuración del evento
      default_allday: false, // No es evento de todo el día
      default_duration: 1, // Duración en horas (ajustar según necesidad)

      // Participantes y recordatorios
      default_alarm_ids: [[6, 0, [1]]], // IDs de alarmas/recordatorios predefinidos

      // Agregar teléfono si está disponible
      ...(this.getPhoneNumber() && { default_phone: this.getPhoneNumber() }),
    };

    // Si hay un partner asociado, agregarlo como participante
    if (this.partner) {
      defaultContext.default_partner_ids = [[6, 0, [this.partner.id]]];
      defaultContext.default_name = `Cita con ${this.partner.name}`;

      // Si el partner tiene email, agregarlo
      if (this.partner.email) {
        defaultContext.default_attendee_ids = [
          [
            0,
            0,
            {
              partner_id: this.partner.id,
              email: this.partner.email,
            },
          ],
        ];
      }
    }

    // Si hay una actividad pendiente, usar sus datos
    if (this.activity) {
      defaultContext.default_name =
        this.activity.summary || "Cita desde actividad";
      defaultContext.default_description = this.activity.note || "";

      // Si la actividad tiene fecha límite, usarla como fecha de la cita
      if (this.activity.date_deadline) {
        defaultContext.default_start =
          this.activity.date_deadline + " 09:00:00";
        defaultContext.default_stop = this.activity.date_deadline + " 10:00:00";
      }
    }

    action.context = defaultContext;
    this.action.doAction(action);
  }

  /**
   * Obtiene la fecha y hora actual en formato requerido por Odoo
   * @returns {string} Fecha y hora en formato 'YYYY-MM-DD HH:mm:ss'
   */
  getCurrentDateTime() {
    const now = new Date();
    // Redondear a la siguiente hora completa
    now.setMinutes(0, 0, 0);
    now.setHours(now.getHours() + 1);

    return this.formatDateTime(now);
  }

  /**
   * Obtiene la fecha y hora de fin (1 hora después del inicio)
   * @returns {string} Fecha y hora en formato 'YYYY-MM-DD HH:mm:ss'
   */
  getEndDateTime() {
    const end = new Date();
    end.setMinutes(0, 0, 0);
    end.setHours(end.getHours() + 2); // 1 hora después del inicio

    return this.formatDateTime(end);
  }

  /**
   * Formatea una fecha para Odoo
   * @param {Date} date
   * @returns {string}
   */
  formatDateTime(date) {
    return (
      date.getFullYear() +
      "-" +
      String(date.getMonth() + 1).padStart(2, "0") +
      "-" +
      String(date.getDate()).padStart(2, "0") +
      " " +
      String(date.getHours()).padStart(2, "0") +
      ":" +
      String(date.getMinutes()).padStart(2, "0") +
      ":" +
      String(date.getSeconds()).padStart(2, "0")
    );
  }

  /**
   * Obtiene el número de teléfono desde diferentes fuentes posibles
   * @returns {string|null} Número de teléfono o null si no está disponible
   */
  getPhoneNumber() {
    // Prioridad: partner phone > partner mobile > softphone number > activity phone
    if (this.partner) {
      return this.partner.phone || this.partner.mobile || null;
    }

    // Si hay un número de teléfono desde el softphone
    if (this.softphone && this.softphone.phoneNumber) {
      return this.softphone.phoneNumber;
    }

    // Si hay actividad con teléfono
    if (this.activity && this.activity.phone) {
      return this.activity.phone;
    }

    return null;
  }

  /**
   * @param {MouseEvent} ev
   * @param {string} phoneNumber
   */
  onClickPhoneNumber(ev, phoneNumber) {
    ev.preventDefault();
    this.userAgent.makeCall({
      activity: this.activity,
      partner: this.partner,
      phone_number: phoneNumber,
    });
  }

  /** @param {MouseEvent} ev */
  async onClickRecord(ev) {
    this.softphone.fold();
    const resModel = this.activity.res_model;
    const resId = this.activity.res_id;
    const viewId = await this.orm.call(resModel, "get_formview_id", [[resId]], {
      context: user.context,
    });
    this.action.doAction({
      type: "ir.actions.act_window",
      res_id: resId,
      res_model: resModel,
      views: [[viewId || false, "form"]],
      view_mode: "form",
      view_type: "form",
      target: "new",
    });
  }

  /** @param {MouseEvent} ev */
  onClickTransfer(ev) {
    if (this.transferPopover.isOpen) {
      return;
    }
    this.transferPopover.open(this.transferButtonRef.el, {
      defaultInputValue: this.voip.store.settings.external_device_number || "",
    });
  }
}
