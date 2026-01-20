# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


# =========================== ORDERS =================================
class RestaurantOrder(models.Model):
    _name = 'restaurant.order'
    _description = 'Restaurant Orders'
    _rec_name = 'name'

    name = fields.Char(
        string='Order Code',
        required=True,
        readonly=True,
        copy=False,
        default='/'
    )

    date_time = fields.Datetime(
        string='Created DateTime',
        default=lambda self: fields.Datetime.now()
    )

    state = fields.Selection([
        ('new', 'New'),
        ('in_preparation', 'In Preparation'),
        ('ready', 'Ready'),
        ('served', 'Served')
    ], string='Status', default='new', required=True)

    note = fields.Text(string='Extra Notes')

    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True
    )

    alarm_table_ids = fields.One2many('restaurant.alarm.table', 'order_id', string='Alarme Tavoline')
    
    def _default_employee(self):
        return self.env['restaurant.employee'].search([('user_id', '=', self.env.user.id)], limit=1)

    employee_id = fields.Many2one('restaurant.employee', string='Employee', default=_default_employee, readonly=True)

    table_id = fields.Many2one('restaurant.table', string='Table', domain="[('status','=','free')]")

    invoice_id = fields.Many2one('restaurant.invoice', string='Invoice')

    orders_line_ids = fields.One2many('restaurant.order.lines', 'order_id', string='Order Lines')

    # ---------------- COMPUTE TOTAL ----------------
    # ---------------- COMPUTE TOTAL ----------------
    @api.depends('orders_line_ids.subtotal')
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = sum(line.subtotal for line in order.orders_line_ids)

    @api.onchange('date_time')
    def _onchange_date_time(self):
        # Kur ndryshon data/ora në prind, detyrojmë llogaritjen e linjave me kohën e RE
        target_dt = self.date_time or fields.Datetime.now()
        for line in self.orders_line_ids:
            if not line.product_id: 
                continue
            # Përdorim logjikën e përbashkët duke i kaluar kohën specifike
            price = line._get_discounted_price(line.product_id, line.quantity, target_dt)
            line.price = price
            line.subtotal = price * line.quantity

    # ---------------- CREATE ORDER ----------------
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = str(self.search_count([]) + 1)

        order = super().create(vals)

        if order.table_id:
            if order.table_id.status != 'free':
                raise UserError("Tavolina është e zënë!")

            order.table_id.write({
                'status': 'taken',
                'current_order_id': order.id,
                'current_waiter_id': order.employee_id.id
            })

        return order

    def unlink(self):
        for order in self:
            if order.table_id:
                order.table_id.write({
                    'status': 'free',
                    'current_order_id': False,
                    'current_waiter_id': False
                })
        return super(RestaurantOrder, self).unlink()

    # ---------------- STATES ----------------
    def action_confirm(self):
        for order in self:
            order.state = 'in_preparation'

    def action_set_ready(self):
        for order in self:
            order.state = 'ready'

    def action_serve_order(self):
        for order in self:
            if order.state != 'ready':
                raise UserError("Porosia duhet të jetë READY!")

            # Zbritje stoku
            for line in order.orders_line_ids:
                if line.product_id.product_type != 'service':
                    if line.product_id.is_composite:
                        line.product_id.update_component_stock(line.quantity)
                    else:
                        line.product_id.quantity_available -= line.quantity

            order.state = 'served'

            if order.table_id:
                order.table_id.write({
                    'status': 'free',
                    'current_order_id': False,
                    'current_waiter_id': False
                })

    def action_create_invoice(self):
        for order in self:
            if order.state != 'served':
                raise UserError("Porosia duhet të jetë SERVED!")

            # Rifresko çmimet e rreshtave të porosisë
            for line in order.orders_line_ids:
                line._compute_prices()

            invoice = self.env['restaurant.invoice'].create({
                'invoice_code': order.name,
                'invoice_date': fields.Datetime.now(),
                'employee_id': order.employee_id.id,
                'table_id': order.table_id.id,
                'final_total_amount': order.total_amount,
                'order_ids': [(6, 0, [order.id])]
            })

            order.invoice_id = invoice.id

            return {
                'type': 'ir.actions.act_window',
                'name': 'Fatura',
                'view_mode': 'form',
                'res_model': 'restaurant.invoice',
                'res_id': invoice.id,
            }

# ======================= ORDER LINES =================================
class OrderLines(models.Model):
    _name = 'restaurant.order.lines'
    _description = 'Order Line'

    order_id = fields.Many2one('restaurant.order', string='Order', ondelete='cascade')
    product_id = fields.Many2one('restaurant.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)

    # Shtojmë varësinë te fields.Datetime.now() indirekt përmes një fushe nëse duhet,
    # por kryesorja është lidhja me produktin
    price = fields.Float(string='Price', compute='_compute_prices', store=True, readonly=False)
    cost_price = fields.Float(string='Cost Price', compute='_compute_prices', store=True)
    subtotal = fields.Float(string='Subtotal', compute='_compute_prices', store=True)

    def _get_discounted_price(self, product, quantity, date_time):
        """
        Llogarit çmimin duke marrë parasysh ofertat në një kohë specifike.
        Kjo metodë nuk varet nga self.order_id, kështu që mund të thirret nga onchange.
        """
        if not product:
            return 0.0

        base_price = product.sale_price
        discount = 0.0

        # Përcaktimi i kohës së saktë (Lokal)
        # Nëse date_time është None, marrim Tani
        check_dt = date_time or fields.Datetime.now()
        
        # Përdorim context_timestamp për të kthyer kohën e serverit (UTC) në kohën e përdoruesit
        order_local = fields.Datetime.context_timestamp(self, check_dt)
        current_hour = order_local.hour + order_local.minute / 60.0

        # Gjejmë ofertat - Mënyra më e sigurt për Many2many
        offers = self.env['restaurant.offers'].search([
            ('product_ids', 'in', product.ids)
        ])

        for offer in offers:
            if offer.offer_type == 'seasonal':
                # Krahasimi i datave (Kthejmë në local për krahasim të drejtë)
                off_start = fields.Datetime.context_timestamp(self, offer.start_time) if offer.start_time else None
                off_end = fields.Datetime.context_timestamp(self, offer.end_time) if offer.end_time else None

                if off_start and off_end and off_start <= order_local <= off_end:
                    discount = max(discount, offer.discount_percent)

            elif offer.offer_type == 'permanent':
                if offer.start_hour <= current_hour <= offer.end_hour:
                    discount = max(discount, offer.discount_percent)

        # Llogaritja finale
        final_price = base_price * (1 - (discount / 100.0))
        return final_price

    @api.depends('product_id', 'quantity', 'order_id.date_time')
    def _compute_prices(self):
        for line in self:
            # Në compute standard, përpiqemi të marrim kohën nga order_id
            # Nëse order_id nuk ekziston (rasti NewId pa lidhje), marrim kohën aktuale
            # Ose nëse po thirret nga onchange i prindit, vlera tashmë është vendosur manualisht atje.
            
            # Shënim: Kur thirret nga onchange_product_id, line.order_id mund të jetë bosh.
            # Në atë rast, do përdoret 'now()', që mund të jetë gabim nëse useri ka ndryshuar orën.
            # Zgjidhja është që useri të ndryshojë orën OSE të mbështetemi te onchange i prindit.
            dt = line.order_id.date_time or fields.Datetime.now()
            
            line.price = line._get_discounted_price(line.product_id, line.quantity, dt)
            line.cost_price = line.product_id.purchase_price
            line.subtotal = line.price * line.quantity

    @api.onchange('product_id', 'quantity')
    def _onchange_refresh_price(self):
        # Detyrojmë llogaritjen menjëherë në UI
        # Këtu mund të mos kemi akses te prindi nëse është krijim i ri
        self._compute_prices()