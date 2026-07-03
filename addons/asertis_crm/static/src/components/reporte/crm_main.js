/** @odoo-module */

import { registry } from "@web/core/registry";
import { Card } from "../card/card";
import { useService } from "@web/core/utils/hooks";
const { Component, onWillStart, useState } = owl;

export class CrmMain extends Component {
  setup() {
    this.state = useState({
      // Oportunidades
      totalOportunidades: 0,
      totalCerradas: 0,

      // Clientes
      totalClientes: 0,
    });

    this.orm = useService("orm");
    this.actionService = useService("action");
    this.user = useService("user");

    onWillStart(async () => {
      await Promise.all([this.getData()]);
    });
  }

  /************************
   * FUNCIONES AUXILIARES *
   ***********************/

  /****************************************************
   * FUNCIONES PARA EXTRAER DATOS Y REALIZAR CÁLCULOS *
   ***************************************************/

  async getData() {
    // Total de oportunidades
    const totalOportunidades = await this.orm.searchCount(
      "crm_asertis", // nombre del modelo
      [["responsable", "=", this.user.userId]] // dominio
    );
    this.state.totalOportunidades = totalOportunidades;

    // Total de oportunidades
    const brr = await this.orm.searchRead(
      "crm_asertis",
      [["responsable", "=", this.user.userId]],
      ["estado_id"]
    );
    // Filtra los que están "Ganada" o "Perdida"
    const cerradas = brr.filter((r) => {
      const estado = r.estado_id?.[1]; // estado_id es [id, nombre]
      return estado === "Ganado" || estado === "Perdido";
    });
    this.state.totalCerradas = cerradas.length || 0;
    console.log("CERRADAS: ", cerradas);

    // Total de clientes
    const totalClientes = await this.orm.searchCount(
      "crm_asertis_clientes", // nombre del modelo
      [["responsable", "=", this.user.userId]] // dominio
    );
    this.state.totalClientes = totalClientes;
  }

  /********************************************************************
   *  FUNCIONES PARA IR A UNA ACCIÓN (ACCIÓN DE VENTANA / ACT.WINDOW) *
   *******************************************************************/
}

CrmMain.template = "asertis_crm.CrmMain";
CrmMain.components = {
  Card,
};

registry.category("actions").add("asertis_crm.crm_main", CrmMain);
