# -*- coding: utf-8 -*-

import datetime
from datetime import timedelta
from odoo import http , _
from odoo.http import request
from odoo.addons.website_blog.controllers.main import WebsiteBlog
from odoo.addons.website_sale.controllers.main import WebsiteSale

class WebsiteBlogSnippets(WebsiteBlog):
    @http.route(['/blog/get_blog_content'], type='http', auth='public', website=True)
    def get_blog_content_data(self, **post):
        value={}
        if post.get('blog_config_id') != 'false' and post.get('blog_config_id'):
            collection_data=request.env['blog.configure'].browse(int(post.get('blog_config_id')))
            value.update({'blog_slider':collection_data})
        return request.render("theme_laze.blog_slider_content", value)

class WebsiteSaleSnippets(WebsiteSale):

    def get_slider_layout_design(self, style_id, values):
        """  Main method for get slider template"""
        template_id = request.env['product_slider_common.options'].sudo().browse(int(style_id)).get_external_id().get(
            int(style_id)) + "_template"
        template = request.env['ir.ui.view'].sudo().search(
            [('key', '=', template_id)])
        if template:
            response = http.Response(template=template_id, qcontext=values)
            return response.render()

    @http.route('/shop/get_product_snippet_content', type='json', auth='public', website=True)
    def get_product_snippet_content(self, **kwargs):
        """  get data For dynamic product slider """
        values = {}
        col_list = []
        if kwargs.get('collection_id'):
            add_to_cart = kwargs.get('add_to_cart', False)
            quick_view = kwargs.get('quick_view', False)
            pro_compare = kwargs.get('pro_compare', False)
            pro_wishlist = kwargs.get('pro_wishlist', False)
            pro_ribbon = kwargs.get('pro_ribbon', False)
            pro_ratting = kwargs.get('pro_ratting', False)
            current_filter_id = kwargs.get('current_filter_id', False)
            collection_list = kwargs.get('collection_id').split(',')
            slider_id = [int(i) for i in kwargs.get(
                'slider_type').split('_') if i.isdigit()]
            slider_type = request.env['product_slider.options'].sudo().browse(
                int(slider_id[0]))
            if(slider_id[0] == 0):
                return False
            tmplt_external_id = slider_type.get_external_id().get(slider_type.id) + "_template"
            tmplt = request.website.viewref(tmplt_external_id)
            current_filter = current_filter_id if not current_filter_id else request.env['slider_temp.collection.configure'].sudo().search([
                ('id', '=', int(current_filter_id))])
            for rec in collection_list:
                col_list.append(
                    # request.env['slider_temp.collection.configure'].sudo().browse(int(rec[0])))
                    request.env['slider_temp.collection.configure'].sudo().browse(int(rec)))
            if tmplt:
                values.update({
                    'slider': tmplt._render({
                        'add_to_cart': add_to_cart,
                        'quick_view': quick_view,
                        'pro_compare': pro_compare,
                        'pro_wishlist': pro_wishlist,
                        'pro_ribbon': pro_ribbon,
                        'pro_ratting': pro_ratting,
                        'slider_type': slider_type,
                        'collections': collection_list,
                        'col_list': tuple(col_list),
                        'check_default': False if current_filter_id else True,
                        'active_collection_data': int(current_filter) if current_filter else request.env['slider_temp.collection.configure'].browse(int(collection_list[0])).id,
                    })
                })
                return values
            else:
                return False
        return values

    @http.route('/shop/get_product_variant_snippet_content', type='json', auth='public', website=True)
    def get_product_variant_snippet_content(self, **kwargs):
        """  get data For dynamic product variant slider """
        values = {}
        col_list = []
        if kwargs.get('collection_id'):
            add_to_cart = kwargs.get('add_to_cart', False)
            quick_view = kwargs.get('quick_view', False)
            pro_compare = kwargs.get('pro_compare', False)
            pro_wishlist = kwargs.get('pro_wishlist', False)
            pro_ribbon = kwargs.get('pro_ribbon', False)
            pro_ratting = kwargs.get('pro_ratting', False)
            current_filter_id = kwargs.get('current_filter_id', False)
            collection_list = kwargs.get('collection_id').split(',')
            slider_id = [int(i) for i in kwargs.get(
                'slider_type').split('_') if i.isdigit()]
            slider_type = request.env['product_var_slider.options'].sudo().browse(
                int(slider_id[0]))
            if(slider_id[0] == 0):
                return False
            tmplt_external_id = slider_type.get_external_id().get(slider_type.id) + "_template"
            tmplt = request.website.viewref(tmplt_external_id)
            current_filter = current_filter_id if not current_filter_id else request.env['slider_var.collection.configure'].sudo().search([
                ('id', '=', int(current_filter_id))])
            for rec in collection_list:
                col_list.append(
                    request.env['slider_var.collection.configure'].sudo().browse(int(rec[0])))                    
            if tmplt:
                values.update({
                    'slider': tmplt._render({
                        'add_to_cart': add_to_cart,
                        'quick_view': quick_view,
                        'pro_compare': pro_compare,
                        'pro_wishlist': pro_wishlist,
                        'pro_ribbon': pro_ribbon,
                        'pro_ratting': pro_ratting,
                        'slider_type': slider_type,
                        'collections': collection_list,
                        'col_list': tuple(col_list),
                        'check_default': False if current_filter_id else True,
                        'active_collection_data': int(current_filter) if current_filter else request.env['slider_var.collection.configure'].browse(int(collection_list[0])).id,
                    })
                })
                return values
            else:
                return False
        return values

    @http.route(['/get_prod_quick_view_details'], type='json', auth="public", website=True)
    def get_prod_quick_view_details(self, **kw):
        """  get data for product slider quick view  """
        product_id = int(kw.get('prod_id', 0))
        if product_id > 0:
            product = http.request.env['product.template'].sudo().search(
                [('id', '=', product_id)])
            pricelist = request.website.get_current_pricelist()
            from_currency = request.env.user.company_id.currency_id
            to_currency = pricelist.currency_id

            def compute_currency(price): return from_currency.compute(
                price, to_currency)
            return request.env.ref('atharva_theme_base.as_product_quick_view_holder')._render({
                'product': product,
                'compute_currency': compute_currency or None})
        else:
            return request.env.ref('atharva_theme_base.as_product_quick_view_holder')._render({
                'error': _('There is some problem with this product.!')
            })

    @http.route(['/shop/get_brand_snippet_content'], type='json', auth='public', website=True)
    def get_brand_snippet_content(self, **kwargs):
        """  get data For product brand slider """
        values = {}
        if kwargs.get('collection_id') and kwargs.get('collection_id') != 'false':
            collection_data = request.env['slider_brand.collection.configure'].browse(
                int(kwargs.get('collection_id')))
            if collection_data and collection_data.active:
                values.update({
                    'auto_slider_value': collection_data.auto_slider,
                    'slider_timing': collection_data.slider_time * 1000,
                    'item_count': int(collection_data.item_count),
                })
                slider_type = collection_data.slider_layout_option_id
                tmplt_external_id = collection_data.slider_layout_option_id.get_external_id(
                ).get(collection_data.slider_layout_option_id.id) + "_template"
                tmplt = request.website.viewref(tmplt_external_id)
                if tmplt:
                    values.update({
                        'slider': tmplt._render({
                            'slider_type': slider_type,
                            'obj': collection_data
                        })
                    })
                    return values
                else:
                    return False
            else:
                values.update({
                    'disable_group': 'True'
                })
        return values

    @http.route(['/shop/get_category_snippet_content'], type='json', auth='public', website=True)
    def get_category_snippet_content(self, **kwargs):
        """  get data For product e-commerce category slider """
        values = {}
        if kwargs.get('collection_id') and kwargs.get('collection_id') != 'false':
            collection_data = request.env['slider_cat.collection.configure'].browse(
                int(kwargs.get('collection_id')))
            if collection_data and collection_data.active:
                slider_type = collection_data.slider_layout_option_id
                tmplt_external_id = collection_data.slider_layout_option_id.get_external_id(
                ).get(collection_data.slider_layout_option_id.id) + "_template"
                tmplt = request.website.viewref(tmplt_external_id)
                if tmplt:
                    values.update({
                        'slider': tmplt._render({
                            'slider_type': slider_type,
                            'obj': collection_data
                        })
                    })
                    return values
                else:
                    return False
            else:
                values.update({
                    'disable_group': 'True'
                })
        return values
