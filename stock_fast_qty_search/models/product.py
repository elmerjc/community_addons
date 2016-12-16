# -*- coding: utf-8 -*-
# © 2014-2016 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import api, fields, models
from openerp.addons import decimal_precision as dp
from openerp.tools.float_utils import float_round


class product_product(models.Model):
    _inherit = "product.product"

    stock_quant_ids = fields.One2many(
        'stock.quant', 'product_id',
        help='Technical: used to compute quantities.')
    stock_move_ids = fields.One2many(
        'stock.move', 'product_id',
        help='Technical: used to compute quantities.')
    qty_available = fields.Float(
        'Quantity On Hand', compute='_compute_quantities',
        search='_search_qty_available',
        digits=dp.get_precision('Product Unit of Measure'),
        help="Current quantity of products.\n"
             "In a context with a single Stock Location, this includes "
             "goods stored at this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "stored in the Stock Location of the Warehouse of this Shop, "
             "or any of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")
    virtual_available = fields.Float(
        'Forecast Quantity', compute='_compute_quantities',
        search='_search_virtual_available',
        digits=dp.get_precision('Product Unit of Measure'),
        help="Forecast quantity (computed as Quantity On Hand "
             "- Outgoing + Incoming)\n"
             "In a context with a single Stock Location, this includes "
             "goods stored in this location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")
    incoming_qty = fields.Float(
        'Incoming', compute='_compute_quantities',
        search='_search_incoming_qty',
        digits=dp.get_precision('Product Unit of Measure'),
        help="Quantity of products that are planned to arrive.\n"
             "In a context with a single Stock Location, this includes "
             "goods arriving to this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods arriving to the Stock Location of this Warehouse, or "
             "any of its children.\n"
             "Otherwise, this includes goods arriving to any Stock "
             "Location with 'internal' type.")
    outgoing_qty = fields.Float(
        'Outgoing', compute='_compute_quantities',
        search='_search_outgoing_qty',
        digits=dp.get_precision('Product Unit of Measure'),
        help="Quantity of products that are planned to leave.\n"
             "In a context with a single Stock Location, this includes "
             "goods leaving this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods leaving the Stock Location of this Warehouse, or "
             "any of its children.\n"
             "Otherwise, this includes goods leaving any Stock "
             "Location with 'internal' type.")

    @api.depends('stock_quant_ids', 'stock_move_ids')
    def _compute_quantities(self):
        """ this method call standard method
        """
        res = self._product_available()
        # for fas qty compute use :
        # res = self._product_available_sql()
        for product in self:
            product.qty_available = res[product.id]['qty_available']
            product.incoming_qty = res[product.id]['incoming_qty']
            product.outgoing_qty = res[product.id]['outgoing_qty']
            product.virtual_available = res[product.id]['virtual_available']

    def _product_available_sql(self):
        # DOTO Check qty computed
        domain_move_in, domain_move_out, domain_quant = \
            self._get_product_qyt_domain()
        moves_in = self._read_group_by_sql(
            'stock.move', domain_move_in, having=False)
        moves_out = self._read_group_by_sql(
            'stock.move', domain_move_out, having=False)
        quants = self._read_group_by_sql(
            'stock.quant', domain_quant, having=False)
        res = {}
        # To improuve perf avoid brows product to get uom rounding
        self._cr.execute("""select p.id, m.rounding  FROM product_product p
            inner join product_template t on p.product_tmpl_id = t.id
            inner join product_uom m on t.uom_id = m.id
            where p.id in %s""", (tuple(self.ids),))
        p_rounding = dict(self._cr.fetchall())

        for id in self.ids:
            qty_available = float_round(
                quants.get(
                    id, 0.0), precision_rounding=p_rounding.get(
                    id, 0.01))
            incoming_qty = float_round(
                moves_in.get(
                    id, 0.0), precision_rounding=p_rounding.get(
                    id, 0.01))
            outgoing_qty = float_round(
                moves_out.get(
                    id, 0.0), precision_rounding=p_rounding.get(
                    id, 0.01))
            virtual_available = float_round(
                quants.get(id, 0.0) +
                moves_in.get(id, 0.0) -
                moves_out.get(id, 0.0),
                precision_rounding=p_rounding.get(id, 0.01))
            res[id] = {
                'qty_available': qty_available,
                'incoming_qty': incoming_qty,
                'outgoing_qty': outgoing_qty,
                'virtual_available': virtual_available,
            }
        return res

    def _search_qty_available(self, operator, value):
        # ---> Set BreakPoint
        import pdb
        pdb.set_trace()
        return self._fast_search_product_quantity(
            [('qty_available', operator, value)])

    def _search_virtual_available(self, operator, value):
        return self._fast_search_product_quantity(
            [('virtual_available', operator, value)])

    def _search_incoming_qty(self, operator, value):
        return self._fast_search_product_quantity(

            [('incoming_qty', operator, value)])

    def _search_outgoing_qty(self, operator, value):
        return self._fast_search_product_quantity(
            [('outgoing_qty', operator, value)])

    def _fast_search_product_quantity(self, domain):
        res = []
        # ---> Set BreakPoint
        import pdb
        pdb.set_trace()
        for field, operator, value in domain:
            # to prevent sql injections
            assert field in ('qty_available', 'virtual_available',
                             'incoming_qty', 'outgoing_qty'), \
                'Invalid domain left operand'
            assert operator in ('<', '>', '=', '!=', '<=',
                                '>='), 'Invalid domain operator'
            assert isinstance(
                value, (float, int)), 'Invalid domain right operand'

            if operator == '=':
                operator = '=='
            res.append(
                ('id', 'in', self._search_qty(field, operator, value)))

        return res

    def _search_qty(self, field, operator, value):
        domain_move_in, domain_move_out, domain_quant = \
            self._get_product_qyt_domain([])
        res = {}
        if field == 'incoming_qty':
            res = self._read_group_by_sql(
                'stock.move', domain_move_in,
                having=[(field, operator, value)])
        elif field == 'outgoing_qty':
            res = self._read_group_by_sql(
                'stock.move', domain_move_out,
                having=[(field, operator, value)])
        elif field == 'qty_available':
            res = self._read_group_by_sql(
                'stock.quant', domain_quant,
                having=[(field, operator, value)])
        elif field == 'virtual_available':
            res = self._search_virtual_qty(
                domain_move_in, domain_move_out, domain_quant,
                domain_virtual_qty=[(field, operator, value)])

        # value == 0 must also inculd all product without stock move or quants
        unmoved_prod = {}
        if value == 0.0 and operator in ('==', '>=', '<='):
            if field == 'incoming_qty':
                unmoved_prod = self._get_unmoved_product(
                    'stock.quant', domain_move_in)
            elif field == 'outgoing_qty':
                unmoved_prod = self._get_unmoved_product(
                    'stock.move', domain_move_out)
            elif field == 'qty_available':
                unmoved_prod = self._get_unmoved_product(
                    'stock.move', domain_quant)

        res = list(res) + list(unmoved_prod)
        return res

    def _get_product_qyt_domain(self, for_search=False):
        domain_products =\
            (not for_search) and [('product_id', 'in', self.ids)] or []
        domain_quant, domain_move_in, domain_move_out = [], [], []
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = \
            self._get_domain_locations()
        domain_move_in += self._get_domain_dates() + \
            [('state', 'not in', ('done', 'cancel', 'draft'))] +\
            domain_products
        domain_move_out += self._get_domain_dates() + \
            [('state', 'not in', ('done', 'cancel', 'draft'))] +\
            domain_products
        domain_quant += domain_products

        lot_id = self._context.get('lot_id')
        owner_id = self._context.get('owner_id')
        package_id = self._context.get('package_id')

        if lot_id:
            domain_quant.append(('lot_id', '=', lot_id))
        if owner_id:
            domain_quant.append(('owner_id', '=', owner_id))
            owner_domain = ('restrict_partner_id', '=', owner_id)
            domain_move_in.append(owner_domain)
            domain_move_out.append(owner_domain)
        if package_id:
            domain_quant.append(('package_id', '=', package_id))

        domain_move_in += domain_move_in_loc
        domain_move_out += domain_move_out_loc
        domain_quant += domain_quant_loc
        return domain_move_in, domain_move_out, domain_quant

    def _get_groupby_query(self, model_name, domain, having=False):
        having = having or []
        model = self.pool.get(model_name)
        query_obj = model._where_calc(self._cr, self._uid, domain)
        model._apply_ir_rules(self._cr, self._uid, query_obj, 'read')
        from_clause, where_clause, where_clause_params = query_obj.get_sql()

        select_clauses = {
            'stock.move':
            """%(table)s.product_id, sum(%(table)s.product_qty) as quantity"""
            % {'table': model._table},
            'stock.quant':
            """%(table)s.product_id, sum(%(table)s.qty) as quantity"""
            % {'table': model._table},
        }
        agrs_fields = {
            'stock.move': 'product_qty',
            'stock.quant': 'qty',
        }
        having_conditions = []
        for field, operator, value in having:
            group_operator = model._fields[
                agrs_fields[model_name]].group_operator or 'sum'
            having_conditions.append(
                '%s(%s) %s' %
                (group_operator, agrs_fields[model_name], operator) + ' %s')
            where_clause_params.append(value)
        having_clause = having_conditions and (
            ' HAVING ' + ' AND '.join(having_conditions)) or ''

        query = """ SELECT
        %(select)s
        FROM %(from)s
        WHERE %(where)s
        GROUP BY product_id %(having)s """ % {
            'select': select_clauses[model_name],
            'from': from_clause,
            'where': where_clause or ' 1=1 ',
            'having': having_clause,
        }
        return query, where_clause_params

    def _read_group_by_sql(self, model_name, domain, having=False):
        having = having or []
        query, where_clause_params = self._get_groupby_query(
            model_name, domain, having=having)
        self._cr.execute(query, where_clause_params)
        return dict(self._cr.fetchall())

    def _search_virtual_qty(self, domain_move_in, domain_move_out,
                            domain_quant, domain_virtual_qty=False):
        """
        Virtual quatity = qty_available + incoming_qty - outgoing_qty
        make search in python side make search verry slows
        if we have 100K products or more.
        The solve this we make request in sql side.
        To be able to seaech in sql we have to get make a querry
        witch return for each product qty_available, incoming_qty,
        outgoing_qty before filtring value.
        For all unmoved products (whitou stock_move or stock_quants qty = 0 )
        """

        domain_virtual_qty = domain_virtual_qty or []
        query_quant1, where_clause_params_quant1 = self._get_groupby_query(
            'stock.quant', domain_quant, having=False)
        query_quant2, where_clause_params_quant2 = \
            self._get_unmoved_product_query('stock.quant', domain_quant)
        query_in1, where_clause_params_in1 = self._get_groupby_query(
            'stock.move', domain_move_in, having=False)
        query_in2, where_clause_params_in2 = self._get_unmoved_product_query(
            'stock.move', domain_move_in)

        query_out1, where_clause_params_out1 = self._get_groupby_query(
            'stock.move', domain_move_out, having=False)
        query_out2, where_clause_params_out2 = self._get_unmoved_product_query(
            'stock.move', domain_move_out)

        where_clause_params_v_qty = where_clause_params_quant1 + \
            where_clause_params_quant2 + where_clause_params_in1 + \
            where_clause_params_in2 + where_clause_params_out1 + \
            where_clause_params_out2

        query_quant = query_quant1 + " UNION " + query_quant2
        query_in = query_in1 + " UNION " + query_in2
        query_out = query_out1 + " UNION " + query_out2

        v_qty_conditions = []
        # in virtual quatity having condition wil be expressed as where
        # condition
        for field, operator, value in domain_virtual_qty:
            v_qty_conditions.append(
                """(query_quant.quantity + query_in.quantity -
                query_out.quantity) %s""" %
                (operator,) + ' %s')
            where_clause_params_v_qty.append(value)
        v_qty_clause = v_qty_conditions and (
            ' WHERE ' + ' AND '.join(v_qty_conditions)) or ''

        v_qty_query = """SELECT query_quant.product_id as id,
            (query_quant.quantity + query_in.quantity - query_out.quantity)
            as quantity FROM
            (%(query_quant)s) AS query_quant
            INNER JOIN (%(query_in)s) AS query_in
            ON query_in.product_id = query_quant.product_id
            INNER JOIN  (%(query_out)s) AS query_out
            ON query_out.product_id = query_quant.product_id
            %(where)s
                """ % {
            'query_quant': query_quant,
            'query_in': query_in,
            'query_out': query_out,
            'where': v_qty_clause or ' ',
        }
        self._cr.execute(v_qty_query, where_clause_params_v_qty)
        return dict(self._cr.fetchall())

    def _get_unmoved_product_query(self, model_name, domain):
        model = self.pool.get(model_name)
        query_obj = model._where_calc(self._cr, self._uid, domain)
        model._apply_ir_rules(self._cr, self._uid, query_obj, 'read')
        from_clause, where_clause, where_clause_params = query_obj.get_sql()

        select_clauses = {
            'stock.move': """%(table)s.product_id, 0 as quantity"""
            % {'table': model._table},
            'stock.quant': """%(table)s.product_id, 0 as quantity"""
            % {'table': model._table},
        }

        query = """( SELECT id, 0 from product_product WHERE active = True
        EXCEPT SELECT
            %(select)s
            FROM %(from)s
            WHERE %(where)s
        ) """ % {
            'select': select_clauses[model_name],
            'from': from_clause,
            'where': where_clause or ' 1=1 ',
        }

        return query, where_clause_params

    def _get_unmoved_product(self, model_name, domain):
        query, where_clause_params = self._get_unmoved_product_query(
            model_name, domain)
        self._cr.execute(query, where_clause_params)
        return dict(self._cr.fetchall())

