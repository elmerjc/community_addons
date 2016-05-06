from openerp import  models, fields, api

class res_config(models.TransientModel):
    _name = 'maintenance.config.settings'
    _inherit = 'res.config.settings'