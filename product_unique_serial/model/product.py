# coding: utf-8
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2007-2015 (<https://vauxoo.com>).
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
##############################################################################

from openerp import fields, models, api, _
from openerp.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    lot_unique_ok = fields.Boolean('Unique lot',
                                   help='Forces set qty=1 '
                                        'to specify a Unique '
                                        'Serial Number for '
                                        'all moves')

    @api.multi
    @api.constrains('lot_unique_ok', 'track_all')
    def _check_not_moves_unique_lot(self):
        for prod in self:
            prod_ids = prod._get_products()
            move_obj = self.env['stock.move']
            if (prod.track_all or prod.lot_unique_ok) and\
                    move_obj.search([('product_id', 'in', prod_ids)]):
                raise ValidationError(_(
                    "You can't activate 'full lots traceability' or 'unique "
                    "lot' in the product %s because this product already "
                    "have stock movements." % prod.name))
