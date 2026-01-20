from odoo import fields, models, api

class RestaurantProduct(models.Model):
    _name = 'restaurant.product'
    _description = 'Product'
    _rec_name = 'product'


    product = fields.Char(string='Product Name', required=True)
    purchase_price = fields.Float(string='Purchase Price', digits=(12, 4))
    sale_price = fields.Float(string='Sale Price', digits=(12, 4), default=0.0)
    product_type = fields.Selection([
        ('dish', 'Pjatë'),
        ('drink', 'Pije'),
        ('raw_material', 'Lëndë e Parë'),
        ('service', 'Shërbim')],
        string='Product Type', required=True, default='drink')
    quantity_available = fields.Float(string='Quantity Available', digits=(12, 2), default=0.0)
    is_available = fields.Boolean(string='Available in Menu', default=True)
    minimum_stock_level = fields.Float(string='Minimum stock level', digits=(12, 2), default=0.0)
    is_composite = fields.Boolean(string='Is Menu Combo?', default=False, help="Nese eshte e selketuar, ky produkt do te konsiderohet si nje perzierje artikujsh te tjere ")

    # Fusha që mbledh vlerën reale të përbërësve pa ulje
    total_components_price = fields.Float(
        string='Vlera Totale (pa ulje)',
        compute='_compute_combo_savings',
        store=True
    )

    # Fusha që llogarit kursimin/uljen në përqindje
    discount_rate = fields.Float(
        string='Ulja e Kombos (%)',
        compute='_compute_combo_savings',
        store=True
    )


    category_ids = fields.Many2many(comodel_name='restaurant.category', string='Category')

    offers_ids = fields.Many2many(comodel_name='restaurant.offers', string='Offers')


    menu_ids = fields.One2many(
        comodel_name='restaurant.composite.product',
        inverse_name='parent_product_id',
        string='Composite Products')

    order_lines_ids = fields.One2many(
        comodel_name='restaurant.order.lines',
        inverse_name='product_id',
        string='Order Lines')

    #metoda per stokun
    def update_component_stock(self, ordered_qty):
        #zbret stokun e perberesve per produktin comp
        for line in self.menu_ids:
            if line.component_id:
                deduction_qty = line.quantity * ordered_qty

                #kontroll nese kemi stok mjaftueshem te perberesi
                if line.component_id.product_type != 'service':
                    line.component_id.quantity_available -= deduction_qty

                if line.component_id.quantity_available < line.component_id.minimum_stock_level:
                    pass

    @api.depends('is_composite', 'menu_ids.price', 'menu_ids.quantity', 'sale_price')
    def _compute_combo_savings(self):
        for rec in self:
            if rec.is_composite and rec.menu_ids:
                # 1. Llogarisim sa do kushtonin produktet veç e veç
                total = sum(line.price * line.quantity for line in rec.menu_ids)
                rec.total_components_price = total

                # 2. Llogarisim përqindjen e uljes bazuar te Sale Price që vendos ti
                if total > 0 and rec.sale_price < total:
                    rec.discount_rate = ((total - rec.sale_price) / total) * 100
                else:
                    rec.discount_rate = 0.0
            else:
                rec.total_components_price = 0.0
                rec.discount_rate = 0.0

    # Modifikojmë çmimin: E bëjmë që të llogaritet automatikisht vetëm herën e parë
    @api.onchange('is_composite', 'menu_ids')
    def _onchange_combo_price(self):
        if self.is_composite and self.menu_ids:
            self.sale_price = sum(line.price * line.quantity for line in self.menu_ids)

class RestaurantCompositeProduct(models.Model):
    _name = 'restaurant.composite.product'
    _description = 'Composite Product (Menu Combo)'

    parent_product_id = fields.Many2one(
        comodel_name='restaurant.product',
        string='Composite Product')

    component_id = fields.Many2one(
        comodel_name='restaurant.product',
        string='Product of Menu')

    quantity = fields.Integer(string='Quantity', default=1)
    price = fields.Float(string='Price', digits=(16, 2))

    @api.onchange('component_id')
    def _onchange_component_id(self):
        if self.component_id:
            self.price = self.component_id.sale_price
