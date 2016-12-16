#########################################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP SA (<http://www.odoo.com>)
#    Copyright (C) 2014-TODAY Abdallah Mohammed (<abdalla_mohammed@outlook.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################################

from openerp import models, fields, api, _


class crm_stage(models.Model):
    _inherit = 'crm.case.stage'

    calculate_probability = fields.Selection(string="Calculate probability method",
                                             selection=[('stage', 'Stage'), ('manual', 'Manual'),
                                                        ('expected_sell', 'Expected Sell'),
                                                        ], required=True,
                                             default="expected_sell", )

    on_change = fields.Boolean(string='Change Probability Automatically', compute='onchange_calculate_probability',
                               help="Setting this stage will change the probability automatically on the opportunity.",
                               default=False)

    @api.depends('calculate_probability')
    @api.model
    def onchange_calculate_probability(self):
        if self.calculate_probability == 'stage':
            self.on_change = True
        else:
            self.on_change = False


class crm_products(models.Model):
    _name = 'crm.products'
    _rec_name = 'name'
    _description = 'CRM Products'

    category_id = fields.Many2one(comodel_name="product.category", string="Product Category", required=True, )
    product_id = fields.Many2one(comodel_name="product.product", string="Product", required=True, )
    name = fields.Text(string="Description", required=True)
    crm_lead_id = fields.Many2one(comodel_name="crm.lead", string="Lead / Opportunity", required=False, )
    quantity = fields.Float(string="Quantity", required=True, default=1)
    product_price = fields.Float(string="Sales Price", required=False, )
    product_cost_price = fields.Float(string="Cost Price", required=False, )
    total_product_cost_price = fields.Float(string="Total Cost Price", required=False, )
    total_price = fields.Float(string="Total price", compute="update_total_price", store=True)
    margin = fields.Float(string="Margin", required=False, )
    expected_sell = fields.Integer(string="Expected Sell (%)", required=True, default=0)

    @api.multi
    @api.onchange('product_id')
    def update_price_name(self):
        for record in self:
            record.product_price = record.product_id.lst_price
            record.product_cost_price = record.product_id.standard_price

            name = record.product_id.display_name
            if record.product_id.description_sale:
                record.name = name + '\n' + record.product_id.description_sale
            else:
                record.name = name

    @api.depends('quantity', 'product_price')
    @api.multi
    def update_total_price(self):
        for record in self:
            record.total_price = record.product_price * record.quantity
            record.total_product_cost_price = record.product_cost_price * record.quantity
            record.margin = record.total_price - record.total_product_cost_price


class crm_lead_product(models.Model):
    _inherit = 'crm.lead'

    product_ids = fields.One2many(comodel_name="crm.products", inverse_name="crm_lead_id", string="Product",
                                  required=False, )
    planned_revenue = fields.Float(string="Expected Revenue", compute='calculate_revenue', store=True)
    planned_cost = fields.Float(string="Planned Costs", compute='calculate_costs', store=True)
    margin = fields.Float(string="Margin", required=False, compute='calculate_margin', store=True)

    @api.depends('product_ids.total_price')
    @api.multi
    def calculate_revenue(self):
        for order in self:
            for record in order.product_ids:
                order.planned_revenue += record.total_price

    @api.depends('product_ids.total_product_cost_price')
    @api.multi
    def calculate_costs(self):
        for order in self:
            for record in order.product_ids:
                order.planned_cost += record.total_product_cost_price

    @api.depends('product_ids.margin')
    @api.multi
    def calculate_margin(self):
        for order in self:
            for record in order.product_ids:
                order.margin += record.margin

    # @api.onchange('product_ids', 'stage_id')
    @api.onchange('product_ids', 'stage_id')
    @api.multi
    def onchange_product_ids(self):
        for reccord in self:
            total_expected_sell = sum([p.expected_sell for p in reccord.product_ids])
            if self.stage_id:
                if self.stage_id.calculate_probability == 'expected_sell':
                    self.probability = total_expected_sell
                if self.stage_id.calculate_probability == 'stage':
                    self.probability = self.stage_id.probability
            else:
                pass
