from odoo import http
from odoo.http import request
import json
import logging
_logger = logging.getLogger(__name__)

class PublicSaleOrderController(http.Controller):

    @http.route('/api/public/create_sale_order', type='json', auth='public', methods=['POST'], csrf=False)
    def create_sale_order(self, **kwargs):
        cuerpo_solicitud = http.request.httprequest.data.decode()
        data = json.loads(cuerpo_solicitud)

        # Buscar cliente por nombre o email
        partner = request.env['res.partner'].sudo().search([
            ('email', '=', data.get('email'))
        ], limit=1)

        # Si no existe el cliente, crearlo
        if not partner:
            partner = request.env['res.partner'].sudo().create({
                'name': data.get('name'),
                'email': data.get('email'),
                'phone': data.get('phone', ''),
            })

        # Crear la orden de venta
        order_vals = {
            'partner_id': partner.id,
            'order_line': [],
        }

        _logger.info(f"Creating sale order for products: {kwargs} ")

        for product_data in data.get('products', []):
            product = request.env['product.template'].sudo().search([
                ('default_code', '=', product_data.get('sku'))
            ], limit=1)

            _logger.info(f"Processing product with SKU: {product_data.get('sku')}, found: {product}")

    

            if product:
                order_vals['order_line'].append((0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': product_data.get('qty', 1),
                    'price_unit': product_data.get('price', product.list_price), 
                }))
        _logger.info(f"Creating sale order with values: {order_vals}")

        sale_order = request.env['sale.order'].sudo().create(order_vals)
    
        return {
            'status': 'success',
            'order_id': sale_order.id,
            'order_name': sale_order.name
        }
