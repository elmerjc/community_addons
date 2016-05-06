# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2013-Present Acespritech Solutions Pvt. Ltd. (<http://acespritech.com>).
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

from openerp.osv import fields, osv, orm
from openerp import models, api


class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        result = super(stock_transfer_details, self).fields_view_get(cr, uid, view_id,
                                        view_type, context, toolbar, submenu)
        return result

    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_transfer_details, self).default_get(cr, uid, fields, context=context)
        if context is None: context = {}
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')
        pos_order_pool = self.pool.get('pos.order')
        stock_pack_pool = self.pool.get('stock.pack.operation')
        pos_ids = pos_order_pool.search(cr, uid, [('picking_id', '=', picking_ids[0])])
#
        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        items = []
        packs = []
        if not picking.pack_operation_ids:
            picking.do_prepare_partial()
# CUSTOM CODE TRY
        if pos_ids:
            pack_op_ids = [x.id for x in picking.pack_operation_ids]
            for each_line in pos_order_pool.browse(cr, uid, pos_ids[0]).lines:
                line_product_id = each_line.product_id.id
                line_lot_id = each_line.prodlot_id.id
                if line_lot_id:
                    for each_op in picking.pack_operation_ids:
                            if each_op.product_id.id == line_product_id:
                                if not each_op.lot_id:
                                    stock_pack_pool.write(cr, uid, each_op.id, {'lot_id': line_lot_id})
                                    break
  
# CUSTOME CODE TRY
        for op in picking.pack_operation_ids:
            item = {
                'packop_id': op.id,
                'product_id': op.product_id.id,
                'product_uom_id': op.product_uom_id.id,
                'quantity': op.product_qty,
                'package_id': op.package_id.id,
                'lot_id': op.lot_id.id,
                'sourceloc_id': op.location_id.id,
                'destinationloc_id': op.location_dest_id.id,
                'result_package_id': op.result_package_id.id,
                'date': op.date,
                'owner_id': op.owner_id.id,
            }
            if op.product_id:
                items.append(item)
            elif op.package_id:
                packs.append(item)
        res.update(item_ids=items)
        res.update(packop_ids=packs)
        return res

class stock_production_lot(osv.osv):
    _inherit = 'stock.production.lot'
    
    def check_stock_lot_new(self, cr, uid, ids, name, arg, context=None):
        '''
            To check the Quantity of products left in this lot
        '''
        res = {}
        for lot in self.browse(cr, uid, ids):
            res[lot.id] = {}
            total = 0
            incoming_qty = 0
            outgoing_qty = 0
            for quant in lot.quant_ids:
                if quant.location_id and quant.location_id.usage and quant.location_id.usage == "internal":
                    total += quant.qty
            res[lot.id] = total
        return res

    _columns = {
        'name': fields.char('Serial Number', required=True, help="Unique Serial Number"),
        'available_stock': fields.function(check_stock_lot_new, type='float', string='Available Stock', store=False)
    }
    
    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if context is None:
            context = {}
        res = super(stock_production_lot, self).name_search(cr, uid, name, args=args, operator='ilike', context=context)
        if context.get("block_old"):
            return []
        return res

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if context.get("block_old"):
            sr_name = vals.get('name')
            if sr_name:
                all_lots = self.search(cr, uid, [])
                all_lot_name = [x.name.strip() for x in self.browse(cr, uid, all_lots)]
                if vals.get('name').strip() in all_lot_name:
                    raise osv.except_osv(('Duplicate Lot Name'),
                                         ("This Lot Number is already generated, please change the lot number"))
        ret_val = super(stock_production_lot, self).create(cr, uid, vals, context)
        return ret_val

    def check_stock_lot(self, cr, uid, lot_id, context=None):
        '''
            To check the Quantity of products left in this lot
        '''
        if context is None:
            context = {}
        pack_obj = self.pool.get('stock.pack.operation')
        pack_ids = pack_obj.search(cr, uid, [('lot_id', '=', lot_id)])
        if pack_ids:
            incoming_qty = 0
            outgoing_qty = 0
            for pack in pack_obj.browse(cr, uid, pack_ids):
                if pack.picking_id and pack.picking_id.state == "done" and pack.picking_id.picking_type_id:
                    if pack.picking_id.picking_type_id.code == "incoming":
                        incoming_qty += pack.product_qty
                    if pack.picking_id.picking_type_id.code == "outgoing":
                        outgoing_qty += pack.product_qty
            return incoming_qty - outgoing_qty
        return 0

    _sql_constraints = [('lot_name_uniq', 'unique(name)', 'Serial No. must be unique!'),
    ]

class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def _prepare_pack_ops(self, cr, uid, picking, quants, forced_qties, context=None):
        """ returns a list of dict, ready to be used in create() of stock.pack.operation.
  
        :param picking: browse record (stock.picking)
        :param quants: browse record list (stock.quant). List of quants associated to the picking
        :param forced_qties: dictionary showing for each product (keys) its corresponding quantity (value) that is not covered by the quants associated to the picking
        """
        def _picking_putaway_apply(product):
            location = False
            # Search putaway strategy
            if product_putaway_strats.get(product.id):
                location = product_putaway_strats[product.id]
            else:
                location = self.pool.get('stock.location').get_putaway_strategy(cr, uid, picking.location_dest_id, product, context=context)
                product_putaway_strats[product.id] = location
            return location or picking.location_dest_id.id
  
        pack_obj = self.pool.get("stock.quant.package")
        quant_obj = self.pool.get("stock.quant")
        product_obj = self.pool.get("product.product")
        vals = []
        qtys_grouped = {}
        # for each quant of the picking, find the suggested location
        quants_suggested_locations = {}
        product_putaway_strats = {}
        for quant in quants:
            if quant.qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(quant.product_id)
            quants_suggested_locations[quant] = suggested_location_id
  
        # find the packages we can movei as a whole
        top_lvl_packages = self._get_top_level_packages(cr, uid, quants_suggested_locations, context=context)
        # and then create pack operations for the top-level packages found
        for pack in top_lvl_packages:
            pack_quant_ids = pack_obj.get_content(cr, uid, [pack.id], context=context)
            pack_quants = quant_obj.browse(cr, uid, pack_quant_ids, context=context)
            vals.append({
                    'picking_id': picking.id,
                    'package_id': pack.id,
                    'product_qty': 1.0,
                    'location_id': pack.location_id.id,
                    'location_dest_id': quants_suggested_locations[pack_quants[0]],
                })
            # remove the quants inside the package so that they are excluded from the rest of the computation
            for quant in pack_quants:
                del quants_suggested_locations[quant]
  
        # Go through all remaining reserved quants and group by product, package, lot, owner, source location and dest location
        for quant, dest_location_id in quants_suggested_locations.items():
            key = (quant.product_id.id, quant.package_id.id, quant.lot_id.id, quant.owner_id.id, quant.location_id.id, dest_location_id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += quant.qty
            else:
                qtys_grouped[key] = quant.qty
  
        # Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
        for product, qty in forced_qties.items():
            if qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(product)
            key = (product.id, False, False, False, picking.location_id.id, suggested_location_id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += qty
            else:
                qtys_grouped[key] = qty
# CUSTOM CODE
        # Create the necessary operations for the grouped quants and remaining qtys
        for key, qty in qtys_grouped.items():
            product_brw = product_obj.browse(cr, uid, key[0], context=context)
            if product_brw.track_all or product_brw.track_incoming:
                if qty > 1:
                    for each_qty in range(int(qty)):
                        vals.append({
                        'picking_id': picking.id,
                        'product_qty': 1,
                        'product_id': key[0],
                        'package_id': key[1],
                        'lot_id': key[2],
                        'owner_id': key[3],
                        'location_id': key[4],
                        'location_dest_id': key[5],
                        'product_uom_id': product_brw.uom_id.id,
                    })
                else:
                    vals.append({
                    'picking_id': picking.id,
                    'product_qty': 1,
                    'product_id': key[0],
                    'package_id': key[1],
                    'lot_id': key[2],
                    'owner_id': key[3],
                    'location_id': key[4],
                    'location_dest_id': key[5],
                    'product_uom_id': product_brw.uom_id.id,
                })
            else:
                vals.append({
                    'picking_id': picking.id,
                    'product_qty': qty,
                    'product_id': key[0],
                    'package_id': key[1],
                    'lot_id': key[2],
                    'owner_id': key[3],
                    'location_id': key[4],
                    'location_dest_id': key[5],
                    'product_uom_id': product_brw.uom_id.id,
                })
        return vals
