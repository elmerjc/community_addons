# -*- coding: utf-8 -*-
##############################################################################
#
#    Elneo
#    Copyright (C) 2011-2015 Elneo (Technofluid SA) (<http://www.elneo.com>).
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
from openerp import models,fields,api
   
class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    serialnumber_required = fields.Boolean("Serial Number Required",help="Check this box to require serial number on warehouse operations")
    
    @api.onchange('serialnumber_required')
    @api.one
    def _change_serialnumber_required(self):
        if (self.serialnumber_required):
            self.track_outgoing = True
            self.unique_serial_number = True
        else:
            self.track_outgoing = False
            self.track_all = False
            self.track_incoming = False
            self.unique_serial_number=False
            
class ProductProduct(models.Model):
    _inherit='product.product'
    
    @api.onchange('serialnumber_required')
    @api.one
    def _change_serialnumber_required(self):
        if (self.serialnumber_required):
            self.track_outgoing = True
            self.unique_serial_number = True
        else:
            self.track_outgoing = False
            self.track_all = False
            self.track_incoming = False
            self.unique_serial_number=False
            