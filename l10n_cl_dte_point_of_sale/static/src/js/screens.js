odoo.define('l10n_cl_dte_point_of_sale.screens', function (require) {
"use strict";

  var PaymentScreen = require('point_of_sale.PaymentScreen');
  var core = require('web.core');
  var QWeb = core.qweb;
  var _t = core._t;
  var rpc = require('web.rpc');
  const Registries = require('point_of_sale.Registries');

  const FEPaymentScreen = (PaymentScreen) =>
      class extends PaymentScreen {

        async _finalizeValidation() {
            if ((this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change()) && this.env.pos.config.iface_cashdrawer) {
                this.env.pos.proxy.printer.open_cashbox();
            }

            this.currentOrder.initialize_validation_date();

            if (!this.currentOrder.is_to_invoice() && this.currentOrder.es_boleta() && !this.currentOrder.finalized){
                if(this.currentOrder.es_boleta_exenta()){
                    this.env.pos.pos_session.numero_ordenes_exentas ++;
                    this.currentOrder.orden_numero =this.env.pos.pos_session.numero_ordenes_exentas;
                }else{
                    this.env.pos.pos_session.numero_ordenes ++;
                    this.currentOrder.orden_numero =this.env.pos.pos_session.numero_ordenes;
                }

                var orden_numero = this.currentOrder.orden_numero-1;
                var caf_files = JSON.parse(this.currentOrder.sequence_id.caf_files);
                var start_number = this.currentOrder.sequence_id.l10n_latam_document_type_id.code == 41 ? this.env.pos.pos_session.start_number_exentas : this.env.pos.pos_session.start_number;
                debugger;
                var sii_document_number = this.env.pos.get_next_number(parseInt(orden_numero) + parseInt(start_number), caf_files, start_number);

                this.currentOrder.sii_document_number = sii_document_number;
                var amount = Math.round(this.currentOrder.get_total_with_tax());
                if (amount > 0){
                    this.currentOrder.signature = this.currentOrder.timbrar(this.currentOrder);
                }

                this.currentOrder.barcode = this.currentOrder.barcode_pdf417();
		        this.currentOrder.exento = this.currentOrder.get_total_exento();
            }

            this.currentOrder.finalized = true;

            let syncedOrderBackendIds = [];

            try {
                if (this.currentOrder.is_to_invoice()) {
                    syncedOrderBackendIds = await this.env.pos.push_and_invoice_order(
                        this.currentOrder
                    );
                } else {
                    syncedOrderBackendIds = await this.env.pos.push_single_order(this.currentOrder);
                }
            } catch (error) {
                if (error instanceof Error) {
                    throw error;
                } else {
                    await this._handlePushOrderError(error);
                }
            }
            if (syncedOrderBackendIds.length && this.currentOrder.wait_for_push_order()) {
                const result = await this._postPushOrderResolve(
                    this.currentOrder,
                    syncedOrderBackendIds
                );
                if (!result) {
                    await this.showPopup('ErrorPopup', {
                        title: 'Error: no internet connection.',
                        body: error,
                    });
                }
            }

            this.showScreen(this.nextScreen);

            // If we succeeded in syncing the current order, and
            // there are still other orders that are left unsynced,
            // we ask the user if he is willing to wait and sync them.
            if (syncedOrderBackendIds.length && this.env.pos.db.get_orders().length) {
                const { confirmed } = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Remaining unsynced orders'),
                    body: this.env._t(
                        'There are unsynced orders. Do you want to sync these orders?'
                    ),
                });
                if (confirmed) {
                    // NOTE: Not yet sure if this should be awaited or not.
                    // If awaited, some operations like changing screen
                    // might not work.
                    this.env.pos.push_orders();
                }
            }
        }

      	async _isOrderValid(isForceValidate) {
      		var res = super._isOrderValid(...arguments);
      		if (this.currentOrder.is_to_invoice() || this.currentOrder.es_boleta()){

                var total_tax = this.currentOrder.get_total_tax();
                    if (this.currentOrder.es_boleta_exenta() && total_tax > 0){
            		        this.showPopup('ErrorPopup',{
            		        	'title': "Error de integridad",
            		        	'body': "No pueden haber productos afectos en boleta/factura exenta",
            		        });
            				return false;
            			}else if(this.currentOrder.es_boleta_afecta() && total_tax <= 0){
            		        this.showPopup('ErrorPopup',{
            		        	'title': "Error de integridad",
            		        	'body': "Debe haber almenos un producto afecto",
            		      	});
            				return false;
            		    };
            		};
            		if (this.currentOrder.is_to_invoice() && this.currentOrder.get_client()) {
            			var client = this.currentOrder.get_client();
            			if (!client.street){
            				this.showPopup('ErrorPopup',{
            					'title': 'Datos de Cliente Incompletos',
            					'body':  'El Cliente seleccionado no tiene la dirección, por favor verifique',
            				});
            				return false;
            			}
            			if (!client.vat){
            				this.showPopup('ErrorPopup',{
            					'title': 'Datos de Cliente Incompletos',
            					'body':  'El Cliente seleccionado no tiene RUT, por favor verifique',
            				});
            				return false;
            			}
            			if (!client.l10n_cl_activity_description){
            				this.showPopup('ErrorPopup',{
            					'title': 'Datos de Cliente Incompletos',
            					'body':  'El Cliente seleccionado no tiene Giro, por favor verifique',
            				});
            				return false;
            			}
            		}
            		// if (res && Math.abs(this.currentOrder.get_total_with_tax() <= 0)) {
            		// 	this.showPopup('ErrorPopup',{
            		// 		'title': 'Orden con total 0',
            		// 		'body':  'No puede emitir Pedidos con total 0, por favor asegurese que agrego lineas y que el precio es mayor a cero',
            		// 	});
            		// 	return false;
            		// }
            		if (res && !this.currentOrder.is_to_invoice() && this.currentOrder.es_boleta()){
            			var start_number = 0;
            			var numero_ordenes = 0;
            			if (this.currentOrder.es_boleta_afecta()){
            				start_number = this.env.pos.pos_session.start_number;
            				numero_ordenes = this.env.pos.pos_session.numero_ordenes;
            			} else if (this.currentOrder.es_boleta_exenta()){
            				start_number = this.env.pos.pos_session.start_number_exentas;
            				numero_ordenes = this.env.pos.pos_session.numero_ordenes_exentas;
            			}
            			var caf_files = JSON.parse(this.currentOrder.sequence_id.caf_files);
            			var next_number = start_number + numero_ordenes;
            			next_number = this.env.pos.get_next_number(next_number, caf_files, start_number);
            			var caf_file = false;
            			for (var x in caf_files){
            				if(next_number >= caf_files[x].AUTORIZACION.CAF.DA.RNG.D && next_number <= caf_files[x].AUTORIZACION.CAF.DA.RNG.H){
            					caf_file =caf_files[x]
            				}
            			}
            			//validar que el numero emitido no supere el maximo del folio
            			if (!caf_file){
            				this.showPopup('ErrorPopup',{
            	        		'title': "Sin Folios disponibles",
            	                'body':  _.str.sprintf("No hay CAF para el folio de este documento: %(document_number)s " +
            	              		  "Solicite un nuevo CAF en el sitio www.sii.cl o utilice el asistente apicaf desde la secuencia", {
            	                			document_number: next_number,
            	              		  })
            	            });
            				return false;
        	            }
        		    }
        		    return res;
      	}

      	unset_boleta(){
      		this.currentOrder.unset_boleta();
      	}

      	click_boleta(){
      		this.currentOrder.set_to_invoice(false);
      		if (this.env.pos.pos_session.caf_files && !this.currentOrder.es_boleta_afecta()) {
      			this.currentOrder.set_boleta(true);
      			this.currentOrder.set_tipo_boleta(this.env.pos.config.secuencia_boleta);
      		}else{
                        this.unset_boleta();
                  }
      		this.render();
      	}

      	click_boleta_exenta(){
      		this.currentOrder.set_to_invoice(false);
      		if (this.env.pos.pos_session.caf_files_exentas && !this.currentOrder.es_boleta_exenta()){
      			this.currentOrder.set_boleta(true);
      			this.currentOrder.set_tipo_boleta(this.env.pos.config.secuencia_boleta_exenta);
      		}else{
                        this.unset_boleta();
                  }
      		this.render();
      	}

        toggleIsToInvoice() {
            // click_invoice
            this.unset_boleta();
            this.currentOrder.set_to_invoice(!this.currentOrder.is_to_invoice());
            this.render();
        }


      	click_factura_exenta(){
      		this.unset_boleta();
      		this.currentOrder.set_to_invoice(!this.currentOrder.is_to_invoice());
      		if (this.currentOrder.is_to_invoice()) {
      				this.currentOrder.set_tipo_boleta(this.env.pos.config.secuencia_factura_exenta);
      		} else {
      				this.currentOrder.unset_boleta();
      		}
      		this.render();
      	}

      }
      Registries.Component.extend(PaymentScreen, FEPaymentScreen);

      return FEPaymentScreen;
});

