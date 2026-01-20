from odoo import models, fields, api

class SalesReportWizard(models.TransientModel):
    _name = 'restaurant.report.wizard'
    _description = 'Restaurant Sales Report Wizard'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    employee_id = fields.Many2one('restaurant.employee', string='Employee (Optional)')

    def action_print_report(self):
        self.ensure_one()
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'employee_id': self.employee_id.id if self.employee_id else False,
            'employee_name': self.employee_id.employee_name if self.employee_id else 'All Employees'
        }
        return self.env.ref('restaurant.action_report_sales').report_action(None, data=data)
