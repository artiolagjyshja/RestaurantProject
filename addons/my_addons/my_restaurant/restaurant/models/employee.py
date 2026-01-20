# -*- coding: utf-8 -*-

from odoo import fields, models

class RestaurantEmployee(models.Model):
    _name = 'restaurant.employee'
    _description = 'Employee'
    _rec_name = 'employee_name'

    employee_name = fields.Char(string='Employee name', required=True)
    role = fields.Selection([
           ('manager', 'Manager'),
           ('waiter', 'Waiter')
      ], string='Position', default='waiter', required=True)
    phone = fields.Char(string='Phone number')
    email = fields.Char(string='Email Address')
    address = fields.Text(string='Address')
    salary = fields.Float(string='Salary', digits=(12,4))
    hiring_date = fields.Datetime(string='Hiring date', required=True)
    is_active = fields.Boolean(string='Active', default=True)
    user_id = fields.Many2one('res.users', string='Related User')



    order_ids = fields.One2many(comodel_name='restaurant.order', inverse_name = 'employee_id', string='Taken Orders')










