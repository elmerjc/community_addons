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
from openerp.exceptions import ValidationError


class StockSerial(models.TransientModel):

    _name = 'stock.serial'

    @api.multi
    @api.depends('serial_ids')
    def _compute_qty_done(self):
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
        'Qty Done', compute='_compute_qty_done', store=False)

    @api.onchange('serial_ids')
    def onchange_serial(self):
        serials = [serial.serial for serial in self.serial_ids]
        if any([serials.count(serial) > 1 for serial in serials]):
            serial_number = list(set([
                serial for serial in serials if serials.count(serial) > 1]))[0]
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _('The Serial number %s already captured') % (
                        serial_number.encode('utf-8'))
                }
            }

    @api.multi
    def move_serial(self):
        quant_obj = self.env['stock.quant']

        for move in self:
            move_id = move.move_id
            product_id = move_id.product_id.id
            move_id.picking_id.pack_operation_ids.filtered(
                lambda dat: dat.product_id.id == product_id).unlink()

            if len(move.serial_ids) > move_id.product_uom_qty:
                raise ValidationError(
                    _('The serial numbers loaded cannot be greater'
                      ' than the requested quantity of the product'))

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
                    if quant_obj.search_count([
                            ('product_id', '=', move_id.product_id.id),
                            ('lot_id', '=', move_serial.lot_id.id),
                            ('qty', '>', 0.0),
                            ('location_id.usage', '=', 'internal')]):
                        raise ValidationError(
                            _('The serial number %s is already stock') % (
                                move_serial.serial))
                    self._get_pack_ops_lot(move, move_serial)
                elif not move_serial.lot_id:
                    raise ValidationError(
                        _('Serial number %s not found') % (move_serial.serial))
                elif move_serial.lot_id.quant_ids.filtered('reservation_id'):
                    raise ValidationError(
                        _('The serial number %s is already reserved in'
                          ' another move') % (move_serial.serial))
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
    lot_id = fields.Many2one(
        'stock.production.lot', string='Lot/Serial Number')

    _sql_constraints = [
        ('uniq_serial', 'unique(serial_id, serial)',
         'You have already mentioned this serial number in another line')]

    @api.onchange('serial')
    def onchange_lot_id(self):
        move_obj = self.env['stock.move']
        move = self._context.get('move_id', [])
        move_id = move_obj.browse(move)
        prod_lot_obj = self.env['stock.production.lot']
        quant_obj = self.env['stock.quant']

        if not self.serial or move_id.picking_type_id.use_create_lots:
            return {}

        serial_number = self.serial.encode('utf-8')
        lot_id = prod_lot_obj.search([
            ('name', '=', serial_number),
            ('product_id', '=', move_id.product_id.id)], limit=1)

        if not lot_id:
            return {'warning': {
                'title': _('Warning'),
                'message': _('Serial number %s not found') % (serial_number),
                }
            }
        elif (move_id.picking_id.picking_type_id.code == 'incoming' and
                quant_obj.search([
                    ('product_id', '=', move_id.product_id.id),
                    ('lot_id', '=', lot_id.id),
                    ('qty', '>', 0.0),
                    ('location_id.usage', '=', 'internal')])):
            return {'warning': {
                'title': _('Warning'),
                'message': _('The serial number %s is already stock') % (
                    serial_number),
                }
            }
        self.lot_id = lot_id
