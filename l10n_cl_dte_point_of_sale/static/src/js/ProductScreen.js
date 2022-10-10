odoo.define('l10n_cl_dte_point_of_sale.ProductScreen', function (require) {
"use strict";

  var ProductScreen = require('point_of_sale.ProductScreen');
  var core = require('web.core');
  var QWeb = core.qweb;
  var _t = core._t;
  var rpc = require('web.rpc');
  const Registries = require('point_of_sale.Registries');


    const FEProductScreen = (ProductScreen) =>
      class extends ProductScreen{
        _onClickPay() {
        var order = this.currentOrder;
            if (order.get_tax_details().length > 0){
				var tax_amount = order.get_tax_details()[0]['amount'];
				if (tax_amount > 0){
					this.click_boleta();
				}
				else if (tax_amount == 0){
					this.click_boleta_exenta();
				}
			}
			else{
				this.click_boleta_exenta();
			}

            this.showScreen('PaymentScreen');
        }

    unset_boleta(order){
		order.unset_boleta();
		// $('.js_boleta').removeClass('highlight');
		// $('.js_boleta_exenta').removeClass('highlight');
	}
	click_boleta(){
		var order = this.currentOrder;
		order.set_to_invoice(false);
		$('.js_invoice').removeClass('highlight');
		// if (this.pos.pos_session.caf_files && (order.es_boleta_exenta() || !order.es_boleta())) { //suspecteous.
		if (this.env.pos.pos_session.caf_files){
			this.unset_boleta(order);
			order.set_boleta(true);
			order.set_tipo_boleta(this.env.pos.config.secuencia_boleta);
			$('.js_boleta_exenta').removeClass('highlight');
			$('.js_boleta').addClass('highlight');
			return;
		}
		this.unset_boleta(order);
	}
	click_boleta_exenta(){
		var order = this.currentOrder;
		order.set_to_invoice(false);
		$('.js_invoice').removeClass('highlight');
		if (this.env.pos.pos_session.caf_files_exentas && !order.es_boleta_exenta()){
			this.unset_boleta(order);
			order.set_boleta(true);
			order.set_tipo_boleta(this.env.pos.config.secuencia_boleta_exenta);
			$('.js_boleta').removeClass('highlight');
			$('.js_boleta_exenta').addClass('highlight');
			return;
		}
		this.unset_boleta(order);
	}


      }
      Registries.Component.extend(ProductScreen, FEProductScreen);

      return FEProductScreen;
});