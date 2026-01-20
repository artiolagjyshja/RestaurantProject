from odoo import fields, models, api

class RestaurantAlarmTable(models.Model):
    _name = 'restaurant.alarm.table'
    _description = 'Thirrjet e Alarmeve'

    # Përdor fields.Datetime.now për konsistencë me serverin
    start_time = fields.Datetime(
        string='Koha e Thirrjes',
        default=fields.Datetime.now,
        readonly=True
    )
    end_time = fields.Datetime(string='Koha e Zgjidhjes', readonly=True)

    order_id = fields.Many2one('restaurant.order', string='Porosia Aktive', readonly=True)
    table_id = fields.Many2one('restaurant.table', string='Tavolina', required=True)

    alarm_cost = fields.Float(string='Kosto Alarmi', default=10.0, readonly=True)

    state = fields.Selection([
        ('active', 'Aktiv'),
        ('solved', 'I Zgjidhur'),
        ('invoiced', 'I Faturuar')
    ], string="Statusi", default='active', readonly=True)

    def action_solve(self):
        """Mbyll alarmin dhe regjistron kohën e përfundimit"""
        for rec in self:
            if rec.state == 'active':
                rec.write({
                    'state': 'solved',
                    'end_time': fields.Datetime.now() # Përdor fields.Datetime këtu
                })

    @api.model
    def create(self, vals):
        if vals.get('table_id') and not vals.get('order_id'):
            # Kërkojmë porosinë më të fundit të hapur për këtë tavolinë
            active_order = self.env['restaurant.order'].search([
                ('table_id', '=', vals.get('table_id')),
                ('state', '!=', 'served')
            ], limit=1, order='create_date desc')

            if active_order:
                vals['order_id'] = active_order.id

        return super(RestaurantAlarmTable, self).create(vals)