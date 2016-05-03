

from openerp.osv import osv, fields, orm
from openerp.tools.float_utils import float_round as round

class pos_order(osv.osv):
    _inherit = "pos.order"

    def _create_account_move_line(self, cr, uid, ids, session=None, move_id=None, context=None):
        super(pos_order, self)._create_account_move_line(cr, uid, ids, None, None, context=context)

        pos_order_obj = self.pool.get('pos.order')
        account_move_obj = self.pool.get('account.move')

        move_line_obj = self.pool.get('account.move.line')

        for order in self.browse(cr, uid, ids, context=context):
            
            session = order.session_id

            if move_id is None:
                # Create an entry for the sale
                move_id = pos_order_obj._create_account_move(cr, uid, session.start_at, 
                    session.name, session.config_id.journal_id.id, company_id, context=context)
            
            move = account_move_obj.browse(cr, uid, move_id, context=context)

            amount_total = order.amount_total

            for o_line in order.lines:
                if o_line.product_id.type != 'service' and o_line.product_id.valuation == 'real_time':
                    # if pos order amount > 0 = sale then stkacc account = stock out or account = current stock
                    # first check the product, if empty check the category
                    stkacc = o_line.product_id.property_stock_account_output and o_line.product_id.property_stock_account_output

                    if not stkacc:
                        stkacc = o_line.product_id.categ_id.property_stock_account_output_categ and \
                            o_line.product_id.categ_id.property_stock_account_output_categ
                    
                    #cost of goods account cogacc 
                    cogacc = o_line.product_id.property_account_expense and o_line.product_id.property_account_expense
                    if not cogacc:
                        cogacc = o_line.product_id.categ_id.property_account_expense_categ and \
                        o_line.product_id.categ_id.property_account_expense_categ

                if cogacc and stkacc:
                    amount = o_line.qty * o_line.product_id.standard_price
                    line_vals= {
                        'period_id': move.period_id.id,
                        'name': order.name,
                        'move_id': move_id,
                        'journal_id': move.journal_id.id,
                        'date': move.date,
                        'product_id': o_line.product_id.id,
                        'partner_id': order.partner_id and order.partner_id.id or False,
                        'quantity': o_line.qty,
                        'ref': o_line.name
                    }

                    if amount_total > 0:
                        #create move.lines to credit stock and debit cogs
                        caml = {
                            'account_id': stkacc.id,
                            'credit': amount,
                            'debit': 0.0,
                            }
                        caml.update(line_vals)
                        daml = {
                            'account_id': cogacc.id,
                            'credit': 0.0,
                            'debit': amount,
                            }
                        daml.update(line_vals)
                        move_line_obj.create(cr, uid, caml)
                        move_line_obj.create(cr, uid, daml)

                    if amount_total < 0:
                        #create move.lines to credit cogs and debit stock
                        caml = {
                            'account_id': cogacc.id,
                            'credit': -amount,
                            'debit': 0.0,
                            }
                        caml.update(line_vals)
                        daml = {
                            'account_id': stkacc.id,
                            'credit': 0.0,
                            'debit': -amount,
                            }
                        daml.update(line_vals)
                        move_line_obj.create(cr, uid, caml)
                        move_line_obj.create(cr, uid, daml)
        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
