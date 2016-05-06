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
from openerp import _, api, fields, exceptions, models
from openerp.exceptions import ValidationError


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.multi
    @api.depends('quant_ids.location_id')
    def _get_last_location_id(self):
        for record in self:
            if record.quant_ids.ids:
                last_quant_id = max(record.quant_ids.ids)
                last_quant_data = self.env['stock.quant'].browse(last_quant_id)
                record.last_location_id = last_quant_data.location_id.id
            else:
                record.last_location_id = False

    last_location_id = fields.Many2one(
        'stock.location',
        string="Last Location",
        compute='_get_last_location_id',
        store=True)

    # Overwrite field to deny create serial number duplicated
    ref = fields.Char('Internal Reference',
                      help="Internal reference number"
                           " in this case it"
                           " is same of manufacturer's"
                           " serial number",
                      related="name", store=True, readonly=True)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def _quant_create(self, qty, move, lot_id=False, owner_id=False,
                      src_package_id=False, dest_package_id=False,
                      force_location_from=False, force_location_to=False):
        # In case of 'Unique Lot' check if the product does not exist somewhere
        # internally already
        if lot_id and move.product_id.lot_unique_ok:
            # Extract from Odoo v9
            if qty != 1.0:
                raise exceptions.Warning(_('You should only receive by '
                                           'the piece with the same serial '
                                           'number'))
            # Customize domain
            domain_quants = [
                ('product_id', '=', move.product_id.id),
                ('lot_id', '=', lot_id),
                ('qty', '>', 0.0)
            ]
            # Check product tracking field to get location usage for domain
            if move.product_id.track_all:
                domain_quants += [('location_id.usage', '!=', 'inventory')]
            else:
                usages = []
                if move.product_id.track_incoming:
                    usages += ['internal']
                if move.product_id.track_outgoing:
                    usages += ['customer', 'transit']
                # mrp module should be installed to use track production field
                if hasattr(move.product_id, "track_production") and \
                        move.product_id.track_production:
                    usages += ['production']
                if usages:
                    domain_quants += [
                        ('location_id.usage', 'in', tuple(usages))]
            # check if exist other similar quant
            if self.search(domain_quants):
                lot_name = self.env['stock.production.lot'].browse(lot_id).name
                raise exceptions.Warning(_('The serial number %s can only '
                                           'belong to a single product in '
                                           'stock') % lot_name)
        return super(StockQuant, self)._quant_create(
            qty, move, lot_id, owner_id, src_package_id,
            dest_package_id, force_location_from, force_location_to)

    @api.multi
    @api.constrains('product_id', 'lot_id', 'qty')
    def _check_inicity_lot_product(self):
        for line in self:
            if line.lot_id and line.product_id and\
                    line.product_id.lot_unique_ok:
                note = _(
                    'When you select a serial number (lot), the quantity is '
                    'corrected with respect to\nthe quantity of that serial '
                    'number (lot) and not to the total quantity of the '
                    'product.')
                quants = self.search([
                    ('lot_id', '=', line.lot_id.id),
                    ('product_id', '=', line.product_id.id),
                    ('company_id', '=', line.company_id.id),
                    ('location_id', '=', line.location_id.id)])
                if line.qty > 1:
                    raise ValidationError(_(
                        'The product %s has active unique lot and you '
                        'try set %s in the lot %s.\nRemmember:\n %s' % (
                            line.product_id.name, line.qty,
                            line.lot_id.name, note)))
                elif sum([x.qty for x in quants]) > 1:
                    raise ValidationError(_(
                        'The product %s has active unique lot and you '
                        'try set more products in the same lot '
                        '%s.\nRemmember:\n %s' % (
                            line.product_id.name, line.lot_id.name, note)))


class StockInventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    @api.multi
    @api.constrains('product_id', 'prod_lot_id', 'product_qty')
    def _ckeck_qty_line(self):
        for line in self:
            if line.product_id.track_all and not line.prod_lot_id and\
                    not line.product_qty:
                raise ValidationError(_(
                    'The product %s has active "Full Lots Traceability", you '
                    'must assign the serial number to update the quantity.'
                    % line.product_id.name))


class StockMove(models.Model):

    _inherit = 'stock.move'

    @api.multi
    def move_lot_unique(self):
        for move in self:
            pick_type = move.picking_id.picking_type_id
            if move.product_id.lot_unique_ok and move.state in (
                    'draft', 'waiting', 'confirmed', 'assigned') and\
                    (pick_type.use_create_lots or pick_type.use_existing_lots):
                move.lot_unique = True

    lot_unique = fields.Boolean('Is lot unique?', compute='move_lot_unique')


class StockPickingType(models.Model):

    _inherit = 'stock.picking.type'

    use_existing_lots = fields.Boolean(
        'Use Existing Lots',
        help='If this is checked, '
        'you will be able to choose the Serial Number / Lots. ')
    use_create_lots = fields.Boolean(
        'Create New Lots',
        help='If this is checked only, '
        'it will suppose you want to create new Serial Numbers / Lots, '
        'so you can provide them in a text field. ')
