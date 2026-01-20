# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import UserError


class RestaurantInvoice(models.Model):
    _name = 'restaurant.invoice'
    _description = 'Restaurant Invoice'
    _rec_name = 'invoice_code'

    invoice_type = fields.Selection(string='Invoice Type',
                                    selection=[('summary', 'Summary'),
                                               ('tax', 'TAX')],
                                    default='tax')

    invoice_date = fields.Datetime(string='Invoice Date', default=lambda self: fields.Datetime.now())

    # readonly=True dhe default='New' që të mos kesh errore gjatë save-it të parë
    invoice_code = fields.Char(string='Invoice Number', required=True, readonly=True, copy=False, default='New')

    final_total_amount = fields.Float(string='Total amount', compute='_compute_amounts', store=True)
    suggested_tip = fields.Float(string='Suggested Tip (10%)', compute='_compute_amounts', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid'),
        ('done', 'Done')
    ], string='Invoice Status', default='draft')

    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'POS')], string='Payment method')

    employee_id = fields.Many2one('restaurant.employee', string='Employee', readonly=True)
    table_id = fields.Many2one('restaurant.table', string='Table', readonly=True)

    order_ids = fields.One2many(comodel_name='restaurant.order', inverse_name='invoice_id', string='Source Orders')

    invoice_item_ids = fields.Many2many(
        comodel_name='restaurant.order.lines',
        string='Detajet e Produkteve',
        compute='_compute_invoice_items'
    )

    # --- METODAT COMPUTE ---

    @api.depends('order_ids', 'order_ids.orders_line_ids')
    def _compute_invoice_items(self):
        """Kjo metodë lidh rreshtat e porosive me faturën"""
        for invoice in self:
            # Marrim të gjitha ID-të e rreshtave nga porositë e lidhura
            line_ids = invoice.order_ids.mapped('orders_line_ids').ids
            if line_ids:
                invoice.invoice_item_ids = [(6, 0, line_ids)]
            else:
                invoice.invoice_item_ids = [(5, 0, 0)]

    @api.depends('invoice_item_ids', 'order_ids.alarm_table_ids')
    def _compute_amounts(self):
        for rec in self:
            # 1. Shuma e produkteve (kodi që kemi bërë më parë)
            product_total = sum(line.subtotal for line in rec.invoice_item_ids)

            # 2. Shuma e alarmeve të lidhura me porositë e kësaj fature
            # Marrim të gjitha porositë e faturës dhe mbledhim koston e alarmeve të tyre
            alarm_total = sum(
                rec.order_ids
                .mapped('alarm_table_ids')
                .filtered(lambda a: a.state == 'solved')
                .mapped('alarm_cost')
            )

            # 3. Totali Final
            rec.final_total_amount = product_total + alarm_total
            rec.suggested_tip = rec.final_total_amount * 0.10

    # --- VEPRIMET (ACTIONS) ---

    def action_confirm(self):
        """Kalon faturën në gjendjen Done"""
        for rec in self:
            if not rec.invoice_item_ids:
                raise UserError("Nuk mund të konfirmoni një faturë pa produkte!")
            rec.state = 'done'

    def action_set_paid(self):
        for invoice in self:
            invoice.state = 'paid'

            # Markojmë alarmet si të faturuara
            alarms = invoice.order_ids.mapped('alarm_table_ids') \
                .filtered(lambda a: a.state == 'solved')

            alarms.write({'state': 'invoiced'})

    # --- OVERRIDES (CREATE/UNLINK) ---

    @api.model
    def create(self, vals):
        """Gjeneron numrin e faturës automatikisht"""
        if vals.get('invoice_code', 'New') == 'New':
            # Sigurohu që ke krijuar një sekuencë me këtë kod në Odoo
            seq = self.env['ir.sequence'].next_by_code('restaurant.invoice')
            vals['invoice_code'] = seq or 'New'
        return super(RestaurantInvoice, self).create(vals)

    def unlink(self):
        """Parandalon fshirjen nëse nuk është Draft"""
        for invoice in self:
            if invoice.state != 'draft':
                raise UserError('Vetëm faturat në gjendje "Draft" mund të fshihen!')
        return super(RestaurantInvoice, self).unlink()