# coding: utf-8
from openerp.addons.product_unique_serial.tests.test_for_unicity\
    import TestUnicity


class TestSerialWizard(TestUnicity):

    def setUp(self):
        super(TestSerialWizard, self).setUp()
        self.picking_type_in = self.env.ref('stock.picking_type_in')
        self.picking_type_out = self.env.ref('stock.picking_type_out')
        self.stock_serial = self.env['stock.serial']
        self.stock_serial_line = self.env['stock.serial.line']
        self.product_unique = self.env.ref(
            'product_unique_serial.product_demo_1')

    def test_serial_wizard_incoming_outgoing(self):
        'This test validate the capture of number serial for move '\
            'of type incoming and to use number serial in '\
            'picking type of outgoing'

        picking_val = {
            'name': 'Picking'
        }
        move_val = [{
            'product_id': self.product_unique.id,
            'qty': 3
        }]

        # create picking
        picking_id = self.create_stock_picking(
            move_val, picking_val, self.picking_type_in)

        for move in picking_id.move_lines:
            # create wizard to capture number serial for this move
            stock_serial_id = self.stock_serial.with_context(
                {'active_id': move.id}).create({})

            # capture one number serial
            self.stock_serial_line.create(
                {'serial': 'serial_1',
                 'serial_id': stock_serial_id.id})
            stock_serial_id.move_serial()

            # if the first wizard was closed with one number serial
            # when the wizard for the same move is reopen must be has
            # the number serial captured
            stock_serial_reopen_id = self.stock_serial.with_context(
                {'active_id': move.id}).create({})

            # validate that the reopen wizard has the number serial
            # captured before
            self.assertEquals(
                len(stock_serial_reopen_id.serial_ids), 1)

            # Add two number serial for the same move
            self.stock_serial_line.create(
                {'serial': 'serial_2',
                 'serial_id': stock_serial_reopen_id.id})
            self.stock_serial_line.create(
                {'serial': 'serial_3',
                 'serial_id': stock_serial_reopen_id.id})

            # the wizard must be has three number serial
            self.assertEquals(
                len(stock_serial_reopen_id.serial_ids), 3)
            stock_serial_reopen_id.move_serial()

            # Transfer the wizard
            self.transfer_picking(picking_id)

            # The move must be three quants by the
            # captured serial number by wizard
            self.assertEquals(
                len(move.quant_ids), 3)
            serial_1_id = move.quant_ids[0].lot_id
            serial_2_id = move.quant_ids[1].lot_id
            serial_3_id = move.quant_ids[2].lot_id
            self.assertTrue(
                serial_1_id.name in ('serial_1', 'serial_2', 'serial_3'),
                'Number Serial must be in quants')
            self.assertTrue(
                serial_2_id.name in ('serial_1', 'serial_2', 'serial_3'),
                'Number Serial must be in quants')
            self.assertTrue(
                serial_3_id.name in ('serial_1', 'serial_2', 'serial_3'),
                'Number Serial must be in quants')

        # Create vals to  picking of outgoing
        picking_val = {
            'name': 'Picking out'
        }
        move_val = [{
            'product_id': self.product_unique.id,
            'qty': 3
        }]

        # create picking
        picking_out_id = self.create_stock_picking(
            move_val, picking_val, self.picking_type_out)
        for move in picking_out_id.move_lines:
            # create wizard to capture number serial for this move
            # add three number serial with quants for this product to reserve
            stock_serial_id = self.stock_serial.with_context(
                {'active_id': move.id}).create({
                    'serial_ids': [
                        (0, 0, {
                            'serial': serial_1_id.name,
                            'lot_id': serial_1_id.id}),
                        (0, 0, {
                            'serial': serial_2_id.name,
                            'lot_id': serial_2_id.id}),
                        (0, 0, {
                            'serial': serial_3_id.name,
                            'lot_id': serial_3_id.id})
                    ]
                })
            stock_serial_id.move_serial()
            # the move must be reserved three quants added from number serial
            self.assertEquals(len(move.reserved_quant_ids), 3)

    def test_serial_wizard_validate_serial_outgoing(self):
        'This test validate that number serial'\
            'exists for product in capture in wizard'
        picking_val = {
            'name': 'Picking'
        }
        move_val = [{
            'product_id': self.product_unique.id,
            'qty': 3
        }]

        # create picking
        picking_id = self.create_stock_picking(
            move_val, picking_val, self.picking_type_out)

        for move in picking_id.move_lines:
            # create wizard to capture number serial for this move
            stock_serial_id = self.stock_serial.with_context(
                {'active_id': move.id}).create({})
            stock_serial_line_id = self.stock_serial_line.with_context(
                {'move_id': move.id}).new({
                    'serial': 'serial_1',
                    'serial_id': stock_serial_id.id})
            serial_line_val = stock_serial_line_id.onchange_lot_id()
            self.assertTrue(
                serial_line_val.get('warning'), 'warning must be created')
