# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class RestaurantOffers(models.Model):
    _name = 'restaurant.offers'
    _description = 'Oferta e Restorantit'
    _rec_name = 'name'

    name = fields.Char(string='Emri i Ofertës', required=True)
    offer_type = fields.Selection([
        ('seasonal', 'Sezonale (Me Data)'),
        ('permanent', 'E Përhershme (Vetëm Orari)')
    ], string='Lloji i Ofertës', default='seasonal', required=True)

    # Fushat për ofertat sezonale
    start_time = fields.Datetime(string='Data Fillimit')
    end_time = fields.Datetime(string='Data Mbarimit')

    # Fushat e reja për orarin e përhershëm (zgjidhja për profesorin)
    start_hour = fields.Float(string='Nga Ora', default=8.0)
    end_hour = fields.Float(string='Deri në Orën', default=10.0)

    discount_percent = fields.Float(string='Ulja (%)', digits=(16, 2))
    product_ids = fields.Many2many(comodel_name='restaurant.product', string='Produktet')

    @api.constrains('start_time', 'end_time', 'start_hour', 'end_hour', 'product_ids', 'offer_type')
    def _check_overlap(self):
        for offer in self:
            # 1. Validimi i logjikës së kohës brenda rekordit
            if offer.offer_type == 'seasonal':
                if not offer.start_time or not offer.end_time:
                    raise ValidationError("Për ofertat sezonale kërkohen datat e fillimit dhe mbarimit!")
                if offer.start_time >= offer.end_time:
                    raise ValidationError("Data e mbarimit duhet të jetë pas fillimit!")
            else:
                if offer.start_hour >= offer.end_hour:
                    raise ValidationError("Ora e mbarimit duhet të jetë pas orës së fillimit!")

            # 2. Kontrolli për mbivendosje me oferta të tjera për të njëjtat produkte
            domain = [
                ('id', '!=', offer.id),
                ('product_ids', 'in', offer.product_ids.ids),
                ('offer_type', '=', offer.offer_type)
            ]

            overlapping_offers = self.search(domain)
            for other in overlapping_offers:
                is_overlap = False
                if offer.offer_type == 'seasonal':
                    if (offer.start_time < other.end_time) and (offer.end_time > other.start_time):
                        is_overlap = True
                else:
                    if (offer.start_hour < other.end_hour) and (offer.end_hour > other.start_hour):
                        is_overlap = True

                if is_overlap:
                    raise ValidationError(
                        f"Produkti ka një ofertë tjetër aktive ('{other.name}') gjatë këtij orari/peridhe!")