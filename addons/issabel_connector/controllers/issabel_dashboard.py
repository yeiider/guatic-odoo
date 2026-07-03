# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class IssabelDashboardController(http.Controller):

    @http.route("/issabel/dashboard/data", type="json", auth="user")
    def get_dashboard_data(self):
        """
        Endpoint para obtener datos del dashboard
        """
        return request.env["issabel.dashboard"].sudo().get_dashboard_data()