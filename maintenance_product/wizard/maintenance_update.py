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
try:
    import simplejson as json
except ImportError:
    import json 

from openerp import models, fields, api, _
from openerp.exceptions import Warning

class maintenance_update_invoice(models.TransientModel):
    _name='maintenance.update.invoice'       
            
    name = fields.Char("Name", size=255)

    @api.model
    def fields_view_get(self,view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        def addString(original_label, label):
            return original_label + '<label colspan="4" string="'+format(label)+'" /><newline />'
        def addTitle(original_label, label):
            return original_label + '<separator colspan="4" string="'+label+'" /><newline />'
        
        result = super(maintenance_update_invoice, self).fields_view_get(view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        
        if view_type=='form':
            if self.env.context.get('active_model',False) == 'maintenance.intervention':
                
                maintenance_intervention_pool = self.env['maintenance.intervention']
                interventions = maintenance_intervention_pool.browse(self.env.context.get('active_id',False))
                warning = addString('', _('Invoices will be re-generated for intervention'))
                
                warning2 = addString('', _('To check them, please go to the corresponding Sale Order'))
                
                
                
                result['arch'] = """
                    <form string="Update pickings">
                        <p>
                        """+warning+"""
                        </p>
                        <footer>
                        <button name="action_generate_invoice" string="Update" type="object" class="oe_highlight" />
                        <button special="cancel" string="Cancel" />
                        </footer>
                    </form>
                    
                """
        return result
    
    @api.multi
    def action_generate_invoice(self):
        maintenance_intervention_pool = self.env['maintenance.intervention']
        
        interventions = maintenance_intervention_pool.browse(self.env.context.get('active_id',False))
        interventions.sudo().with_context(intervention_force_done=True).action_done()
            
        return {'type': 'ir.actions.act_window_close'} 



class maintenance_update_pickings(models.TransientModel):
    _name='maintenance.update.pickings'
    
    name = fields.Char("Name", size=255)

    @api.model
    def fields_view_get(self,view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        def addString(original_label, label):
            return original_label + '<label colspan="4" string="'+label+'" /><newline />'
        def addTitle(original_label, label):
            return original_label + '<separator colspan="4" string="'+label+'" /><newline />'
        
        result = super(maintenance_update_pickings, self).fields_view_get(view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        
        if view_type=='form':
            
            if self.env.context.get('active_model',False) == 'maintenance.intervention':
                
                maintenance_intervention_pool = self.env['maintenance.intervention']
                interventions = maintenance_intervention_pool.browse(self.env.context.get('active_id',False))
                
               
                deleted_done_moves = self.env['stock.move']
                
                
                deleted_product_moves = self.env['stock.move']
                changed_products_lower = self.env['maintenance.intervention.product']
                changed_products_higher = self.env['maintenance.intervention.product']
                added_products = self.env['maintenance.intervention.product']
                
                warning = ""
                for intervention in interventions:
                    if not intervention.sale_order_id or intervention.sale_order_id.state == 'draft':
                        warning = addTitle(warning,'Sale order will be re-generated')
                    else:
                        #find pickings
                        pickings = intervention.sale_order_id.picking_ids 
                        
                        picking = self.env['stock.picking']
                        #products in moves
                        for picking in pickings:
                            #find deleted products
    
                            for move in picking.move_lines:
                                if not move.intervention_product_id:
                                    deleted_product_moves += move
                                    '''
                                    if move.procurement_id.sale_line_id.route_id == 'make_to_order':
                                        deleted_ordered_moves += move
                                    '''
                                    if move.state == 'done':
                                        deleted_done_moves += move
                                        
                        #find added products
                        products_of_moves = picking.mapped('move_lines.intervention_product_id')
                        #products_of_moves = move.intervention_product_id for move in picking.move_lines   
                        for product in intervention.intervention_products:
                            if product not in products_of_moves:
                                added_products += product
                                '''
                                if sale_order_line_pool.product_id_change([], 
                                    intervention.sale_order_id.pricelist_id.id, product.product_id.id, qty=product.quantity, 
                                    partner_id=intervention.sale_order_id.partner_id.id, lang=intervention.sale_order_id.partner_id.lang, fiscal_position=intervention.sale_order_id.fiscal_position, shop_id=intervention.sale_order_id.shop_id.id)['value']['type'] != 'make_to_stock':
                                        added_products_without_stock = added_products_without_stock | product
                                '''        
                                        
                        #find quantity changes
                        for move in picking.move_lines:
                            if move.product_qty < move.intervention_product_id.quantity:
                                changed_products_lower += move.intervention_product_id
                                ''' ELNEO SPECIFIC - TO MOVE
                                if move.sale_line_id and move.sale_line_id.type == 'make_to_order':
                                    added_products_without_stock = added_products_without_stock | move.intervention_product_id
                                '''
                                
                            if move.product_qty > move.intervention_product_id.quantity:
                                changed_products_higher += move.intervention_product_id                                
                                ''' ELNEO SPECIFIC - TO MOVE
                                if move.sale_line_id and move.sale_line_id.type == 'make_to_order':
                                    deleted_ordered_moves += move
                                '''
                
                '''
                if deleted_ordered_moves:
                    warning = addTitle(warning, _("Following deleted products was ordered to supplier : \r\n"))
                for move in deleted_ordered_moves:
                    warning = addString(warning, str(move.product_qty)+" "+move.product_id.name_get()[0][1])
                '''
                    
                if deleted_done_moves:
                    warning = addTitle(warning, _("Following deleted products has been already picked"))
                for move in deleted_done_moves:
                    warning = addString(warning, str(move.product_qty)+" "+move.product_id.name_get()[0][1])
                    
                if deleted_product_moves:
                    warning = addTitle(warning, _("Deleted products"))
                for move in deleted_product_moves:
                    warning = addString(warning, str(move.product_qty)+" "+move.product_id.name_get()[0][1])
                    
                if added_products:
                    warning = addTitle(warning, _("Following products have been added"))
                for product in added_products:
                    warning = addString(warning, str(product.quantity)+" "+product.product_id.name_get()[0][1])
                    
                if changed_products_lower:
                    warning = addTitle(warning, _("Following products quantities have been changed (lower)"))
                for product in changed_products_lower:
                    warning = addString(warning, str(product.quantity)+" "+product.product_id.name_get()[0][1])
                    
                if changed_products_higher:
                    warning = addTitle(warning, _("Following products quantities have been changed (higher)"))
                for product in changed_products_higher:
                    warning = addString(warning, str(product.quantity)+" "+product.product_id.name_get()[0][1])
                
                '''    
                if added_products_without_stock:
                    warning = addTitle(warning, _("Following products has been added, but they should be ordered to supplier"))
                for product in added_products_without_stock:
                    warning = addString(warning, str(product.quantity)+" "+product.product_id.name_get()[0][1])
                '''
                
                if not deleted_product_moves and not deleted_done_moves and not changed_products_lower and not changed_products_higher and not added_products:
                    result['arch'] = """
                    <form string="Update pickings">
                        """+addString('', _('No changes'))+"""
                        <footer>
                        <button special="cancel" string="Ok"/>
                        </footer>
                    </form>"""
                else:
                    result['arch'] = """
                        <form string="Update pickings">
                            """+warning+"""
                            <footer>
                                <button name="action_update" string="Update" type="object" class="oe_highlight"/>
                                <button special="cancel" string="Cancel" />
                            </footer>
                        </form>
                    """
        return result
    
    
    @api.multi
    def action_update(self):
        maintenance_intervention_pool = self.env['maintenance.intervention']
        interventions = maintenance_intervention_pool.browse(self.env.context['active_id'])
        stock_move_pool = self.env['stock.move']
        picking_pool = self.env['stock.picking']
        
        for intervention in interventions:
            order = intervention.sale_order_id
            
            if not order or order.state == 'draft':
                order.unlink()
                intervention.action_confirm()
            else:
                #find pickings
                pickings = intervention.sale_order_id.picking_ids
                out_picking = self.env['stock.picking']
                
                #delete
                for picking in intervention.sale_order_id.picking_ids:
                    
                    #if picking.state == 'done':
                    #    raise osv.except_osv(_('Error'), _('We cannot change done pickings for the moment'))

                    moves_to_delete = picking.move_lines.filtered(lambda r: not r.intervention_product_id)
                    
                    moves_to_delete.write({'state':'draft'})
                    moves_to_delete.unlink()
                    
                    if picking.picking_type_id.code == 'outgoing':
                        out_picking = picking
                        
                #quantity changes
                
                moves_to_check = self.env['stock.move']
                for product in intervention.intervention_products: #loop on intervention products
                    for picking in pickings: #loop on pickings
                        related_moves = picking.move_lines.filtered(lambda r:r.intervention_product_id.id == product.id)
                        
                        
                        move_qty = sum([move.product_qty for move in related_moves])
                        diff_qty = product.quantity - move_qty
                        if diff_qty:
                            if picking.state == 'done' and picking.picking_type_id.code == 'outgoing':
                                raise Warning(_('Error'), _('The delivery picking is done.'))
                            
                            moves_not_done = related_moves.filtered(lambda r:r.state != 'done')
                            
                            moves_done = related_moves.filtered(lambda r:r.state == 'done')

                            if len(moves_not_done) > 1:
                                raise Warning(_('Error'), _('Many moves not done for one product'))
                            
                            if moves_not_done:
                                #find move not done with max quantity
                                move = moves_not_done[0]
                                for move_not_done in moves_not_done:
                                    if move_not_done.product_qty > move.product_qty:
                                        move = move_not_done 
                                        
                                #change it quantity in accordance with difference
                                move.product_uom_qty = move.product_uom_qty+diff_qty
                                move.product_uos_qty = move.product_uos_qty+diff_qty
                                
                                moves_to_check = moves_to_check | move
                                
                            elif related_moves:
                                new_vals = {'product_qty':diff_qty}
                                if diff_qty < 0:
                                    new_vals['state'] = 'assigned'
                                elif related_moves[0].move_dest_id:
                                    new_vals['state'] = 'confirmed'
                                else: 
                                    new_vals['state'] = 'waiting'
                                    
                                new_move = self.env['stock.move'].copy(related_moves[0].id, new_vals)
                                
                                if diff_qty > 0:
                                    moves_to_check = moves_to_check | new_move
                                
                                
                            if picking.state == 'done': 
                                picking.delete_workflow()
                                picking.state = 'draft'
                                picking.create_workflow()
                                picking.signal_workflow('button_confirm')
                                
                                moves_done.state = 'done'
                                
                                
                moves_to_check.action_assign()
                            
                            
                        
                #add
                move_ids = self.env['stock.move']
                products_of_moves = out_picking.mapped('move_lines.intervention_product_id')
                for product in intervention.intervention_products:
                    if product not in products_of_moves:
                        internal_picking = self.env['stock.picking']
                        out_picking = self.env['stock.picking']
                        
                        for picking in pickings:
                            if picking.picking_type_id.code == 'internal':
                                internal_picking = picking
                            if picking.picking_type_id.code == 'outgoing':
                                out_picking = picking
    
                        pickings=self.env['stock.picking']
                        #sort pickings in good order to manage move_dest_id 
                        if internal_picking:
                            pickings += out_picking | internal_picking
                        else:
                            pickings += out_picking
                        
                        new_id = None
                        
                        if not out_picking:
                            name = intervention.warehouse_id.maintenance_picking_type_id.sequence_id._next() or '/'
                            
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
                            
                            pickings += out_picking
                        
                        
                        
                        for picking in pickings:
                            if order.warehouse_id.wh_output_stock_loc_id.usage == 'internal':
                                if picking.picking_type_id.code == 'internal':
                                    location_id = order.warehouse_id.wh_output_stock_loc_id.id #stock
                                    location_dest_id = order.warehouse_id.wh_output_stock_loc_id.id #output
                                elif picking.picking_type_id.code == 'outgoing':
                                    location_id = order.warehouse_id.wh_output_stock_loc_id.id #output
                                    location_dest_id = order.partner_shipping_id.property_stock_customer.id
                                    #location_dest_id = order.warehouse_id.wh_output_stock_loc_id.chained_location_get(order.partner_id, product.product_id)[0] #customer
                            else:
                                raise Warning(_('Error'),_('Not implemented'))
                            
                            
                            values = stock_move_pool.onchange_product_id(prod_id=product.product_id.id, loc_id=location_id,
                                loc_dest_id=location_dest_id, partner_id=order.partner_shipping_id.id)['value']
                            
                            values.update({
                                'name': product.product_id.name_get()[0][1],
                                'picking_id': picking.id,
                                'product_id': product.product_id.id,
                                'date': intervention.date_start or time.strftime('%Y-%m-%d'),
                                'date_expected': intervention.date_start or time.strftime('%Y-%m-%d'),
                                'product_uom_qty': product.quantity,
                                'product_uos_qty': product.quantity,
                                'partner_id': order.partner_shipping_id.id,                            
                                'company_id': order.company_id.id,
                                'state':new_id and 'confirmed' or 'waiting',
                                'intervention_product_id':product.id,
                                'move_dest_id':new_id and new_id.id or False
                            })
                            
                            new_id = self.env['stock.move'].create(values)
                            move_ids = move_ids | new_id
                move_ids.action_assign()
                
                #force availability of empty pickings (or fully available)
                for pick in pickings: #refresh pickings
                    #reinitialize workflows of done pickings
                    if pick.state == 'done' and pick.move_lines.filtered(lambda r:r.state !='done'):
                        pick.state = 'draft'
                        pick.delete_workflow()
                        pick.create_workflow()
                        pick.signal_workflow('button_confirm')
                    
                    #if picking has no unavailable moves : set pick as available

                    not_available_moves = pick.move_lines.filtered(lambda r:r.state in ('confirmed','waiting','done'))
                    if not not_available_moves:
                        pick.force_assign()

        return {'type': 'ir.actions.act_window_close'}
    
    

class MaintenanceProductFlowUpdate(models.TransientModel):
    _name = 'maintenance.product.flow.update'
    
    
    @api.model
    def _update_sale_order(self,part, intervention):
        order_line = intervention.sale_order_id.order_line.filtered(lambda r:r.intervention_product_id==part)
            
        # Create the sale order line
        if not order_line:
            vals = intervention.get_sale_order_line(intervention.sale_order_id,part,intervention.sale_order_id.partner_id)
            order_line = self.env['sale.order.line'].create(vals)
            
            #UPDATE Procurement
            #self._update_or_create_procurement(order_line)
        else:
            # We check quantities
            if order_line.product_uom_qty != part.quantity:
                # The quantity in intervention is greater than in sale
                if order_line.product_uom_qty < part.quantity:
                    order_line.product_uom_qty = part.quantity
                    
                elif order_line.product_uom_qty > part.quantity:
                    order_line.product_uom_qty = part.quantity
                
                #UPDATE Procurement
                self._update_procurement(order_line)
                    
        order_line.button_confirm()
        
    @api.model
    def _get_diff_qty(self,new_qty,procurements):
        diff_qty = 0
        proc_qty = 0
        for procurement in procurements:
            proc_qty += procurement.product_qty
            
        diff_qty = new_qty - proc_qty
            
        return diff_qty
    
    @api.model
    def _update_procurement(self,order_line):
        
        procurements = order_line.procurement_ids
        
        
        out_procurements = procurements.filtered(lambda r:r.location_id.usage =='customer')
        
        out_procurements_running = out_procurements.filtered(lambda r:r.state =='running')
        out_procurements_confirmed = out_procurements.filtered(lambda r:r.state =='confirmed')
        
        if out_procurements_confirmed and out_procurements_confirmed[0]:
            out_procurements_confirmed.product_qty = order_line.product_uom_qty
        elif not out_procurements_confirmed and out_procurements_running:
            diff_qty = self._get_diff_qty(order_line.product_uom_qty, out_procurements_running)
            if diff_qty > 0:
                vals = self.env['sale.order']._prepare_order_line_procurement(order_line.order_id,order_line, group_id=order_line.order_id.procurement_group_id.id)
                vals.update({
                             'product_qty':diff_qty,
                             'product_uos_qty':diff_qty
                             })
                new_procurement = self.env['procurement.order'].create(vals)
                
                new_procurement.run()
            if diff_qty < 0:
                
                
                locations = procurements.mapped('location_id')
                for location in locations:
                    rest_diff_qty = diff_qty
                    # We sort procurements by quantity desc
                    for procurement in (procurements.filtered(lambda r:r.location_id == location).sorted(key=lambda r:r.product_qty,reverse=True)):
                        if procurement.state == 'confirmed':
                            if procurement.product_qty + rest_diff_qty < 0:
                                rest_diff_qty += procurement.product_qty
                                procurement.product_qty = 0
                                procurement.action_cancel()
                            else:
                                procurement.product_qty = procurement.product_qty + rest_diff_qty
                                rest_diff_qty = 0
                        if procurement.state =='running':
                            if procurement.product_qty + rest_diff_qty < 0 and self._check_updatable_procurement_moves(procurement):
                                rest_diff_qty += procurement.product_qty
                                procurement.product_qty = 0
                                self._update_procurement_moves(procurement)
                            else:
                                if self._check_updatable_procurement_moves(procurement):
                                    procurement.product_qty = procurement.product_qty + rest_diff_qty
                                    rest_diff_qty = 0
                                    self._update_procurement_moves(procurement)
                    if rest_diff_qty != 0:
                        raise Warning(_('You try to change quantity for a lower value than exists in pickings for the product : %s') % (procurement.product_id.name))

                    
    @api.model
    def _update_procurement_moves(self,procurement):
        if self._check_updatable_procurement_moves(procurement):
            for move in procurement.move_ids.filtered(lambda r:r.state not in ('cancel','done')):
                move.product_uom_qty = procurement.product_qty
                if move.product_uom_qty == 0:
                    move.action_cancel()
                
    @api.model
    def _check_updatable_procurement_moves(self,procurement):
        res = True
        # We check if we can update the move
        if procurement.rule_id and procurement.rule_id.action == 'buy' and procurement.purchase_line_id and procurement.purchase_line_id.state != 'draft':
            res = False
            
        return res
        
        '''
        if out_procurement:
            out_procurement.cancel()
            
            out_procurement.product_qty = order_line.product_uom_qty
            
            out_procurement.reset_to_confirmed()
            
            out_procurement.run()
        '''
        
        '''
                    
        for procurement in order_line.procurement_ids:
            if procurement.state =='done':
                raise Warning(_('You cannot modify quantities when some procurements are done!'))
            else:
                procurement.product_qty = order_line.product_uom_qty
                
                procurement.run([procurement.id])
        '''        
        return True
        #procurement_group = intervention.sale_order_id.procurement_group_id
        
    @api.model
    def _cancel_link_sale_purchase(self,order_line):
        procurements = self.env['procurement.order'].search([('sale_line_id','=',order_line.id)])
        for procurement in procurements:
            if procurement.purchase_line_id:
                procurement.purchase_line_id = None
                
                
    
    @api.model
    def _cancel_link_incoming_move_dest(self,order_line):
        
        # Cancel link between incoming picking move and destination move if there is a purchase
        incoming_procurements = self.env['procurement.order'].search([('sale_line_id','=',order_line.id),('purchase_line_id','!=',False)])
        if incoming_procurements:
            for incoming_procurement in incoming_procurements:
                moves = incoming_procurement.move_ids.filtered(lambda r:r.state != 'done')
                moves.write({'move_dest_id':False})
    
        return True
        
    @api.model
    def _check_pickings(self,intervention):
        for sale_order_line in intervention.sale_order_id.order_line.filtered(lambda r:r.product_id and r.product_id.type=='product' and not r.intervention_product_id):
            if self.env['procurement.order'].search([('sale_line_id','=',sale_order_line.id),('state','=','done')]):
                raise Warning(_('You have deleted a product that have pickings already done. Please cancel manually products in sale order.'))
            else:
               
                self._cancel_link_incoming_move_dest(sale_order_line)
                
                self._cancel_link_sale_purchase(sale_order_line)
                sale_order_line.button_cancel()
                sale_order_line.unlink()
                
        
    
    @api.multi
    def action_update(self):
        intervention = self.env['maintenance.intervention'].browse(self.env.context.get('active_id',False))
                
        intervention.ensure_one()
        
        self._check_pickings(intervention)
        # Look for changes between sale order and parts
        for part in intervention.intervention_products:
            
            self._update_sale_order(part,intervention)
            
        intervention.sale_order_id.action_ship_create()
      
    @api.model
    def fields_view_get(self,view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        def addString(original_label, label):
            return original_label + '<label colspan="4" string="'+label+'" /><newline />'
        def addTitle(original_label, label):
            return original_label + '<separator colspan="4" string="'+label+'" /><newline />'
        
        result = super(MaintenanceProductFlowUpdate, self).fields_view_get(view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        
        if view_type=='form':
            
            if self.env.context.get('active_model',False) == 'maintenance.intervention':
      
                maintenance_intervention_pool = self.env['maintenance.intervention']
                interventions = maintenance_intervention_pool.browse(self.env.context.get('active_id',False))
                
                
                deleted_done_moves = self.env['stock.move']
                
                
                deleted_product_moves = self.env['stock.move']
                changed_products_lower = self.env['maintenance.intervention.product']
                changed_products_higher = self.env['maintenance.intervention.product']
                added_products = self.env['maintenance.intervention.product']
                
                warning = ""
                for intervention in interventions:
                    if not intervention.sale_order_id or intervention.sale_order_id.state == 'draft':
                        warning = addTitle(warning,'Sale order will be re-generated')
                    else:
                        #find pickings
                        pickings = intervention.sale_order_id.picking_ids 
                        
                        picking = self.env['stock.picking']
                        #products in moves
                        for picking in pickings:
                            #find deleted products
    
                            for move in picking.move_lines:
                                if not move.intervention_product_id:
                                    deleted_product_moves += move
                                    '''
                                    if move.procurement_id.sale_line_id.route_id == 'make_to_order':
                                        deleted_ordered_moves += move
                                    '''
                                    if move.state == 'done':
                                        deleted_done_moves += move
                                        
                        #find added products
                        products_of_moves = picking.mapped('move_lines.intervention_product_id')
                        #products_of_moves = move.intervention_product_id for move in picking.move_lines   
                        for product in intervention.intervention_products:
                            if product not in products_of_moves:
                                added_products += product
                                '''
                                if sale_order_line_pool.product_id_change([], 
                                    intervention.sale_order_id.pricelist_id.id, product.product_id.id, qty=product.quantity, 
                                    partner_id=intervention.sale_order_id.partner_id.id, lang=intervention.sale_order_id.partner_id.lang, fiscal_position=intervention.sale_order_id.fiscal_position, shop_id=intervention.sale_order_id.shop_id.id)['value']['type'] != 'make_to_stock':
                                        added_products_without_stock = added_products_without_stock | product
                                '''        
                                        
                        #find quantity changes
                        for move in picking.move_lines:
                            qty=0
                            for move_compare in picking.move_lines.filtered(lambda r:r.intervention_product_id):
                                qty+=move_compare.product_qty
                                
                            if qty < move.intervention_product_id.quantity and (move.intervention_product_id not in changed_products_lower):
                                changed_products_lower += move.intervention_product_id
                                ''' ELNEO SPECIFIC - TO MOVE
                                if move.sale_line_id and move.sale_line_id.type == 'make_to_order':
                                    added_products_without_stock = added_products_without_stock | move.intervention_product_id
                                '''
                                
                            if qty > move.intervention_product_id.quantity and (move.intervention_product_id not in changed_products_higher):
                                changed_products_higher += move.intervention_product_id                                
                                ''' ELNEO SPECIFIC - TO MOVE
                                if move.sale_line_id and move.sale_line_id.type == 'make_to_order':
                                    deleted_ordered_moves += move
                                '''
                
                '''
                if deleted_ordered_moves:
                    warning = addTitle(warning, _("Following deleted products was ordered to supplier : \r\n"))
                for move in deleted_ordered_moves:
                    warning = addString(warning, str(move.product_qty)+" "+move.product_id.name_get()[0][1])
                '''
                    
                if deleted_done_moves:
                    warning = addTitle(warning, _("Following deleted products has been already picked"))
                for move in deleted_done_moves:
                    warning = addString(warning, str(move.product_qty)+" "+move.product_id.name_get()[0][1])
                    
                if deleted_product_moves:
                    warning = addTitle(warning, _("Deleted products"))
                for move in deleted_product_moves:
                    warning = addString(warning, str(move.product_qty)+" "+move.product_id.name_get()[0][1])
                    
                if added_products:
                    warning = addTitle(warning, _("Following products have been added"))
                for product in added_products:
                    warning = addString(warning, str(product.quantity)+" "+product.product_id.name_get()[0][1])
                    
                if changed_products_lower:
                    warning = addTitle(warning, _("Following products quantities have been changed (lower)"))
                for product in changed_products_lower:
                    warning = addString(warning, str(product.quantity)+" "+product.product_id.name_get()[0][1])
                    
                if changed_products_higher:
                    warning = addTitle(warning, _("Following products quantities have been changed (higher)"))
                for product in changed_products_higher:
                    warning = addString(warning, str(product.quantity)+" "+product.product_id.name_get()[0][1])
                
                '''    
                if added_products_without_stock:
                    warning = addTitle(warning, _("Following products has been added, but they should be ordered to supplier"))
                for product in added_products_without_stock:
                    warning = addString(warning, str(product.quantity)+" "+product.product_id.name_get()[0][1])
                '''
                
                if not deleted_product_moves and not deleted_done_moves and not changed_products_lower and not changed_products_higher and not added_products:
                    result['arch'] = """
                    <form string="Update pickings">
                        """+addString('', _('No changes'))+"""
                        <footer>
                        <button special="cancel" string="Ok"/>
                        </footer>
                    </form>"""
                else:
                    result['arch'] = """
                        <form string="Update pickings">
                            """+warning+"""
                            <footer>
                                <button name="action_update" string="Update" type="object" class="oe_highlight"/>
                                <button special="cancel" string="Cancel" />
                            </footer>
                        </form>
                    """
        return result