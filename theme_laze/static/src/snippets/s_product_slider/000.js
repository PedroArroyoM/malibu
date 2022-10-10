odoo.define('theme_laze.s_product_slider',function(require){
'use strict';

var sAnimation = require('website.content.snippets.animation');
var concurrency = require('web.concurrency');
var ajax = require('web.ajax');
var publicWidget = require('web.public.widget');
var sale = new sAnimation.registry.WebsiteSale();


if($(".oe_website_sale").length === 0){
    $("div#wrap").addClass("oe_website_sale");
}
sAnimation.registry.product_slider_actions = sAnimation.Class.extend({
    selector : ".as_product_slider",
    disabledInEditableMode: false,
    start: function (editable_mode) {
        var self = this;
        if (self.editableMode){
            self.$target.find('div').empty().append('<div class="seaction-head"><h2>' + self.$target.attr("data-collection_name") + '</h2></div>');
        }
        if (!self.editableMode) {
            this.getProductData();
        }
    },
    initialize_owl: function (autoplay=false, items=4, slider_timing=5000) {
        $('.as-product-carousel').owlCarousel({
            loop: true,
            rewind: true,
            margin: 10,
            nav: true,
            lazyLoad:true,
            dots: false,
            navText : ['<span aria-label="Previous"></span>', '<span aria-label="Next"></span>'],
            autoplay: autoplay || false,
            autoplaySpeed: parseInt(slider_timing) || 5000,
            autoplayTimeout: 3000,
            autoplayHoverPause:true,
            items: items,
            responsive: {
                0: {
                    items: 1,
                },
                481: {
                    items: 2,
                },
                768: {
                    items: 2,
                },
                1024: {
                    items: 4,
                },
                1200: {
                    items: items,
                }
            },
        });
    },
    getProductData: function(){
        var self = this;
        ajax.jsonRpc("/shop/get_product_snippet_content", 'call', {
            'collection_id': self.$target.attr('data-collection_id') || 0,
            'slider_type': self.$target.attr('data-slider_type') || '',
            'add_to_cart' : self.$target.attr('data-add_to_cart') || '',
            'quick_view' : self.$target.attr('data-quick_view') || '',
            'pro_compare' : self.$target.attr('data-pro_compare') || '',
            'pro_wishlist' : self.$target.attr('data-pro_wishlist') || '',
            'pro_ribbon' : self.$target.attr('data-pro_ribbon') || '',
            'pro_ratting' : self.$target.attr('data-pro_ratting') || '',
        }).then(function( data ) {
            if(data){
                var autoplay = self.$target.attr('data-prod-auto') || false;
                var prod_count = parseInt(self.$target.attr('data-prod-count')) || 4;
                var slider_timing = parseInt(self.$target.attr('data-slider_timing')) || 0;
                self.$target.find('div').empty().append(data.slider);
                self.initialize_owl(eval(autoplay), prod_count, slider_timing);
                $(self.$target).find(".as_collection_change").first().addClass("active");
                self.get_slider_data($(self.$target));
            }
        });
    },
    get_slider_data: function(target){
        var self = this;
        $(target).find(".as_collection_change").click(function(){
            $('.as_theme_loader_layout').removeClass('d-none');
            var current_filter_id = $(this).attr('data-id');
            $(target).find(".as_collection_change").removeClass('active');
            $(this).addClass('active');
            var current_filter = $(target).find("div[filter-id='" + current_filter_id + "']");
            var slider_id = $(target).attr("data-collection_id");
            $(target).find(".as_collection_data").hide()
            if (current_filter.length == 1){
                $('.as_theme_loader_layout').addClass('d-none');
                $('.as_theme_loader_layout').addClass('hidden');
                current_filter.show()
            }else{
                ajax.jsonRpc("/shop/get_product_snippet_content", 'call',
                    {
                        'collection_id': self.$target.attr('data-collection_id'),
                        'slider_type': self.$target.attr('data-slider_type') || '',
                        'add_to_cart' : self.$target.attr('data-add_to_cart') || '',
                        'quick_view' : self.$target.attr('data-quick_view') || '',
                        'pro_compare' : self.$target.attr('data-pro_compare') || '',
                        'pro_wishlist' : self.$target.attr('data-pro_wishlist') || '',
                        'pro_ribbon' : self.$target.attr('data-pro_ribbon') || '',
                        'pro_ratting' : self.$target.attr('data-pro_ratting') || '',
                        'current_filter_id':current_filter_id,
                    }
                ).then(function (data) {
                    $('.as_theme_loader_layout').addClass('d-none');
                    $('.as_theme_loader_layout').addClass('hidden');
                    var autoplay = self.$target.attr('data-prod-auto') || false;
                    var prod_count = parseInt(self.$target.attr('data-prod-count')) || 4;
                    var slider_timing = parseInt(self.$target.attr('data-slider_timing')) || 0;
                    $(target).find(".as_data_container").append($(data.slider).find(".as_collection_data"));
                    self.initialize_owl(eval(autoplay), prod_count, slider_timing);
                });
            }
        });
    },
});
});
