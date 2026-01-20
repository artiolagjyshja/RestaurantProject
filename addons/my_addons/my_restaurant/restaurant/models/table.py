from odoo import fields, models, api


class RestaurantTable(models.Model):
    _name = 'restaurant.table'
    _description = 'Tavolinat e Restorantit'
    _rec_name = 'tableNumber'
    _order = 'tableNumber asc'

    tableNumber = fields.Integer(string='Table Number', required=True)
    status = fields.Selection([
        ('free', 'Free'),
        ('taken', 'Taken')
    ], string='Status', default='free', required=True)

    number_of_seats = fields.Integer(string='Number of seats', required=True, default=2)
    location = fields.Selection([
        ('inside', 'In'),
        ('outside', 'Out'),
        ('bar', 'Bar')
    ], string='Location', default='inside')

    current_waiter_id = fields.Many2one('restaurant.employee', string='Current Waiter')

    # Kjo fushë do të gjejë automatikisht porosinë e hapur për këtë tavolinë
    current_order_id = fields.Many2one(
        'restaurant.order',
        string='Active Order',
        compute='_compute_current_order'
    )

    order_ids = fields.One2many('restaurant.order', 'table_id', string='Orders')
    alarm_table_ids = fields.One2many('restaurant.alarm.table', 'table_id', string='Table alarms')

    @api.depends('order_ids', 'order_ids.state')
    def _compute_current_order(self):
        for rec in self:
            # Kërkojmë porosinë e fundit që nuk është 'served' (e përfunduar)
            active_order = rec.order_ids.filtered(lambda o: o.state != 'served')
            rec.current_order_id = active_order[0] if active_order else False