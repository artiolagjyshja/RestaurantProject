from odoo import fields, models

class RestaurantCategory(models.Model):
    _name = 'restaurant.category'
    _description = 'Category'
    _rec_name = 'category_name'

    category_name = fields.Char(string='Category name', required=True)

    product_ids = fields.Many2many(comodel_name='restaurant.product', string='Product')


