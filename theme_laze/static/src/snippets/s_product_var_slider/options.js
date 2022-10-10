odoo.define('theme_laze.s_product_var_slider_options',function(require){
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var weContext = require('web_editor.context');
var options = require('web_editor.snippets.options');
var qweb = core.qweb;
var _t = core._t;

ajax.loadXML('/theme_laze/static/src/xml/product_variant_slider_popup.xml', core.qweb);

options.registry['product_variant_slider_actions'] = options.Class.extend({
    popup_template_id: "main_product_variant_slider_layout_template",
    popup_title: _t("Select Product Variant Slider Layout"),

    start: function () {
        var self = this;
        return this._super.apply(this, arguments);
    },

    product_variant_slider_configure: function(previewMode, value){
        var self = this;

        var $modal = $(qweb.render('theme_laze.p_var_slider_popup_template'));
        $modal.modal();

        self._rpc({
            model: 'slider_var.collection.configure',
            method: 'name_search',
            args: ['', [['website_id','in',[false,parseInt($('html').attr('data-website-id'))]]]],
        }).then(function(collection){
                var pro_col_ele =  $modal.find('select[name="pro_collection"]');
                if(collection.length > 0){
                    for(var i = 0; i < collection.length; i++){
                        pro_col_ele.append("<option value='" + collection[i][0] + "'>" + collection[i][1] + "</option>");
                    }
                }

                var selected_collection = self.$target.attr('data-collection_id');
                selected_collection = selected_collection.split(',');
                $modal.find('#multiselect_two').multiselect('select',selected_collection);

                self._rpc({
                    model: 'product_var_slider.options',
                    method: 'name_search',
                    args: ['', []],
                    context: weContext.get()
                }).then(function(slider){

                    var $sliders_ele =  $modal.find('select[name="slider_type"]');

                    if(slider.length > 0){
                        var slider = slider.sort((a,b) => a[1].toUpperCase().localeCompare(b[1].toUpperCase()));
                        for(var i = 0; i < slider.length; i++){
                            $sliders_ele.append("<option value='slider_layout_" + slider[i][0] + "'>" + slider[i][1] + "</option>");
                        }
                    }
                    var selected_slider = self.$target.attr('data-slider_type');
                    $sliders_ele.val(selected_slider);
                    $modal.find('form .p_slider_sample_view img.snip_sample_img').attr('src', '/theme_laze/static/src/img/snippets/product_slider/' + $sliders_ele.val() + '.png');

                    var sel_slider_name = $modal.find( "select[name='slider_type'] option:selected" ).text();
                    var check_slider = sel_slider_name.split(' ');

                    if (check_slider[0] == 'Grid') {

                        var $prod_auto = $modal.find('#prod-auto');
                        $prod_auto.prop('checked',false);
                        $modal.find('div.prod_count').hide();
                        $modal.find('div.auto_load').hide();
                        $modal.find('div.slider_time').hide();
                    }else{
                        $modal.find('div.prod_count').show();
                        $modal.find('div.auto_load').show();
                        self.$target.attr('data-prod-auto') == 'true' ? $modal.find('div.slider_time').show() : $modal.find('div.slider_time').hide();
                    }
                });
        });

        $modal.on('click', '.btn_apply', function(){

            var $collection_list = $modal.find("select[name='pro_collection']");
            var $slider_ele = $modal.find("select[name='slider_type']");
            var $prod_count = $modal.find('#prod-count');
            var $prod_auto = $modal.find('#prod-auto');
            var $slider_time = $modal.find('#slider_time');
            var $add_to_cart = $modal.find('#add_to_cart');
            var $quick_view = $modal.find('#quick_view');
            var $pro_compare = $modal.find('#pro_compare');
            var $pro_wishlist = $modal.find('#pro_wishlist');
            var $pro_ribbon = $modal.find('#pro_ribbon');
            var $pro_ratting = $modal.find('#pro_ratting');

            $prod_auto.is(':checked') == true ? self.$target.attr('data-prod-auto', true) :  self.$target.attr('data-prod-auto', false);
            $add_to_cart.is(':checked') == true ? self.$target.attr('data-add_to_cart', true) : self.$target.attr('data-add_to_cart', false);
            $quick_view.is(':checked') == true ? self.$target.attr('data-quick_view', true) : self.$target.attr('data-quick_view', false);
            $pro_compare.is(':checked') == true ? self.$target.attr('data-pro_compare', true) : self.$target.attr('data-pro_compare', false);
            $pro_wishlist.is(':checked') == true ? self.$target.attr('data-pro_wishlist', true) : self.$target.attr('data-pro_wishlist', false);
            $pro_ribbon.is(':checked') == true ? self.$target.attr('data-pro_ribbon', true) : self.$target.attr('data-pro_ribbon', false);
            $pro_ratting.is(':checked') == true ? self.$target.attr('data-pro_ratting', true) : self.$target.attr('data-pro_ratting', false);

            self.$target.attr('data-collection_id', $collection_list.val());
            self.$target.attr('data-slider_type', $slider_ele.val());
            self.$target.attr('data-prod-count', $prod_count.val());
            self.$target.attr('data-slider_time', $slider_time.val());

            var collection_name = $modal.find("select[name='pro_collection'] option:selected").text();
            if(!collection_name)
                collection_name = 'NO COLLECTION SELECTED';
            self.$target.attr('data-collection_name', collection_name);
            self.$target.find('div').empty().append('<div class="seaction-head"><h2>' + collection_name + '</h2></div>');

        });


        $modal.on('change', $modal.find("select[name='slider_type']"), function (e){
            var $slider_sel = $(this).find("select[name='slider_type'] option:selected");
            $modal.find('form .p_slider_sample_view img.snip_sample_img').attr('src', '/theme_laze/static/src/img/snippets/product_slider/' + $slider_sel.val() + '.png');

            if ($slider_sel.text().indexOf('Grid') != -1) {
                var $prod_auto = $modal.find('#prod-auto');
                $prod_auto.prop('checked',false);
                $modal.find('div.prod_count').hide();
                $modal.find('div.auto_load').hide();
            }
            else{
                $modal.find("#prod-auto").parent().show();
                $modal.find('div.prod_count').show();
                $modal.find('div.auto_load').show();
            }
        });
        $modal.on('change', $modal.find("input[name='prod-auto']"), function(e){

            if ($modal.find('input#prod-auto').is(':checked')) {
                $modal.find('div.slider_time').show();
            }
            else {
                $modal.find('div.slider_time').hide();
            }
        });

        self.$target.attr('data-prod-auto') == 'true' ? $modal.find("form input[id='prod-auto']").prop('checked', true) : $modal.find("form input[id='prod-auto']").prop('checked', false);
        self.$target.attr('data-add_to_cart') == 'true' ? $modal.find("form input[id='add_to_cart']").prop('checked', true) : $modal.find("form input[id='add_to_cart']").prop('checked', false);
        self.$target.attr('data-quick_view') == 'true' ? $modal.find("form input[id='quick_view']").prop('checked', true) :  $modal.find("form input[id='quick_view']").prop('checked', false);
        self.$target.attr('data-pro_compare') == 'true' ? $modal.find("form input[id='pro_compare']").prop('checked', true) : $modal.find("form input[id='pro_compare']").prop('checked', false);
        self.$target.attr('data-pro_wishlist') == 'true' ? $modal.find("form input[id='pro_wishlist']").prop('checked', true) : $modal.find("form input[id='pro_wishlist']").prop('checked', false);
        self.$target.attr('data-pro_ribbon') == 'true' ? $modal.find("form input[id='pro_ribbon']").prop('checked', true) : $modal.find("form input[id='pro_ribbon']").prop('checked', false);
        self.$target.attr('data-pro_ratting') == 'true' ? $modal.find("form input[id='pro_ratting']").prop('checked', true) : $modal.find("form input[id='pro_ratting']").prop('checked', false);
        $modal.find('#prod-count').val(self.$target.attr('data-prod-count'));
        $modal.find('#slider_time').val(self.$target.attr('data-slider_time'));
    },
    onBuilt: function(){
        var self = this;
        this._super();
        this.product_variant_slider_configure('click');
    },
    cleanForSave: function () {
        this.$target.find('div').empty();
        $('.as_product_variant_slider').find('div').empty();
        var model = this.$target.parent().attr('data-oe-model');
        if(model){
            this.$target.parent().addClass('o_editable o_dirty');
        }
    },
});
});
