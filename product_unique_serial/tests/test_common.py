# -*- coding: utf-8 -*-
# Copyright 2016 Vauxoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from copy import deepcopy

from openerp.tests.common import TransactionCase
from openerp import _


class TestCommon(TransactionCase):
    """ This test will prove the next cases to procure the module uniqueness:
    - Test 1: Can't be created two Serial Numbers with the same name"""

    note = _(
        u'Remember: When a serial number (lot) is selected, its quantity '
        u'is fixed against the quantity in the serial number (lot) and not '
        u'against the quantity in full of the product.')

    msg_greater = _(
        u'Product %s has been configured to use unique lots. '
        u'You are trying to set %s items in lot %s. %s')

    msg_increase = _(
        u'Product %s has been configured to use unique lots. '
        u'You are trying to increase %s items in the lot %s. %s')

    def setUp(self):
        super(TestCommon, self).setUp()
        self.stock_production_lot_obj = self.env['stock.production.lot']
        self.stock_picking_type_obj = self.env['stock.picking.type']
        self.stock_picking_obj = self.env['stock.picking']
        self.product_obj = self.env['product.product']
        self.stock_move_obj = self.env['stock.move']
        self.product_uom_obj = self.env['product.uom']
        self.stock_location_obj = self.env['stock.location']
        self.stock_inventory_obj = self.env['stock.inventory']
        self.stock_inventory_line_obj = self.env['stock.inventory.line']
        self.stock_loc = self.env.ref('stock.stock_location_stock')
        self.prod_d1 = self.env.ref('product_unique_serial.product_demo_1')
        self.stock_production_lot_obj = self.env['stock.production.lot']

    def create_stock_picking(self, moves_data, picking_data, picking_type):
        """ Returns the stock.picking object, with his respective created
            created stock.move lines """
        # Require deepcopy for clone dict into list items
        moves_data_copy = deepcopy(moves_data)
        picking_data_copy = picking_data.copy()
        stock_move_ids = []
        default_product_data = None
        for move_n in moves_data_copy:
            # Getting the qty for the stock.move
            qty = move_n.get('qty')
            del move_n['qty']
            # Getting default data through product_id onchange
            if 'source_loc' in move_n.keys()\
                    and 'destination_loc' in move_n.keys():
                default_product_data = self.stock_move_obj.onchange_product_id(
                    prod_id=move_n.get('product_id'),
                    loc_id=move_n.get('source_loc'),
                    loc_dest_id=move_n.get('destination_loc'))
                del move_n['source_loc']
                del move_n['destination_loc']
            else:
                default_product_data = self.stock_move_obj.onchange_product_id(
                    move_n.get('product_id'))
            move_n.update(default_product_data.get('value'))
            # Getting default data through product_uom_qty onchange
            default_qty_data = self.stock_move_obj.onchange_quantity(
                move_n.get('product_id'),
                qty,
                default_product_data.get('product_uom'),
                default_product_data.get('product_uos'))
            default_qty_data['value'].update({'product_uom_qty': qty})
            move_n.update(default_qty_data.get('value'))
            # Getting the new stock.move id
            move_created = self.stock_move_obj.with_context(
                default_picking_type_id=picking_type.id).create(move_n)
            stock_move_ids.append(move_created.id)
        # Creating picking
        picking_data_copy.update({
            'move_lines': [(6, 0, stock_move_ids)],
            # TODO: Uncomment when fix current context bug
            # 'move_lines': [(0, 0, moves_data_copy)],
            # and remove move_created line
            'picking_type_id': picking_type.id})
        return self.stock_picking_obj.create(picking_data_copy)

    def transfer_picking(self, picking_instance, serial_number=None):
        """ Creates a wizard to transfer the picking given like parameter """
        # Marking the picking as Todo
        picking_instance.action_confirm()
        if picking_instance.state == 'confirmed':
            # Checking availability
            picking_instance.action_assign()
        if picking_instance.state == 'assigned':
            # Transfering picking
            transfer_details = picking_instance.do_enter_transfer_details()
            wizard_for_transfer = self.env[transfer_details.get('res_model')].\
                browse(transfer_details.get('res_id'))
            if serial_number:
                if len(serial_number) == 1:
                    for transfer_item in wizard_for_transfer.item_ids:
                        transfer_item.lot_id = serial_number[0].id
                else:
                    # Case for the A, B & C serial numbers: That are 3 like
                    # value for the quantity field in the wizard, so we should
                    # split this record 2 times.
                    # Splitting the record and executing the transfer
                    wizard_split = wizard_for_transfer.item_ids[0].\
                        split_quantities()
                    wizard_for_transfer = self.env['stock.transfer_details'].\
                        browse(wizard_split.get('res_id'))
                    wizard_split = wizard_for_transfer.item_ids[0].\
                        split_quantities()
                    wizard_for_transfer = self.env['stock.transfer_details'].\
                        browse(wizard_split.get('res_id'))
                    index = 0
                    for transfer_item in wizard_for_transfer.item_ids:
                        transfer_item.lot_id = serial_number[index].id
                        index += 1
            # Executing the picking transfering
            wizard_for_transfer.do_detailed_transfer()
