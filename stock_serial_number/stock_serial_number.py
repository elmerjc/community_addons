# -*- coding: utf-8 -*-
##############################################################################
#
#    Elneo
#    Copyright (C) 2011-2015 Elneo (Technofluid SA) (<http://www.elneo.com>).
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

from openerp import models,fields,api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    unique_serial_number = fields.Boolean("Unique Serial Number",help="When using tracking outgoing/incoming lots/serial numbers, moves will be split into unique quantities to enter the serial number")

class StockTransferDetails(models.TransientModel):
    _inherit = 'stock.transfer_details'

    #serial_number = fields.Char("Serial number", size=255)
    
    @api.model
    def default_get(self,fields):
        res = super(StockTransferDetails,self).default_get(fields=fields)
        if not res.has_key('item_ids'):
            return res
        
        for key, value in res.iteritems():
            if key != 'item_ids':
                continue
            
            res_items=[]
            for item in value:
                split=False
                product = self.env['product.product'].browse(item['product_id'])
                dest = self.env['stock.location'].browse(item['destinationloc_id'])
                src = self.env['stock.location'].browse(item['sourceloc_id'])
                if product.unique_serial_number and product.track_all and not dest.usage == 'inventory':
                    split = True
                if product.unique_serial_number and product.track_incoming and src.usage in ('supplier', 'transit', 'inventory') and dest.usage == 'internal':
                    split=True
                if product.unique_serial_number and product.track_outgoing and dest.usage in ('customer', 'transit') and src.usage == 'internal':
                    split=True
            
                if split:
                    items = self._split_quantities(item)
                    res_items.extend(items)
                    
                else:
                    res_items.append(item)
            
            res.update({'item_ids':res_items})
            
        return res
    
    @api.model
    def _split_quantities(self,item):
        res=[]
        if item['quantity']>1:
            item['quantity'] = (item['quantity']-1)
            new_item = item.copy()
            new_item['quantity'] = 1
            new_item['packop_id'] = False
            res.append(new_item)
            res.extend(self._split_quantities(item))
        else:
            res.append(item)
        
        return res
