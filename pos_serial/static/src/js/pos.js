openerp.pos_serial = function (instance) {
    var _t = instance.web._t;
    var QWeb = instance.web.qweb;

    var _super_order = instance.point_of_sale.Order.prototype;
    instance.point_of_sale.Order = instance.point_of_sale.Order.extend({
        addProduct: function(product, options){
            options = options || {};
            var attr = JSON.parse(JSON.stringify(product));
            attr.pos = this.pos;
            attr.order = this;
            var line = new instance.point_of_sale.Orderline({}, {pos: this.pos, order: this, product: product});

            if (product.track_incoming || product.track_all) {
                var self = this;
                new instance.web.Model("stock.production.lot").get_func("search_read")
                            ([['product_id', '=', attr.id],['quant_ids.location_id.usage','=', 'internal']]).pipe(
                    function(result) {
                        if (result) {
                            initial_ids = _.map(result, function(x) {return x['id']});
                            this.pop = new instance.web.form.SelectCreatePopup(this);
                                this.pop.select_element(
                                    'stock.production.lot',
                                    {
                                        title: 'Select serial number for: ' + attr.display_name,
                                        initial_ids: initial_ids,
                                        initial_view: 'search',
                                        disable_multiple_selection: true,
                                        no_create: true
                                    }, [], new instance.web.CompoundContext({}));
                        }
                        this.pop.on("elements_selected", self, function(element_ids) {
                            var dataset = new instance.web.DataSetStatic(self, 'stock.production.lot', {});
                            dataset.name_get(element_ids).done(function(data) {
                                if (data) {
                                    new instance.web.Model("stock.production.lot").get_func("check_stock_lot")(data[0][0]).pipe(
                                        function(lot_res){
                                            if (lot_res > 0) {
                                             line.set_serial_id(data[0][0]);
                                                line.set_serial(data[0][1]);
                                                sr_no = data[0][1];
                                                (self.get('orderLines')).each(_.bind( function(item) {
                                                    if (item.get_product().id == attr.id && item.get_serial() == data[0][1]) {
                                                        alert('Same product is already assigned with same serial number !');
                                                        sr_no = null;
                                                        return false;
                                                    }
                                                }, this));
                                                if (sr_no != null) {
                                                    if(options.quantity !== undefined){
                                                        line.set_quantity(options.quantity);
                                                    }
                                                    if(options.price !== undefined){
                                                        line.set_unit_price(options.price);
                                                    }
                                                    if(options.discount !== undefined){
                                                        line.set_discount(options.discount);
                                                    }
                                                    var last_orderline = self.getLastOrderline();
                                                    if (last_orderline && last_orderline.can_be_merged_with(line) && options.merge !== false){
                                                        last_orderline.merge(line);
                                                    } else {
                                                        self.get('orderLines').add(line);
                                                    }
                                                    self.selectLine(self.getLastOrderline());
                                                }
                                            } else {
                                                alert (_t('Not enough quantity in this serial number !'))
                                            }
                                        });
                                }
                            });
                        });
                    });
            } else {
                _super_order.addProduct.call(this, product, options);
            }
        },
    });

    instance.point_of_sale.ProductCategoriesWidget = instance.point_of_sale.ProductCategoriesWidget.extend({
        perform_search: function(category, query, buy_result){
            if(query){
                var products = this.pos.db.search_product_in_category(category.id,query)
                if(buy_result && products.length === 1){
                    this.pos.get('selectedOrder').addProduct(products[0]);
                }else{
                    this.product_list_widget.set_product_list(products);
                }
            }else{
                var products = this.pos.db.get_product_by_category(this.category.id);
                this.product_list_widget.set_product_list(products);
            }
        },
    });

    instance.point_of_sale.OrderWidget = instance.point_of_sale.OrderWidget.extend({
        set_value: function(val) {
            var order = this.pos.get('selectedOrder');
            this.numpad_state = this.pos_widget.numpad.state;
            var mode = this.numpad_state.get('mode');
            if (this.editable && order.getSelectedLine()) {
                if( mode === 'quantity'){
                    if (val != 'remove' && val != '' && order.getSelectedLine().get_serial()) {
                        alert('Can not change quantity if serial number assigned !');
                    } else {
                        order.getSelectedLine().set_quantity(val);
                    }
                }else if( mode === 'discount'){
                    order.getSelectedLine().set_discount(val);
                }else if( mode === 'price'){
                    order.getSelectedLine().set_unit_price(val);
                }
            }
        },
    });

    var orderline_id = 1;

    var _super_orderline = instance.point_of_sale.Orderline.prototype;
    instance.point_of_sale.Orderline = instance.point_of_sale.Orderline.extend({
        initialize: function(attr,options){
            this.prodlot_id = null;
            this.prodlot_id_id = null;
            _super_orderline.initialize.call(this, attr, options);
        },
        set_serial_id: function(sr_no_id) {
            this.prodlot_id_id = sr_no_id;
        },
        get_serial_id: function() {
            return this.prodlot_id_id;
        },
        set_serial: function(sr_no) {
            this.prodlot_id = sr_no;
        },
        get_serial: function() {
            return this.prodlot_id;
        },
        can_be_merged_with: function(orderline){
            var merged_lines = _super_orderline.can_be_merged_with.call(this, orderline);
            if(this.get_serial()) {
                return false;
            }
            return merged_lines;
        },
        export_as_JSON: function() {
            var lines = _super_orderline.export_as_JSON.call(this);
            new_val = {
                prodlot_id: this.get_serial_id(),
            }
            $.extend(lines, new_val);
            return lines;
        }
    });

    var PosModelSuper = instance.point_of_sale.PosModel
    instance.point_of_sale.PosModel = instance.point_of_sale.PosModel.extend({
        load_server_data: function(){
            var self = this;
            var loaded = PosModelSuper.prototype.load_server_data.call(this);

            loaded = loaded.then(function(){
                return self.fetch(
                    'product.product',
                    ['track_incoming','track_all'],
                    [['sale_ok','=',true],['available_in_pos','=',true]],
                    {}
                );
            }).then(function(products){
                $.each(products, function(){
                    $.extend(self.db.get_product_by_id(this.id) || {}, this)
                });
                return $.when()
            })
            return loaded;
        },
    });

    instance.web.SearchView.include({
        start: function() {
            var self = this;

            this.$view_manager_header = this.$el.parents(".oe_view_manager_header").first();

            this.setup_global_completion();
            this.query = new instance.web.search.SearchQuery()
                    .on('add change reset remove', this.proxy('do_search'))
                    .on('change', this.proxy('renderChangedFacets'))
                    .on('add reset remove', this.proxy('renderFacets'));

            if (this.options.hidden) {
                this.$el.hide();
            }
            if (this.headless) {
                this.ready.resolve();
            } else {
                var load_view = instance.web.fields_view_get({
                    model: this.dataset._model,
                    view_id: this.view_id,
                    view_type: 'search',
                    context: this.dataset.get_context(),
                });

                this.alive($.when(load_view)).then(function (r) {
                    self.fields_view_get.resolve(r);
                    return self.search_view_loaded(r);
                }).fail(function () {
                    self.ready.reject.apply(null, arguments);
                });
            }

            var view_manager = this.getParent();
            while (!(view_manager instanceof instance.web.ViewManager) &&
                    view_manager && view_manager.getParent) {
                view_manager = view_manager.getParent();
            }

        //  if (view_manager) {
        //      this.view_manager = view_manager;
        //      if (view_manager.pop) {
        //          view_manager.pop.on('switch_mode', this, function (e) {
        //              self.drawer.toggle(e === 'graph');
        //          });
        //      } else {
        //          view_manager.on('switch_mode', this, function (e) {
        //                self.drawer.toggle(e === 'graph');
        //            });
        //      }
        //  }
            return $.when(p, this.ready);
        },
    });
}
