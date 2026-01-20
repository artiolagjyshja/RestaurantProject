from odoo import models, api, fields

class ReportRestaurantSales(models.AbstractModel):
    _name = 'report.restaurant.report_sales_template'
    _description = 'Sales Report Logic'

    @api.model
    def _get_report_values(self, docids, data=None):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        employee_id = data.get('employee_id')
        
        # Domain për filtrin e rreshtave të porosive
        # Kujdes: Po kërkojmë te order lines, prandaj lidhja me datën është përmes order_id
        domain = [
            ('order_id.date_time', '>=', start_date),
            ('order_id.date_time', '<=', end_date),
            ('order_id.state', '=', 'served') # Vetëm të përfunduarat
        ]

        if employee_id:
            domain.append(('order_id.employee_id', '=', employee_id))

        lines = self.env['restaurant.order.lines'].search(domain)

        # Agregimet
        total_sales = sum(l.subtotal for l in lines)
        total_cost = sum(l.cost_price * l.quantity for l in lines) # Kostoja totale
        total_profit = total_sales - total_cost

        # Statistikat e produkteve
        product_stats = {}
        for line in lines:
            pid = line.product_id.id
            if pid not in product_stats:
                product_stats[pid] = {'name': line.product_id.product, 'qty': 0, 'sales': 0}
            
            product_stats[pid]['qty'] += line.quantity
            product_stats[pid]['sales'] += line.subtotal

        # Gjetja e Best/Least Seller
        sorted_products = sorted(product_stats.values(), key=lambda x: x['qty'], reverse=True)
        best_seller = sorted_products[0] if sorted_products else None
        least_seller = sorted_products[-1] if sorted_products else None

        return {
            'doc_ids': docids,
            'doc_model': 'restaurant.report.wizard',
            'data': data,
            'docs': lines,
            'total_sales': total_sales,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'best_seller': best_seller,
            'least_seller': least_seller,
            'company': self.env.company,
        }
