from openerp import  models,fields, api
from openerp.tools.safe_eval import safe_eval

class res_config(models.TransientModel):
    _inherit = 'maintenance.config.settings'

    account_sale_journal = fields.Many2one('account.journal','Maintenance Intervention Sale Journal',domain=[('type','=','sale')])

    @api.multi
    def set_account_sale_journal(self):
        
        
        self.env['ir.config_parameter'].set_param('maintenance_product.account_sale_journal',repr(self.account_sale_journal.id))
        
    
   
        
    
    @api.multi
    def get_default_account_sale_journal(self):
        res = {}
        account_sale_journal = self.env['ir.config_parameter'].get_param('maintenance_product.account_sale_journal',False)
        if account_sale_journal:
            res.update({'account_sale_journal':int(account_sale_journal)})
        #test = self.payment_term_partner
        
        return res