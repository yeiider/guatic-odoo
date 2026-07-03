/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
const { Component, onWillStart, useRef, onMounted, useState } = owl

export class OwlDashFGAF extends Component {

    setup() {
        this.orm = useService("orm")
        // ⚠️ Inicializar estado correctamente
        this.state = useState({
            iframeUrl: "",
        });
        // ⚠️ IMPORTANTE: acceder a this.router.current SOLO dentro de `onWillStart` o después
        onWillStart(async () => {
            //alert("Cargando dashboard...");
            await  this.obtenerIframeUrl()
        });
    }


    async obtenerIframeUrl() {

        let iframeUrl = "https://dash.fenalcovalle.com/public/dashboard/61da6b65-af0d-4bb3-8274-3e2ccc00c441?tab=11-resumen-general"
        const params = this.props.action ? this.props.action.params : {};
        console.log("Parámetros recibidos:", params);
        console.log("Parámetros recibidos:", this.props.action.params.dashboard); 
        if (params.dashboard=='audio') { 
            iframeUrl = "https://apps2.asertis.com.co/web#id=14771&cids=1&menu_id=148&active_id=14771&model=fv_transacciones_unica&view_type=form"
        }

       
        this.state.iframeUrl = iframeUrl;
        return iframeUrl
    }
    
     
} 

OwlDashFGAF.template = "owl.OwlFactDashboard"
//OwlDashFGAF.components = { NotifyCard, KpiCard, ChartRenderer }   
registry.category("actions").add("iframe.dashboard", OwlDashFGAF) 