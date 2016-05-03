openerp.pos_mrp_product_operation = function(instance, local) {
    module = instance.point_of_sale;
    var _t = instance.web._t;
    var round_pr = instance.web.round_precision;

    module.PosWidget = module.PosWidget.extend({
        build_widgets: function() {
            this._super();
            this.select_operation = new module.SelectOperationPopupWidget(this, {});
            this.screen_selector.popup_set['select-operation'] = this.select_operation;
        },
    });

    module.Order = module.Order.extend({

        zero_pad: function(num, size) {
            var s = ""+num;
            while (s.length < size) {
                s = "0" + s;
            }
            return s;
        },

        generateUniqueId: function() {
            return this.zero_pad(this.pos.pos_session.id,5) + '-' +
                this.zero_pad(this.sequence_number,4);
        },

        setLotNumbers: function() {
            var prefix = this.generateUniqueId();
            var product;
            var index = 1;
            var orderline;
            var orderlines = this.get('orderLines').models;

            for (var i=0, len=orderlines.length; i<len; i++) {
                orderline = orderlines[i];
                product =  orderline.get_product();
                if (
                    !_.isUndefined(product.operations) &&
                    product.operations.length > 0
                ) {
                   orderline.lot_number =
                        prefix + '-' + this.zero_pad(index, 3);
                   index += 1;
                }
            }
        },

        addProduct: function(product, options){
            var res = this._super(product, options);
            this.setLotNumbers();
            return res;
        },

        removeOrderline: function(line){
            var res = this._super(line);
            this.setLotNumbers();
            return res;
        },

        updateProduct: function(product, orderline_id){
            var orderline = this.getOrderline(orderline_id);
            orderline.product = product;
            this.setLotNumbers();
            orderline.trigger('change', orderline);
        },

    });

    module.Orderline = module.Orderline.extend({
        get_unit_price: function(){
            var rounding = this.pos.currency.rounding;
            var price = this.price + this.get_operations_price();
            return round_pr(price, rounding);

        },

        get_operations_price: function(){
            var operation_price = 0;
            if (!_.isUndefined(this.product.operations)) {

                for(var i=0, len=this.product.operations.length; i<len; i++) {
                    operation_price += this.product.operations[i].price;
                }
            }
            return operation_price;
        },

        can_be_merged_with: function(orderline){
            if (!_.isUndefined(orderline.get_product().operations))
                return false;
            return this._super(orderline);
        },

        export_as_JSON: function() {

            var res = this._super();

            var product = this.get_product();
            if (!_.isUndefined(product.operations)) {
                var config = {};
                config.operation_ids = [];
                for(var i=0, len=product.operations.length; i<len; i++) {
                    config.operation_ids.push(product.operations[i].id);
                }
                res.config = config;
                if (this.lot_number) {
                    res.force_lot_number = this.lot_number;
                }
            }

            return res;
        },

        export_for_printing: function() {

            res = this._super();
            res.operations = this.get_product().operations;
            if (this.lot_number) {
                res.lot_number = this.lot_number;
                res.ean13 = create_ean13(this.lot_number);
            }
            return res;
        }

    });

    module.SelectOperationPopupWidget = module.PopUpWidget.extend({
        template:'SelectOperationPopupWidget',

        start: function(){
            this._super();
        },


        show: function(options){

            var options = options || {};
            var self = this;
            var previous;
            this._super();

            this.product = options.product;
            this.categories = self.pos.db.get_categories(
                options.operations || []
            );

            this.appendTo(this.pos_widget.$el);
            this.renderElement();

            var selected = options.selected_operations;
            if (selected.length > 0) {
                for (var i=0, len=selected.length; i<len; i++) {
                    var operation = selected[i];
                    var line = this.$('ul.select-operation:last').clone();
                    line.find('select').val(operation.id).prop('selected', true);
                    line.insertBefore('ul.select-operation:last');
                }

                for (var i=0, len=selected.length; i<len; i++) {
                    var operation = selected[i];
                    this.$('select.select-operation')
                    .children('optgroup')
                    .children('option')
                    .filter('[value="' + operation.id + '"]')
                    .not(':selected')
                    .attr("hidden", "hidden");
                }
            }

            this.$('select.select-operation').focus(function() {
                previous = $(this).val();
            }).click(function() {
                previous = $(this).val();
            }).change(function(e){
                var last_line = self.$('ul.select-operation:last');
                var last_select = self.$('select.select-operation:last');
                if(this.value != 'choice') {
                    if(last_select[0] === e.target) {
                        last_line.clone(true).insertAfter(last_line);
                    };
                    self.$('select.select-operation').not($(this))
                        .children('optgroup')
                        .children('option')
                        .filter('[value="' + this.value + '"]')
                        .attr("hidden", "hidden");
                };
                if(previous != 'choice'){
                    self.$('select.select-operation')
                        .children('optgroup')
                        .children('option')
                        .filter('[value="'+ previous +'"]')
                        .removeProp('hidden');
                };
            });

            this.$('.delete-operation').click(function(e){
                n = self.$('select.select-operation').length;
                last_operation = self.$('.delete-operation:last');
                if(last_operation[0] === e.target && n == 1) {
                    self.$('select.select-operation:last').val('choice').prop('selected', true);
                };
                if (n > 1) {
                    var select = $(this).closest('ul').find('.select-operation');
                    self.$('select.select-operation')
                        .children('optgroup')
                        .children('option')
                        .filter('[value="' + select.val() + '"]')
                        .removeProp('hidden');
                    $(this).closest('ul').remove();
                };
            });

            this.$('.button.cancel').click(function(){
                self.pos_widget.screen_selector.close_popup();
            });
            this.$('.button.ok').click(function(){
                var operations = [];
                self.$('select.select-operation').each(function(){
                    if(this.value != 'choice' && this.value != 'delete') {
                        operations.push(
                            self.pos.db.get_product_by_id(parseInt(this.value))
                        );
                    }
                });
                self.product.operations = operations;
                self.pos_widget.screen_selector.close_popup();
                var product = jQuery.extend(true, {}, self.product);
                order = self.pos.get('selectedOrder');
                if (options.configure_line_id) {
                    order.updateProduct(product, options.configure_line_id);
                }
                else {
                    order.addProduct(product);
                }
          });
        },

    });

    module.OrderWidget = module.OrderWidget.extend({

        render_orderline: function(orderline){
            self = this;
            var template = 'Orderline';
            if (!_.isUndefined(orderline.get_product().operations)) {
                template += 'WithOperations';
            }
            var el_str  = openerp.qweb.render(template, {widget:this, line:orderline});
            var el_node = document.createElement('div');
            el_node.innerHTML = _.str.trim(el_str);
            el_node = el_node.childNodes[0];
            el_node.orderline = orderline;
            el_node.addEventListener('click',this.line_click_handler);
            $(el_node).find('button').on('click', function() {
                var product = orderline.product;
                var operations = self.pos.db.get_operations(product.id);
                params = {
                    product: product,
                    operations: operations,
                    orderline: orderline,
                    configure_line_id: orderline.id,
                    selected_operations: orderline.product.operations
                }
                self.pos.pos_widget.screen_selector.show_popup(
                    'select-operation', params);
            });
            orderline.node = el_node;
            return el_node;
        },

    });

    module.VariantListWidget = module.VariantListWidget.extend({
        init: function(parent, options) {
            var self = this;
            this._super(parent, options);
            this.click_variant_handler_original = this.click_variant_handler;
            this.click_variant_handler = function(event) {
                var product_id = this.dataset['variantId'];
                self.click_variant_handler_original.call(this, event);
                var product = self.pos.db.get_product_by_id(product_id);
                var order = self.pos.get('selectedOrder');
                var last_orderline =
                    order.pos.get('selectedOrder').getLastOrderline();

                // clear previous operations
                var last_product = jQuery.extend({}, product);
                last_product.operation_ids = [];
                last_product.operations = [];
                order.updateProduct(last_product, last_orderline.id);

                // Chain operations screen
                var operations = self.pos.db.get_operations(product_id);
                if (operations.length > 0) {
                    var params = {
                        product: product,
                        operations: operations,
                        options: options,
                        configure_line_id: last_orderline.id,
                        selected_operations: []
                    };
                    self.pos.pos_widget.screen_selector.show_popup(
                        'select-operation', params);
                }
            };
        },
    });

    module.ProductListWidget = module.ProductListWidget.extend({

        init: function(parent, options) {
            this._super(parent, options);
            var self = this;
            this.click_product_handler_original = this.click_product_handler;
            this.click_product_handler = function(event){
                var product = self.pos.db.get_product_by_id(this.dataset['productId']);
                var operations = self.pos.db.get_operations(product.id);
                if (product.product_variant_count == 1 && operations.length > 0) {
                    var params = {
                        product: product,
                        operations: operations,
                        options: options,
                        configure_line_id: false,
                        selected_operations: []
                    };
                    self.pos.pos_widget.screen_selector.show_popup(
                        'select-operation', params);
                } else {
                    self.click_product_handler_original.call(this, event);
                }
            };
        },

        set_product_list: function(product_list){
            var product_list_without_operations = [];
            var product;
            for (var i=0, len=product_list.length; i<len; i++) {
                product = product_list[i];
                if (!product.is_operation) {
                    product_list_without_operations.push(product);
                }
            }
            return this._super(product_list_without_operations);
        },

    });

    module.PosDB = module.PosDB.extend({

        get_operations: function(product_id) {
            var operation_id;
            var operation;
            var operations = [];
            var product = this.get_product_by_id(product_id);

            if (_.isUndefined(product) ||
                _.isUndefined(product.operation_ids)) {
                return operations;
            }

            for (var i=0, len=product.operation_ids.length; i<len; i++) {
                var operation_id = product.operation_ids[i];
                var operation = this.get_product_by_id(operation_id);
                if (! _.isUndefined(operation)) {
                    operations.push(operation);
                };
            }
            return operations;
        },

        get_categories: function(operations) {
            var categories = [];
            var operation;
            for(var i=0, len=operations.length; i < len; i++) {
                operation = operations[i];
                categ_id = operation.pos_categ_id[0];
                if (categ_id in categories) {
                    categories[categ_id].operations.push(operation);
                } else {
                    category = {
                        name: operation.pos_categ_id[1],
                        operations: [operation],
                    };
                    categories[categ_id] = category;
                }
            }

            var categories = Object.keys(categories).map(function(key){
                return categories[key];
            });

            for(var i=0, len=categories.length; i < len; i++) {
                var category = categories[i];
                category.operations.sort(function(a, b) {
                    return a.display_name.localeCompare(b.display_name) > 0;
                })
            }

            categories.sort(function(a, b) {
                return a.name.localeCompare(b.name) > 0;
            });

            return categories;
        },

    });

    module.PosModel = module.PosModel.extend({

        initialize: function(session, attributes) {
            for (var i = 0 ; i < this.models.length; i++) {
                if (this.models[i].model == 'product.product') {
                    this.models[i].fields.push('operation_ids');
                    this.models[i].fields.push('is_operation');
                }
            }
            return this._super(session, attributes);
        }
   });
}
