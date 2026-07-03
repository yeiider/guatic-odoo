/** @odoo-module */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class TimelineOne2many extends Component {
  get activities() {
    const records = this.props.value?.records || [];
    return records;
  }

  showDetails(activity) {
    Swal.fire({
      title: "Información",
      html: `
        <p><strong>Actividad:</strong> ${activity.data.actividad}</p>
        <p><strong>Fecha:</strong> ${activity.data.fecha}</p>
        <p><strong>Descripción:</strong> ${activity.data.descripcion}</p>
        <p><strong>Registrado por:</strong> ${activity.data.create_uid[1]}</p>
      `,
      icon: "info",
    });
  }
}

TimelineOne2many.template = "asertis_crm.TimelineOne2many";
TimelineOne2many.props = {
  ...standardFieldProps,
};
TimelineOne2many.supportedTypes = ["one2many"];

registry.category("fields").add("timeline_one2many", TimelineOne2many);
