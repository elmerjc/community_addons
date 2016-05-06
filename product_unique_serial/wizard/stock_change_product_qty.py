# coding: utf-8
############################################################################
#    Module Writen For Odoo, Open Source Management Solution
#
#    Copyright (c) 2015 Vauxoo - http://www.vauxoo.com
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
#    coded by: Luis Torres <luis_t@vauxoo.com>
############################################################################
from openerp import models, api, _
from openerp.exceptions import ValidationError


class StockChangeProductQty(models.TransientModel):
    _inherit = 'stock.change.product.qty'

    @api.multi
    def change_product_qty(self):
        for wiz in self:
            if wiz.product_id.track_all and not wiz.lot_id:
                raise ValidationError(_(
                    'The product %s has active "Full Lots Traceability", you '
                    'must assign the serial number to update the quantity.'
                    % wiz.product_id.name))
        return super(StockChangeProductQty, self).change_product_qty()
