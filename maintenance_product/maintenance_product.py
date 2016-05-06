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
import time
import logging

from datetime import datetime, timedelta

from openerp import models, fields, api, _
from openerp.exceptions import Warning


def get_datetime(date_field):
    return datetime.strptime(date_field[:19], '%Y-%m-%d %H:%M:%S')


class intervention_type(models.Model):
    _inherit="maintenance.intervention.type"
    
    @api.one
    def _get_maintenance_available(self):
        
        domains = {
            'count_maintenance_draft': [('state', '=', 'draft')],
            'count_maintenance_confirmed': [('state', '=', 'confirmed'),('available','=',False)],
            'count_maintenance_available': [('state', '=', 'confirmed'),('available','=',True)],
        }
        
        for field in domains:
            data = self.env['maintenance.intervention'].read_group(domains[field] +
                [('state', 'not in', ('done', 'cancel')), ('maint_type', '=', self.id)],
                ['maint_type'], ['maint_type'])
            count = dict(map(lambda x: (x['maint_type'] and x['maint_type'][0], x['maint_type_count']), data))
            setattr(self,field,count.get(self.id, 0)) 
            #result.setdefault(self.id, {})[field] = count.get(self.id, 0)
        
        if self.count_maintenance:
            self.rate_maintenance_late = self.count_maintenance_late * 100 / (self.count_maintenance_confirmed + self.count_maintenance_available)
        else:
            self.rate_maintenance_late = 0
    
    
    count_maintenance_available=fields.Integer(compute=_get_maintenance_available)
    count_maintenance_confirmed=fields.Integer(compute=_get_maintenance_available)
    rate_maintenance_late=fields.Integer(compute=_get_maintenance_available)

class maintenance_intervention(models.Model):
    _inherit = 'maintenance.intervention'
    
    @api.one
    def unlink(self):
        if self.sale_order_id and self.sale_order_id.state != 'cancel' and self.sale_order_id.state != 'draft':
            raise Warning(_('You can\'t delete intervention with confirmed sale order.\n\n Please cancel sale order before.'))
        return super(maintenance_intervention, self).unlink()
    
    @api.one
    def _get_available(self):
        if self.state != 'confirmed':
            self.available = False
        else:
            if not self.intervention_products:
                # No spare parts to wait for
                self.available = True
            else:
                available_pickings = self.sale_order_id.picking_ids.filtered(lambda r:(r.state == 'assigned' and r.picking_type_id.code =='outgoing') or not r.move_lines)
                out_pickings = self.sale_order_id.picking_ids.filtered(lambda r:(r.state in ['waiting','confirmed','partially_available','assigned'] and r.picking_type_id.code =='outgoing') or not r.move_lines)
                self.available = len(available_pickings) > 0 and (len(available_pickings) == len(out_pickings))
    
    @api.model
    def _search_available(self, operator, value):
        op_value = operator
        if op_value == '=':
            op_value = '=='
            
        boolean = eval(str(value) + str(op_value) + 'True')
        available_ids = self.env['stock.picking'].search([('picking_type_id.code','=','outgoing'),('state','=','assigned')])
        domain = ['&',('state','=','confirmed'),'|',('intervention_products','=',False),('sale_order_id.picking_ids','in',available_ids.mapped('id'))]  
        available_interventions = self.search(domain)
        
        if boolean:
            return [('id','in',available_interventions.mapped('id'))]
        else:
            return [('id','not in',available_interventions.mapped('id'))]
    
    stock_pickings = fields.One2many(related='sale_order_id.picking_ids', relation='stock.picking', string="Pickings")
    sale_order_id = fields.Many2one('sale.order',string='Sale order', readonly=True)
    intervention_products = fields.One2many('maintenance.intervention.product', 'intervention_id', 'Maintenance intervention products',auto_join=True)

    available = fields.Boolean(compute=_get_available,search='_search_available', string="Available")
    warehouse_id = fields.Many2one(related='sale_order_id.warehouse_id', string="Warehouse")

    @api.one
    def copy(self,default={}):
        default.update({'intervention_products':None})
        
        new_id = super(maintenance_intervention, self).copy(default)
        new_id.sale_order_id = None
        
        for intervention_product in self.intervention_products:
            product = intervention_product.copy({'intervention_id':new_id.id})
            
        return new_id
    
    @api.multi
    def action_confirm(self):
        if self.action_create_update_sale_order():
            return super(maintenance_intervention,self).action_confirm()
        
    
    @api.multi
    def action_create_quotation(self):
        return self.with_context(quotation=True).action_create_update_sale_order()
    
    @api.multi
    def _update_sale_workforce_line(self,sale_order):
        if (sale_order.order_line and self.maint_type.workforce_product_id not in sale_order.order_line.mapped('product_id')) or not sale_order.order_line:
            order_line={}
            order_line['product_id'] = self.maint_type.workforce_product_id.id
            order_line['product_uom_qty'] = 0
            order_line['product_uos_qty'] = 0
            order_line['order_id'] = sale_order.id
            order_line['name'] = self.maint_type.workforce_product_id.description or '-'
            order_line['price_unit'] = self.maint_type.workforce_product_id.list_price
            
            
            #re-check every time the cost price at intervention validation
            order_line['purchase_price'] = self.maint_type.workforce_product_id.cost_price
            order_line['delay'] = self.maint_type.workforce_product_id.seller_delay
            self.env['sale.order.line'].create(order_line)
    
    @api.multi
    def action_create_update_sale_order(self): 
        #intervention must be reload 
        if len(self) > 0 and self[0].state=='confirmed':
            return False

        #create sale_order
        for intervention in self:
            partner = intervention.installation_id.partner_id
            sale_order_line_pool = self.env['sale.order.line']
            
            if intervention.sale_order_id:
                #add sale_order_lines to existing sale_order 
                for intervention_product in intervention.intervention_products:
                    if not sale_order_line_pool.search([('intervention_product_id','=',intervention_product.id)]):
                        order_line = self.get_sale_order_line(intervention.sale_order_id, intervention_product, partner)
                        sale_order_line_pool.create(order_line)
            else:
                sale_order_pool = self.env['sale.order']
                
                default_values = sale_order_pool.onchange_partner_id(partner.id)['value']
                
                invoice_address_id = None
                if intervention.installation_id.invoice_address_id:
                    invoice_address_id = intervention.installation_id.invoice_address_id.id
                else:
                    invoice_address_id = default_values['partner_invoice_id']
                    
                delivery_address_id = None
                if intervention.installation_id.address_id:
                    delivery_address_id = intervention.installation_id.address_id.id
                else:
                    delivery_address_id = default_values['partner_shipping_id']
                    
                contact_address_id = None
                if intervention.contact_address_id:
                    contact_address_id = intervention.contact_address_id.id
                    
                default_values['partner_id'] = partner.id
                default_values['partner_invoice_id'] = invoice_address_id
                default_values['partner_shipping_id'] = delivery_address_id
                default_values['intervention_id'] = intervention.id 
                default_values['order_policy'] = 'picking'
                
                
                for field in default_values.keys():
                    if type(default_values[field]) == list:
                        field_type = sale_order_pool._columns[field]._type
                        if field_type == 'one2many':
                            default_values[field] = [(0,0,val) for val in default_values[field]] 
                        elif field_type == 'many2many':
                            default_values[field] = [(4,val) for val in default_values[field]]
                
                
                sale_order = sale_order_pool.create(default_values)
                
                
                #create sale order lines from maintenance intervention products of current intervention 
                for intervention_product in intervention.intervention_products:
                    order_line = self.get_sale_order_line(sale_order, intervention_product, partner)
                    new_order_line_id = sale_order_line_pool.create(order_line)
                    intervention_product.sale_order_line_id= new_order_line_id
                                        
                #update intervention
                intervention.sale_order_id = sale_order
                
            self._update_sale_workforce_line(intervention.sale_order_id)
            
            #confirm sale order
            if not self._context.get("quotation",False):
                intervention.sale_order_id.signal_workflow('order_confirm')
                
              
        return True
    
    @api.model
    def get_sale_order_line(self,sale_order, intervention_product, partner):
        
        order_line = self.env['sale.order.line'].product_id_change(
                            sale_order.pricelist_id.id, intervention_product.product_id.id, qty=intervention_product.quantity, 
                            partner_id=partner.id, lang=partner.lang, fiscal_position=sale_order.fiscal_position.id)['value']
            
        order_line['product_id'] = intervention_product.product_id.id
        order_line['product_uom_qty'] = intervention_product.quantity
        order_line['product_uos_qty'] = intervention_product.quantity
        order_line['intervention_product_id'] = intervention_product.id
        order_line['order_id'] = sale_order.id
        

        order_line['name'] = intervention_product.description or '-'
            
       
        order_line['price_unit'] = intervention_product.sale_price
        
        
        #re-check every time the cost price at intervention validation
        order_line['purchase_price'] = intervention_product.cost_price
            
        
        order_line['delay'] = intervention_product.delay

        order_line['discount'] = intervention_product.discount
        
        
        if order_line.has_key('tax_id'):
            taxes = order_line['tax_id']
            order_line['tax_id']=[(6,0,taxes)]
        
        return order_line
    
    @api.multi
    def action_cancel(self):
        '''
        Cancel sale_order with intervention
        '''
        result = super(maintenance_intervention, self).action_cancel()
        sale_orders = self.mapped('sale_order_id')
        
        for sale_order in sale_orders:
            sale_order.with_context(cancel_from_intervention=True).action_cancel()
            
        return result
    
    
    @api.multi
    def action_draft(self):
        '''
        Reset sale_order to draft with intervention
        ''' 
        result = super(maintenance_intervention, self).action_draft()
        sale_orders = self.mapped('sale_order_id')
        
        for sale_order in sale_orders:
            sale_order.action_cancel()
            sale_order.action_cancel_draft()
        return result
    
    @api.one
    def manage_diff_qty(self,diff_qty): #function to override in other modules
        return True
    
    @api.multi
    def action_done(self):
        '''
        Add products to delivery order
        
        '''
        for intervention in self:
            order = intervention.sale_order_id
            pickings = intervention.sale_order_id.picking_ids
            
            diff_qty = [] #list of products of intervention and there differences between expected quantities and final quantities  
            
            if order.state in ('draft', 'cancel'):
                raise Warning(_('Please confirm sale order before closing intervention !'))
            
            out_picking = False
            int_picking = False
            for picking in pickings:
                if picking.picking_type_id.code == 'outgoing':
                    out_picking = picking 
                if picking.picking_type_id.code == 'internal':
                    int_picking = picking
            
            #There are products
            products_of_moves = self.env['stock.move']
            if out_picking:
                
                #Delete moves
                moves_todelete = self.env['stock.move']
                for move in out_picking.move_lines:
                    if move.intervention_product_id:
                        products_of_moves += move
                    elif move.procurement_id.sale_line_id:
                        moves_todelete = move | moves_todelete
                        diff_qty.append((move.product_id.id, - move.procurement_id.sale_line_id.product_uom_qty, move.procurement_id.sale_line_id.id))
                    else:
                        moves_todelete = move | moves_todelete
                        diff_qty.append((move.product_id.id, - move.product_qty, None))
                        
                moves_todelete.write({'state':'cancel'})
            
            
            #NEW LOOP#
            for intervention_product in intervention.intervention_products:
                if intervention_product.product_id:
                    #add new moves
                    if intervention_product not in products_of_moves.mapped('intervention_product_id'):
                        location_id = intervention_product.get_move_location_id()
                        
                        location_dest_id = intervention_product.get_move_location_dest_id()
                        
                        values = self.env['stock.move'].onchange_product_id(prod_id=intervention_product.product_id.id, loc_id=location_id,
                                                                     loc_dest_id=location_dest_id, partner_id=order.partner_shipping_id.id)['value']
                        # There is no out picking (maybe a void spare part list)                                             
                        if not out_picking:
                            name = intervention.warehouse_id.maintenance_picking_type_id.sequence_id._next() or '/'
                            
                            
                            if not intervention.sale_order_id.procurement_group_id:
                                vals = self.env['sale.order']._prepare_procurement_group(intervention.sale_order_id)
                                group_id = self.env['procurement.group'].create(vals)
                                order.write({'procurement_group_id': group_id.id})
                            
                            pick_values={
                                         'name':name,
                                         'origin':intervention.code+' '+intervention.sale_order_id.name,
                                         'state':'assigned',
                                         'partner_id':intervention.partner_id.id,
                                         'location_id':intervention.warehouse_id.maintenance_picking_type_id.default_location_src_id.id,
                                         'location_dest_id':intervention.warehouse_id.maintenance_picking_type_id.default_location_dest_id.id,
                                         'picking_type_id':intervention.warehouse_id.maintenance_picking_type_id.id
                                         }
                            out_picking = self.env['stock.picking'].create(pick_values)
                        values.update({
                            'name': intervention_product.product_id.name_get()[0][1],
                            'picking_id': out_picking.id,
                            'product_id': intervention_product.product_id.id,
                            'date': intervention.date_start or time.strftime('%Y-%m-%d'),
                            'date_expected': intervention.date_start or time.strftime('%Y-%m-%d'),
                            'product_uom_qty': intervention_product.quantity,
                            'product_uos_qty': intervention_product.quantity,
                            'partner_id': order.partner_shipping_id.id,
                            'location_id': location_id,
                            'location_dest_id': location_dest_id,                            
                            'company_id': order.company_id.id,
                            'state':'done',
                            'intervention_product_id':intervention_product.id,
                            'group_id':intervention.sale_order_id.procurement_group_id.id
                        })
                        
                        diff_qty.append((intervention_product.product_id.id, intervention_product.quantity, intervention_product.sale_order_line_id.id))
                        self.env['stock.move'].create(values)
                        
                    else:
                        #update moves
                        move = products_of_moves.filtered(lambda r:r.intervention_product_id.id==intervention_product.id)
                        if move:
                            move = move[0]
                            move_qty = move.product_qty
                            interv_qty = intervention_product.quantity
                            if move_qty != interv_qty:
                                ''' FRAMEWORK ERROR IN stock.move.write() (in stock module) : DONT TEST SUPERUSER_ID TO BYPASS product changes'''
                                intervention_moves_done = move.filtered(lambda r:r.state=='done')
                                if self.env.context.get('intervention_force_done',False) and intervention_moves_done:
                                    intervention_moves_done.write({'state':'assigned'})
                                move.sudo().write({'product_uom_qty':interv_qty, 'product_uos_qty':interv_qty})
                                intervention_moves_done.write({'state':'done'})
                                ''' END OF MODIFICATION '''
                                original_qty = 0
                                if intervention_product and intervention_product.sale_order_line_id:
                                    original_qty = intervention_product.sale_order_line_id.product_uom_qty
                                diff_qty.append((move.product_id.id, interv_qty-original_qty, move.procurement_id.sale_line_id.id))    
                        
            
                        
            intervention.manage_diff_qty(diff_qty)
                        
            
            if out_picking:
                out_picking.force_assign()
                out_picking.do_transfer()
                '''
                moves=out_picking.move_lines
                for move in moves:
                    move.action_done()
                out_picking.action_done()
                '''
                #self.env['stock.move'].action_done([move.id for move in out_picking.move_lines if move.id not in moves_todelete])
                #self.env['stock.picking'].action_done([out_picking.id])
            
            if int_picking:
                (int_picking.move_lines - moves_todelete).action_done()
                int_picking.action_done()
                #self.env['stock.move'].action_done([move.id for move in int_picking.move_lines if move.id not in moves_todelete])
                #self.env['stock.picking'].action_done([int_picking.id])
                
            intervention.generate_invoice()
      
        return super(maintenance_intervention, self).action_done()
    
    @api.multi
    def generate_invoice(self):
        result = self.env['account.invoice']
        for intervention in self:
            
            out_picking = self.env['stock.picking']
            out_picking = intervention.sale_order_id.picking_ids.filtered(lambda r:r.picking_type_id.code=='outgoing' and r.state != 'cancel')
            
            if not out_picking and intervention.intervention_products:
                raise Warning(_('The intervention spare parts is not void and there is no delivery order for this intervention.'))
            
            maintenance_time = 0
            for task in intervention.tasks:
                if task.planned_hours:
                    maintenance_time = maintenance_time + task.maintenance_time
                        
            if not maintenance_time:
                raise Warning(_('No workforce time specified'))
            
            out_picking.mapped('sale_id').invoice_ids.filtered(lambda r:r.state == 'draft').unlink()
            
            # FROM PICKING INVOICE GENERATION BEHAVIOUR
            for o_picking in out_picking:
                o_picking.invoice_state = '2binvoiced'
                intervention.sale_order_id.order_line.write({'invoiced': False})
                
                #out_picking.do_transfer()
                journal_id = self.env['ir.config_parameter'].get_param('maintenance_product.account_sale_journal',False)

                if not journal_id:
                    raise Warning(_('Please configure default Sale Journal for Maintenance'))
                invoice_ids = o_picking.action_invoice_create(journal_id=int(journal_id))
            
            # FROM SALE ORDER INVOICE GENERATION (THERE IS NO SPARE PARTS)
            if not out_picking or not invoice_ids:
                invoice_ids=intervention.sale_order_id.action_invoice_create()
                intervention.sale_order_id.order_line.write({'invoiced': False})
            
            #created_invoices_res = out_picking.sale_id.action_invoice_create()
            invoice = self.env['account.invoice'].browse(invoice_ids)
            
            if invoice not in intervention.sale_order_id.invoice_ids:
                intervention.sale_order_id.invoice_ids+=invoice
            
            maintenance_product = intervention.maint_type.workforce_product_id
            
            
            #Find if another invoice line for the same invoice with maintenance time product has allready been created
            invoice_maintenance_lines = self.env['account.invoice.line'].search([('invoice_id','=',invoice.id),('product_id','=',maintenance_product.id)])
            
            account_id = maintenance_product.product_tmpl_id.property_account_income.id
            if not account_id:
                account_id = maintenance_product.categ_id.property_account_income_categ.id
            
            partner=invoice.partner_id or intervention.sale_order_id.partner_invoice_id or intervention.installation_id.invoice_address_id or False
            taxes = maintenance_product.taxes_id
            if partner:
                account_id = partner.property_account_position.map_account(account_id)
                taxes_ids = partner.property_account_position.map_tax(taxes)
            else:
                taxes_ids = taxes
    
            if not invoice_maintenance_lines:
                self.env['account.invoice.line'].create({
                    'name': maintenance_product.name,
                    'invoice_id': invoice.id,
                    'uos_id': maintenance_product.uos_id.id,
                    'product_id': intervention.maint_type.workforce_product_id.id,
                    'account_id': account_id,
                    'price_unit': maintenance_product.list_price,
                    'quantity': maintenance_time,
                    'invoice_line_tax_id': [(6, 0, [x.id for x in taxes_ids])],
                    'intervention_id':intervention.id
                })
            else:
                invoice_maintenance_lines.write({'quantity':maintenance_time})
                
                
            self.env['account.invoice.line'].search([('invoice_id','=',invoice.id)]).write({'intervention_id':intervention.id})
            
            invoice.write({'origin':intervention.code+' '+intervention.sale_order_id.name})
            
            invoice.button_compute(True)
                
            result += invoice
            
        return result


class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'
    
    intervention_product_id = fields.Many2one('maintenance.intervention.product', string="Maintenance product")
    intervention_id = fields.Many2one('maintenance.intervention', string="Intervention")

class maintenance_installation(models.Model):
    _inherit = 'maintenance.installation' 
    
    @api.one
    def _get_installation_products(self):
        '''
        Get installation intervention lines history
        '''
        
        result = self.env['maintenance.intervention.product']
        for intervention in self.interventions.filtered(lambda r:r.state == 'done'):
            for product in intervention.intervention_products:
                result = result | product

        result = result.sorted(key=lambda r:r.intervention_date,reverse=True).sorted(key=lambda r:r.intervention_id.name)
        
        self.intervention_products = result
        
    
    intervention_products = fields.One2many('maintenance.intervention.product',compute=_get_installation_products,string='Spare part history')
    


class maintenance_element(models.Model):
    _inherit = 'maintenance.element' 
    
    intervention_products = fields.One2many('maintenance.intervention.product', 'maintenance_element_id', 'Spare part history')
    
maintenance_element()

class maintenance_intervention_product(models.Model):
    _name = 'maintenance.intervention.product' 

    _rec_name = 'description'
    
    @api.model
    def get_move_location_id(self):
        '''
        Get Intervention Product Move Location
        @return: location recordset
        '''
        location_id = self.intervention_id.sale_order_id.warehouse_id.lot_stock_id.id
        res = location_id
        return res
    
    @api.model
    def get_move_location_dest_id(self):
        '''
        Get Intervention Product Move Destination Location
        @return: location recordset
        '''
        res = self.intervention_id.sale_order_id.partner_shipping_id.property_stock_customer.id
        #location_dest_id = self.env['stock.location'].chained_location_get(self.intervention_id.sale_order_id.shop_id.warehouse_id.lot_output_id, self.intervention_id.sale_order_id.partner_id, self.product_id)[0]
        #res = location_dest_id
        return res

    @api.onchange('quantity')
    def onchange_quantity(self):
        if self.product_id and self.intervention_id.installation_id:
            self.onchange_product_id()
            #product_id_change_res = self.onchange_product_id(self.product_id, self.intervention_id.installation_id, self.quantity, context={})
            #return {'value':{'type':product_id_change_res['value']['type']}}
        #return {}

    @api.onchange('product_id')
    def onchange_product_id(self):        
        if self.product_id and self.intervention_id.installation_id:
            
            sale_line_change_product = self.sale_order_line_id.product_id_change(pricelist=self.intervention_id.installation_id.partner_id.property_product_pricelist.id,
                                                                                  product = self.product_id.id, 
                                                                                  partner_id=self.intervention_id.installation_id.partner_id.id, 
                                                                                  qty=self.quantity)
            
            
            
            self.description = sale_line_change_product['value'].get('name',self.product_id.name_get()[0][1])
            self.delay = sale_line_change_product['value'].get('delay',2)
            self.sale_price=sale_line_change_product['value'].get('price_unit',0)
            self.cost_price = sale_line_change_product['value'].get('purchase_price',0)
            self.route_id=sale_line_change_product['value'].get('route_id',False)

    @api.one
    def _get_int_move_availability(self):
        moves = self.moves.filtered(lambda r:r.picking_id.picking_type_id.code == 'internal')
        if len(moves) == 1 :
            self.int_move_availability = moves.state
        elif len(moves) > 1:
            one_done = False
            one_not_done = False
            not_done_state = None
            for move in moves:
                if move.state == 'done':
                    one_done = True
                elif move.state != 'cancel':
                    one_not_done = True
                    not_done_state = move.state
            if one_done and one_not_done:
                self.int_move_availability = u'partial'
            elif not one_done and one_not_done:
                self.int_move_availability = not_done_state
            else:
                moves_to_get = moves.filtered(lambda r:r.product_id.id==self.product_id.id)
                if len(moves_to_get) > 0:
                    self.int_move_availability = moves_to_get[0].state
        else:
            self.int_move_availability = 'unknown'

    description= fields.Char(string="Description", size=255)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    sale_order_line_id = fields.Many2one( comodel_name="sale.order.line",  string="Sale order line", readonly=True,copy=False)
    intervention_id = fields.Many2one('maintenance.intervention', string="Maintenance intervention", ondelete='cascade',index=True)
    maintenance_element_id = fields.Many2one('maintenance.element', string="Maintenance element",index=True) 
    quantity = fields.Float("Quantity",default=1)
    intervention_date = fields.Datetime(related='intervention_id.date_start', string="Date")
    int_move_availability = fields.Selection(compute='_get_int_move_availability', string="Reservation", selection=[('unknown','Unknown'),('partial', 'Partial'), ('draft', 'Draft'), ('waiting', 'Waiting'), ('confirmed', 'Not Available'), ('assigned', 'Available'), ('done', 'Done'), ('cancel', 'Cancelled')])
    sale_price = fields.Float("Sale price")
    cost_price = fields.Float("Cost price")
    discount = fields.Float("Discount (%)")
    delay = fields.Float("Delay")
    route_id = fields.Many2one('stock.location.route', 'Route', domain=[('sale_selectable', '=', True)])
    moves = fields.One2many('stock.move','intervention_product_id', 'Moves linked')
    #type = fields.Selection([('make_to_stock', 'from stock'), ('make_to_order', 'on order'),('partial','Partial')], 'Procurement Method')
        
    
    #synchronisation between sale_order_line fields and intervention_product fields
    @api.multi
    def update_values(self,vals):
        
        #break infinite loop
        if self.env.context.get("update_from_order",False):
            return False

        for intervention_product in self:
            if intervention_product.intervention_id and intervention_product.intervention_id.sale_order_id and intervention_product.intervention_id.state == 'draft':
                context={}
                context['update_from_intervention'] = True
                
                order_line = self.env['maintenance.intervention'].get_sale_order_line(intervention_product.intervention_id.sale_order_id, intervention_product, intervention_product.intervention_id.installation_id.partner_id)
                
                if intervention_product.sale_order_line_id:
                    intervention_product.sale_order_line_id.with_context(context).write(order_line)
                elif intervention_product.intervention_id and intervention_product.intervention_id.sale_order_id:
                    sale_line_id = self.env['sale.order.line'].with_context(context).create(order_line)
                    intervention_product.with_context(context).write({'sale_order_line_id':sale_line_id.id})
                
        return True
    
    
    
    @api.model
    def create(self,vals):
        res = super(maintenance_intervention_product, self).create(vals)
        
        if not self.env.context.get("update_from_order",False):
            res.update_values(vals)
        else:
            return False
        
        return res
    
    @api.multi
    def write(self,vals):
        res = super(maintenance_intervention_product, self).write(vals)
        
        if not self.env.context.get("update_from_order",False):
            self.update_values(vals)
        else:
            return False
        
        return res
    
    @api.multi
    def unlink(self):


        
        #sale_line_ids = [intervention_product.sale_order_line_id for intervention_product in self if (intervention_product.sale_order_line_id and intervention_product.intervention_id.state == 'draft')]
        if not self.env.context.get("from_sale_order_line",False):
            sale_lines = self.filtered(lambda r:r.intervention_id.state == 'draft').mapped('sale_order_line_id')
            sale_lines.with_context(from_intervention=True).unlink()
        res = super(maintenance_intervention_product, self).unlink()
        return res


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    intervention_product_id = fields.Many2one('maintenance.intervention.product', string="Maintenance intervention product")
    
    @api.depends('intervention_product_id')
    def update_intervention_product(self):
        self.intervention_product_id.sale_order_line_id = self.id
    
    
    #synchronisation between sale_order_line fields and intervention_product fields
    @api.multi
    def update_values(self, vals):
       
        #break infinite loop#break infinite loop
        if self.env.context.get("update_from_intervention",False):
            return False
        

        for order_line in self:
            if order_line.intervention_product_id and order_line.intervention_product_id.intervention_id.state == 'draft':
                order_line.intervention_product_id.with_context({'update_from_order':True}).write( {
                    'description':order_line.name,
                    'sale_price':order_line.price_unit, 
                    'cost_price':order_line.purchase_price, 
                    'discount':order_line.discount, 
                    'delay':order_line.delay,
                    'route_id':order_line.route_id.id
                })
        return True
    
        
    @api.model
    def create(self,vals):
        res = super(sale_order_line, self).create(vals)
        
        if not self.env.context.get("update_from_intervention",False):
            res.update_values(vals)
        
        return res
    
    @api.multi
    def write(self,vals):
        
        res = super(sale_order_line, self).write(vals)
        
        if not self.env.context.get("update_from_intervention",False):
            self.update_values(vals)
        else:
            return False
        
        return res
    
    @api.multi
    def unlink(self):
        intervention_products = self.filtered(lambda r:r.intervention_product_id.intervention_id.state=="draft").mapped('intervention_product_id')
        #intervention_product_ids = [sale_line.intervention_product_id.id for sale_line in self if (sale_line.intervention_product_id and sale_line.intervention_product_id.intervention_id.state == 'draft')]
        if not self.env.context.get("from_intervention",False):
            intervention_products.with_context(from_sale_order_line=True).unlink()
        res = super(sale_order_line, self).unlink()
        return res


class sale_order(models.Model):
    _inherit = 'sale.order' 
    
    
    @api.multi
    def action_ship_create(self):
        result = super(sale_order, self).action_ship_create()
        
        for order in self:
            if order.intervention_id:
                order.intervention_id.state = 'confirmed'
                
                #find pickings:
                if order.procurement_group_id:
                    picks = set()
                    for proc in order.procurement_group_id.procurement_ids:
                        for move in proc.move_ids:
                            picks.add(move.picking_id)
                    picks = list(picks)
                else:
                    picks = order.picking_ids
                    
                #set intervention_product_id reference for stock_moves
                for picking in picks:
                    picking.origin = str(picking.origin)+' '+order.intervention_id.code
                    if picking.state != 'cancel':
                        for move in picking.move_lines:
                            move.intervention_product_id = move.procurement_id.sale_line_id.intervention_product_id
                            

                ''' TO BE VALIDATED - WE HAVE TO KNOW THE PICKING TYPE ID (DEPENDS FROM THE ROUTE)'''
                '''
                int_picking = None
                out_picking = None
                for pick in order.picking_ids:
                    if pick.picking_type_id.code == 'internal':
                        int_picking = pick
                    elif pick.picking_type_id.code == 'outgoing':
                        out_picking = pick 
                
                if order.intervention_id:
                    if not int_picking:
                        pick_int_name = self.env['ir.sequence'].get('stock.picking.internal')
                        int_picking_id = self.env['stock.picking'].create({
                            'name': pick_int_name,
                            'origin': order.name,
                            'picking_type_id': self.env['stock.picking.type'].search([('code','=','internal')]).id,
                            'state': 'auto',
                            'move_type': order.picking_policy,
                            'sale_id': order.id,
                            'address_id': order.partner_shipping_id.id,
                            'note': order.note,
                            'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
                            'company_id': order.company_id.id,
                        })
                        int_picking_id.signal_workflow('button_confirm')
                        
                    if not out_picking:
                        pick_out_name = self.env['ir.sequence'].get('stock.picking.out')
                        out_picking_id = self.env['stock.picking'].create({
                            'name': pick_out_name,
                            'origin': order.name,
                            'type': self.env['stock.picking.type'].search([('code','=','outgoing')]).id,
                            'state': 'auto',
                            'move_type': order.picking_policy,
                            'sale_id': order.id,
                            'address_id': order.partner_shipping_id.id,
                            'note': order.note,
                            'invoice_state': (order.order_policy=='picking' and '2binvoiced') or 'none',
                            'company_id': order.company_id.id,
                        })
                        out_picking_id.signal_workflow('button_confirm')
                '''
        
        return result              
      
    @api.multi
    def _get_intervention(self):
        result = {}
        for sale in self:            
            interventions = self.env['maintenance.intervention'].search([('sale_order_id','=',sale.id),('state','!=','cancel')])
            if interventions:
                result[sale.id] = interventions[0]
            else:
                result[sale.id] = None
        return result


    @api.depends('procurement_group_id')
    @api.one
    def _get_picking_ids(self):
        
        if not self.procurement_group_id:
            self.picking_ids = None
        else:
            self.picking_ids = self.env['stock.picking'].search([('group_id','=',self.procurement_group_id.id)])
    
    picking_ids = fields.One2many('stock.picking', 'sale_id', compute='_get_picking_ids', store=True)
    intervention_id = fields.Many2one(comodel_name="maintenance.intervention",compute=_get_intervention, store=True)


class maintenance_intervention_task(models.Model):
    _inherit = "maintenance.intervention.task"
    
    #if task is to plan, check availability of related pickings, and set task is NOT to plan, if out picking is available (assigned)
    @api.multi
    @api.depends('date_start','user_id')
    def _get_to_plan(self):
        #res = super(maintenance_intervention_task, self)._get_to_plan()
        
        for task_to_plan in self:
            if task_to_plan.intervention_id and task_to_plan.intervention_id.sale_order_id and task_to_plan.intervention_id.sale_order_id.picking_ids:
                if task_to_plan.intervention_id.state != 'done':
                    available_out_picking_found = False
                    for picking in task_to_plan.intervention_id.sale_order_id.picking_ids:
                        if (picking.state == 'assigned' and picking.picking_type_id.code == 'outgoing') or not picking.move_lines:
                            available_out_picking_found = True
                    task_to_plan.to_plan = available_out_picking_found
                else:
                    task_to_plan.to_plan = False
        
   
    to_plan = fields.Boolean(compute=_get_to_plan, string='To plan',default=False,store=True)

class stock_picking(models.Model):
    _inherit = ['stock.picking']
    
    @api.model
    def _install_sale_id(self):
        self._cr.execute('''DO $$ 
        BEGIN
            BEGIN
                ALTER TABLE stock_picking ADD COLUMN sale_id integer;
                COMMENT ON COLUMN stock_picking.sale_id IS 'Sale Order';
            EXCEPTION
                WHEN duplicate_column THEN RAISE NOTICE 'column sale_id already exists in stock_picking.';
            END;
            update stock_picking set sale_id = so.id from sale_order so where so.procurement_group_id = stock_picking.group_id;
        END;
        $$''')
        return True
  
    @api.multi
    @api.depends('group_id')
    def _get_sale_id(self):
        for pick in self:
            if pick.group_id:
                pick.sale_id=self.env['sale.order'].search([('procurement_group_id', '=', pick.group_id.id)])
            else:
                pick.sale_id=None

    
    sale_id = fields.Many2one('sale.order',compute='_get_sale_id', store=True)
    
    #associate invoice_line with maintenance product
    '''
    DEPRECATED
    def _invoice_line_hook(self, cr, uid, move_line, invoice_line_id):
        self.pool.get("account.invoice.line").write(cr, uid, invoice_line_id, {'intervention_product_id':move_line.intervention_product_id.id})
        return super(stock_picking, self)._invoice_line_hook(cr, uid, move_line, invoice_line_id)
    '''
   
    '''
    DEPRECATED
    def test_done(self, cr, uid, ids, context=None):
        #if it's an empty picking linked to confirmed intervention, it's not done
        result = super(stock_picking, self).test_done(cr, uid, ids, context=None)
        
        if result and len(ids) == 1:
            pick = self.browse(cr, uid, ids[0])
            if pick.type == 'out' and len(pick.move_lines) == 0 and pick.sale_id and pick.sale_id.intervention_id and pick.sale_id.intervention_id.state != 'done':
                return False
        
        return result
    '''
    
    
    
    @api.cr_uid_ids_context
    def do_transfer(self,cr,uid,ids,context=None):
        result = super(stock_picking,self).do_transfer(cr,uid,ids,context=None)
        
        if result and len(ids) == 1:
            picking = self.browse(cr, uid, ids[0])
            if picking.picking_type_id.code == 'outgoing' and len(picking.move_lines) == 0 and picking.sale_id and picking.sale_id.intervention_id and picking.sale_id.intervention_id.state != 'done':
                return False
            
        for picking in self.browse(cr,uid,ids,context=context):
            if picking.picking_type_id.code == 'internal':
                for move in picking.move_lines:
                    if move.intervention_product_id and move.intervention_product_id.intervention_id and move.intervention_product_id.intervention_id.tasks:
                        task_ids = [task.id for task in move.intervention_product_id.intervention_id.tasks]
                        self.pool['maintenance.intervention.task'].write(cr,uid,task_ids, {'to_plan':True},context=context)
 
            
        return result
    
    
    
    
    ''' DEPRECATED see do_transfer
    @api.multi
    def action_done(self):
        """Changes picking state to done by processing the Stock Moves of the Picking

        Normally that happens when the button "Done" is pressed on a Picking view.
        @return: True
        """
        result = super(stock_picking,self).action_done()
        
        if result and len(self) == 1:
            pick = self[0]
            if pick.type == 'out' and len(pick.move_lines) == 0 and pick.sale_id and pick.sale_id.intervention_id and pick.sale_id.intervention_id.state != 'done':
                return False
            
        for picking in self:
            if picking.type == 'internal':
                for move in picking.move_lines:
                    if move.intervention_product_id and move.intervention_product_id.intervention_id and move.intervention_product_id.intervention_id.tasks:
                        task_ids = [task.id for task in move.intervention_product_id.intervention_id.tasks]
                        self.env['maintenance.intervention.task'].write(task_ids, {'to_plan':True})
 
            
        return result
        
    '''
    
    '''
    DEPRECATED
    def test_cancel(self, cr, uid, ids, context=None):
        result = super(stock_picking, self).test_cancel(cr, uid, ids, context=None)
        
        if result and len(ids) == 1:
            pick = self.browse(cr, uid, ids[0])
            #if we validate empty maintenance picking we don't want to consider it as canceled.
            if len(pick.move_lines) == 0 and pick.sale_id and pick.sale_id.intervention_id:
                return False
        
        return result
    '''
    
    '''
    @api.multi
    def action_cancel(self):
        for pick in self:
            pick.move_lines.action_cancel()
        return True
    '''
          
    '''
    DEPRECATED
    def action_done(self, cr, uid, ids, context=None):
        result = super(stock_picking, self).action_done(cr, uid, ids, context)
        #set all tasks of intervention to done
        for picking in self.browse(cr, uid, ids, context):
            if picking.type == 'internal':
                int_move_found = True
                for move in picking.move_lines:
                    if move.intervention_product_id and move.intervention_product_id.intervention_id and move.intervention_product_id.intervention_id.tasks:
                        task_ids = [task.id for task in move.intervention_product_id.intervention_id.tasks]
                        self.pool.get("maintenance.intervention.task").write(cr, uid, task_ids, {'to_plan':True})
        
        return result
    '''
    
class StockMove(models.Model):
    _inherit = 'stock.move'
    
    @api.model
    def _create_invoice_line_from_vals(self, move, invoice_line_vals):
        """ Update invoice line with intervention product
            Deprecate (v6) the stock.picking._invoice_line_hook function
        @param move: Stock move
        @param invoice_line_vals: Values of the invoice line
        @return: The invoice line id
        """
        
        invoice_line_id = super(StockMove,self)._create_invoice_line_from_vals(move,invoice_line_vals)
        
        self.env['account.move.line'].browse(invoice_line_id).intervention_product_id = move.intervention_product_id.id
        
        return invoice_line_id
    
    intervention_product_id =fields.Many2one(comodel_name='maintenance.intervention.product', string="Maintenance intervention product")
    maint_element_id = fields.Many2one(comodel_name="maintenance.element", string="Maintenance element", )
    
    
class ProcurementOrder(models.Model):
    _inherit='procurement.order'
    
    @api.model
    def _run_move_create(self,procurement):
        '''
        When interventions are confirmed (and sale_order), procurement are not always run.
        So, the stock move is not always present.
        When the procurement is run and create the move, we add the link with the intervention product
        '''
    
        res = super(ProcurementOrder,self)._run_move_create(procurement)
        
        # We are looking if sale_order that generated this procurement is linked to an intervention and linke move to spare part
        if 'group_id' in res and 'intervention_product_id' not in res:
            
            if procurement.sale_line_id and procurement.sale_line_id.intervention_product_id:
                res.update({'intervention_product_id':procurement.sale_line_id.intervention_product_id.id})
                        
        return res