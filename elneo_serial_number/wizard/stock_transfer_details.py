from openerp import models, api, fields


class stock_transfer_details_items(models.TransientModel):
    _inherit = 'stock.transfer_details_items'
    
    serial_number = fields.Char('Serial number')
    
    
class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'
    
    @api.one
    def do_detailed_transfer(self):
        for item in self.item_ids:
            if item.serial_number:
                if item.lot_id:
                    item.lot_id.name = item.serial_number
                else:
                    item.lot_id = self.env['stock.production.lot'].create({'name':item.serial_number,'product_id':item.product_id.id})
        return super(stock_transfer_details,self).do_detailed_transfer()


