# coding: utf-8
###########################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#
#    Copyright (c) 2010 Vauxoo - http://www.vauxoo.com/
#    All Rights Reserved.
#    info Vauxoo (info@vauxoo.com)
############################################################################
#    Coded by: Vauxoo Consultores (info@vauxoo.com)
############################################################################
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

from openerp import models, fields, api, _


class StockSerial(models.TransientModel):

    _name = 'stock.serial'

    @api.multi
    @api.depends('serial_ids')
    def _qty_done(self):
        for serial in self:
            serial.product_qty_done = len(serial.serial_ids)

    @api.model
    def default_get(self, field_list):
        res = super(StockSerial, self).default_get(field_list)
        move_obj = self.env['stock.move']
        move_ids = self._context.get('active_id', [])
        move_id = move_obj.browse(move_ids)
        vals = []
        if move_id.picking_type_id.code != 'incoming':
            for move_reserve in move_id.reserved_quant_ids:
                if move_reserve.lot_id and move_reserve.qty == 1:
                    vals_serial = {
                        'lot_id': move_reserve.lot_id.id,
                        'serial': move_reserve.lot_id.name
                    }
                    vals.append(vals_serial)
        else:
            for move_op in move_id.picking_id.pack_operation_ids:
                if move_op.product_id == move_id.product_id and\
                        move_op.lot_id and move_op.product_qty == 1:
                    vals_serial = {
                        'lot_id': move_op.lot_id.id,
                        'serial': move_op.lot_id.name
                    }
                    vals.append(vals_serial)
        res.update({
            'move_id': move_id.id,
            'product_id': move_id.product_id.id,
            'product_qty': move_id.product_uom_qty,
            'serial_ids': vals
        })
        return res

    serial_ids = fields.One2many(
        'stock.serial.line', 'serial_id', 'Serials')
    move_id = fields.Many2one('stock.move', "Move")
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_qty = fields.Float('Qty', readonly=True)
    product_qty_done = fields.Float(
        'Qty Done', compute='_qty_done', store=False)

    @api.onchange('serial_ids')
    def onchange_serial(self):
        serial = []

        for serial_name in self.serial_ids:
            if serial_name.serial in serial:
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _(
                            'The Serial number {} already captured'.format(
                                serial_name.serial.encode('utf-8')))
                    }}
            else:
                serial.append(serial_name.serial)

    @api.multi
    def move_serial(self):
        quant_obj = self.env['stock.quant']

        for move in self:
            move_id = move.move_id

            product_id = move_id.product_id.id
            move_id.picking_id.pack_operation_ids.filtered(
                lambda dat: dat.product_id.id == product_id).unlink()

            if move_id.picking_type_id.use_existing_lots:
                move_id.do_unreserve()

            for move_serial in move.serial_ids:
                # This validation by picking type code and
                # picking type create/existing lots is necessary because
                # the lot can be used again if are not present in someone
                # location of type internal and not need to be created
                if move_id.picking_type_id.use_create_lots or (
                    move_id.picking_type_id.use_existing_lots and
                        move_id.picking_id.picking_type_id.code == 'incoming'):
                    self._get_pack_ops_lot(move, move_serial)
                else:
                    quants = quant_obj.quants_get_prefered_domain(
                        move_id.location_id,
                        move_id.product_id,
                        qty=1,
                        domain=[],
                        prefered_domain_list=[],
                        restrict_lot_id=move_serial.lot_id.id,
                        restrict_partner_id=[],
                    )
                    quant_obj.quants_reserve(quants, move_id)
        return True

    @api.model
    def _get_pack_ops_lot(self, move, move_serial):
        lot_obj = self.env['stock.production.lot']
        stock_pack_op_obj = self.env['stock.pack.operation']
        lot_id = move_serial.lot_id
        if not lot_id:
            lot_id = lot_obj.create({
                'name': move_serial.serial,
                'ref': move_serial.serial,
                'product_id': move.move_id.product_id.id
            })
        stock_pack_op_obj.create({
            'picking_id': move.move_id.picking_id.id,
            'product_qty': 1,
            'product_id': move.move_id.product_id.id,
            'lot_id': lot_id.id,
            'owner_id': move.move_id.picking_id.owner_id.id,
            'location_id': move.move_id.location_id.id,
            'location_dest_id': move.move_id.location_dest_id.id,
            'product_uom_id': move.move_id.product_id.uom_id.id
        })


class StockSerialLine(models.TransientModel):

    _name = 'stock.serial.line'

    serial_id = fields.Many2one('stock.serial', 'Serial')
    serial = fields.Char('Serial', required=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')

    @api.onchange('serial')
    def onchange_lot_id(self):
        move_obj = self.env['stock.move']
        move = self._context.get('move_id', [])
        move_id = move_obj.browse(move)
        prod_lot_obj = self.env['stock.production.lot']
        quant_obj = self.env['stock.quant']

        if move_id.picking_type_id.use_create_lots:
            return {}
        if self.serial:
            serial_number = self.serial.encode('utf-8')
            lot_id = prod_lot_obj.search(
                [('name', '=', self.serial),
                 ('product_id', '=', move_id.product_id.id)], limit=1)

            if lot_id and\
                    move_id.picking_id.picking_type_id.code == 'incoming':
                other_quants = quant_obj.search(
                    [('product_id', '=', move_id.product_id.id),
                     ('lot_id', '=', lot_id.id),
                     ('qty', '>', 0.0),
                     ('location_id.usage', '=', 'internal')])
                if other_quants:
                    message = _(
                        'The serial number {} is already in stock'.format(
                            serial_number))
                    return {
                        'warning': {
                            'title': _('Warning'),
                            'message': message
                        }}
            if not lot_id:
                message = _('Serial {} not found'.format(serial_number))
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': message
                    }}
            self.lot_id = lot_id
