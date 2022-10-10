odoo.define('l10n_cl_dte_point_of_sale.models', function (require) {
"use strict";

// implementaciónen el lado del cliente de firma
var models = require('point_of_sale.models');
const { Gui } = require('point_of_sale.Gui');
var utils = require('web.utils');
var core = require('web.core');
var _t = core._t;

var modules = models.PosModel.prototype.models;
var round_pr = utils.round_precision;

for(var i=0; i<modules.length; i++){
	var model=modules[i];
	if(model.model === 'res.company'){
		model.fields.push('l10n_cl_activity_description','street','city', 'l10n_cl_dte_resolution_number', 'l10n_cl_dte_resolution_date');
	}
	if(model.model === 'res.partner'){
		model.fields.push('vat','l10n_cl_activity_description','l10n_cl_sii_taxpayer_type', 'state_id', 'city_id', 'l10n_cl_dte_email');//, 'sync');
	}
	if(model.model === 'pos.session'){
		model.fields.push('caf_files', 'caf_files_exentas', 'start_number', 'start_number_exentas', 'numero_ordenes', 'numero_ordenes_exentas');
	}
	if (model.model == 'product.product') {
		model.fields.push('name');
	}
	if (model.model == 'res.country') {
		model.fields.push('code');
	}
}

models.load_models({
	model: 'res.partner',
	fields: ['vat',],
	domain: function(self){ return [['id','=', self.company.partner_id[0]]]; },
      	loaded: function(self, dn){
      		self.company.vat = dn[0].vat;
      	},
});

models.load_models({
	model: 'ir.sequence',
	fields: ['id', 'l10n_latam_document_type_id'],
	domain: function(self){ return [['id', '=', self.config.secuencia_boleta[0]]]; },
		loaded: function(self, doc){
			if(doc.length > 0){
				self.config.secuencia_boleta = doc[0];
			}
		}
});

models.load_models({
	model: 'ir.sequence',
	fields: ['id', 'l10n_latam_document_type_id'],
	domain: function(self){ return [['id', '=', self.config.secuencia_boleta_exenta[0]]]; },
		loaded: function(self, doc){
			if (doc.length > 0){
				self.config.secuencia_boleta_exenta = doc[0];
			}
		}
});

models.load_models({
	model: 'l10n_latam.document.type',
	fields: ['id', 'name', 'code'],
	domain: function(self){ return [['id', '=', (self.config.secuencia_boleta ? self.config.secuencia_boleta.l10n_latam_document_type_id[0]: false)]]; },
		loaded: function(self, doc){
			if(doc.length > 0){
				self.config.secuencia_boleta.l10n_latam_document_type_id = doc[0];
				self.config.secuencia_boleta.caf_files = self.pos_session.caf_files;
			}
		}
});

models.load_models({
	model: 'l10n_latam.document.type',
	fields: ['id', 'name', 'code'],
	domain: function(self){ return [['id', '=', (self.config.secuencia_boleta_exenta ? self.config.secuencia_boleta_exenta.l10n_latam_document_type_id[0]:false)]]; },
		loaded: function(self, doc){
			if(doc.length > 0){
				self.config.secuencia_boleta_exenta.l10n_latam_document_type_id = doc[0];
				self.config.secuencia_boleta_exenta.caf_files = self.pos_session.caf_files_exentas;
			}
		}
});

models.load_models({
	model: 'l10n_latam.document.type',
	fields: ['id', 'name', 'code'],
		loaded: function(self, dt){
			self.sii_document_types = dt;
		},
});


models.load_models({
	model: 'res.country.state',
	fields: ['id', 'name', 'country_id'],
		loaded: function(self, st){
			self.states = st;
		},
});

models.load_models({
	model: 'res.city',
	fields: ['id', 'name', 'state_id', 'country_id'],
		loaded: function(self, ct){
			self.cities = ct;
			self.cities_by_id = {};
            _.each(ct, function(city){
                self.cities_by_id[city.id] = city;
            });
		},
});




var PosModelSuper = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
	folios_boleta_exenta: function(){
		return this.pos_session.caf_files_exentas;
	},
	folios_boleta_afecta: function(){
		return this.pos_session.caf_files;
	},
	get_next_number: function(sii_document_number, caf_files, start_number){
	debugger;
		var start_caf_file = false;
		for (var x in caf_files){
			if(parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.D) <= parseInt(start_number)
					&& parseInt(start_number) <= parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.H)){
				start_caf_file = caf_files[x];
			}
		}
		var caf_file = false;
		var gived = 0;
		for (var x in caf_files){
			if(parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.D) <= sii_document_number &&
					sii_document_number >= parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.H)){
				caf_file = caf_files[x];
			}else if( !caf_file || ( sii_document_number < parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.D) &&
					sii_document_number < parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.D) &&
					parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.D) < parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.D)
			)){// menor de los superiores caf
				caf_file = caf_files[x];
			}
			if (sii_document_number > parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.H) && caf_files[x] != start_caf_file){
				gived += (parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.H) - parseInt(caf_files[x].AUTORIZACION.CAF.DA.RNG.D)) +1;
			}
		}
		if (!caf_file){
			return sii_document_number;
		}
		if(sii_document_number < parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.D)){
			var dif = sii_document_number - ((parseInt(start_caf_file.AUTORIZACION.CAF.DA.RNG.H) - start_number) + 1 + gived);
			sii_document_number = parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.D) + dif;
			if (sii_document_number >  parseInt(caf_file.AUTORIZACION.CAF.DA.RNG.H)){
				sii_document_number = get_next_number(sii_document_number);
			}
		}
		return sii_document_number;
	},

});

var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
	initialize: function(attr, options) {
		_super_order.initialize.call(this,attr,options);
		debugger;
		this.unset_boleta();
		if (this.pos.config.marcar === 'boleta' && this.pos.config.secuencia_boleta){
			this.set_boleta(true);
			this.set_tipo_boleta(this.pos.config.secuencia_boleta);
		}else if (this.pos.config.marcar === 'boleta_exenta' && this.pos.config.secuencia_boleta_exenta){
			this.set_boleta(true);
			this.set_tipo_boleta(this.pos.config.secuencia_boleta_exenta);
		}else if (this.pos.config.marcar === 'factura'){
			this.set_to_invoice(true);
		}
		if(this.es_boleta()){
			//this.signature = this.signature || false;
			//this.sii_document_number = this.sii_document_number || false;
			this.orden_numero = this.orden_numero ||this.pos.pos_session.numero_ordenes;
			if (this.orden_numero <= 0){
			debugger;
				this.orden_numero = 1;
			}
		}
	},
	export_as_JSON: function() {
		var json = _super_order.export_as_JSON.apply(this,arguments);
		json.sequence_id = this.sequence_id;
		debugger;
		json.sii_document_number = this.sii_document_number;
		json.signature = this.signature;
		json.orden_numero = this.orden_numero;
		json.barcode = this.barcode;
		json.exento = this.exento;
		json.finalized = this.finalized;
		return json;
	},
    init_from_JSON: function(json) {// carga pedido individual
    	_super_order.init_from_JSON.apply(this,arguments);
    	this.sequence_id = json.sequence_id;
    	this.sii_document_number = json.sii_document_number;
    	this.signature = json.signature;
    	this.barcode = json.barcode;
    	this.exento = json.exento;
    	this.orden_numero = json.orden_numero;
		this.finalized = json.finalized;
	},
	export_for_printing: function() {
		var json = _super_order.export_for_printing.apply(this,arguments);
		json.company.vat = this.pos.company.vat;
		json.company.l10n_cl_activity_description = this.pos.company.l10n_cl_activity_description;
		json.company.street = this.pos.company.street;
		json.company.city = this.pos.company.city;
		json.company.l10n_cl_dte_resolution_number = this.pos.company.l10n_cl_dte_resolution_number;
		json.company.l10n_cl_dte_resolution_date = this.pos.company.l10n_cl_dte_resolution_date;
		debugger;
		json.sii_document_number = this.sii_document_number;
		json.orden_numero = this.orden_numero;
		if(this.sequence_id){
			json.nombre_documento = this.sequence_id.l10n_latam_document_type_id.name;
		}
		var d = this.creation_date;
		var curr_date = this.completa_cero(d.getDate());
		var curr_month = this.completa_cero(d.getMonth() + 1); // Months
																	// are zero
																	// based
		var curr_year = d.getFullYear();
		var hours = d.getHours();
		var minutes = d.getMinutes();
		var seconds = d.getSeconds();
		var date = curr_year + '-' + curr_month + '-' + curr_date + ' ' +
			this.completa_cero(hours) + ':' + this.completa_cero(minutes) + ':' + this.completa_cero(seconds);
		json.creation_date = date;
		//json.barcode = this.barcode_pdf417();
		//json.exento = this.get_total_exento();
		json.referencias = [];
		json.client = this.get('client');
		json.barcode = this.barcode;
		json.exento = this.exento;
		return json;
	},

	/*push_single_order: function(order, opts) {
	    _super_order.push_single_order.apply(this,arguments);
	    debugger;

		if(order && order.es_boleta() && !this.finalized){
			var orden_numero = order.orden_numero -1;
			var caf_files = JSON.parse(order.sequence_id.caf_files);
			var start_number = order.sequence_id.l10n_latam_document_type_id.code == 41 ? this.pos_session.start_number_exentas : this.pos_session.start_number;

			var sii_document_number = this.get_next_number(parseInt(orden_numero) + parseInt(start_number), caf_files, start_number);

			order.sii_document_number = sii_document_number;
			var amount = Math.round(order.get_total_with_tax());
			if (amount > 0){
				order.signature = order.timbrar(order);
			}
	    }
		return PosModelSuper.push_order.apply(this, [order, opts]);
	},

	initialize_validation_date: function(order, opts) {
        _super_order.initialize_validation_date.apply(this, arguments);
		debugger;
		var order = this;
		if(order && !order.is_to_invoice() && order.es_boleta() && !this.finalized){
			var orden_numero = order.orden_numero-1;
			var caf_files = JSON.parse(order.sequence_id.caf_files);
			var start_number = order.sequence_id.l10n_latam_document_type_id.code == 41 ? this.pos.pos_session.start_number_exentas : this.pos.pos_session.start_number;
            debugger;
			var sii_document_number = this.pos.get_next_number(parseInt(orden_numero) + parseInt(start_number), caf_files, start_number);

			order.sii_document_number = sii_document_number;
			var amount = Math.round(order.get_total_with_tax());
			if (amount > 0){
				order.signature = order.timbrar(order);
			}
	    }

	},

	*/

	initialize_validation_date: function(){
	//TODO: el momento en que se incrementa el numero de la boleta deberia ser cuando se guarda en la bbdd no cuando se manda
	debugger;
		_super_order.initialize_validation_date.apply(this,arguments);

	},
  get_total_with_tax: function() {
  	_super_order.get_total_with_tax.apply(this,arguments);
  	return round_pr(this.orderlines.reduce((function(sum, orderLine) {
  		return sum + orderLine.get_price_with_tax();
  	}), 0), this.pos.currency.rounding);
	},
	set_tipo_boleta: function(tipo_boleta){
		this.sequence_id = tipo_boleta;
	},
	set_boleta: function(boleta){
		this.boleta = boleta;
	},
	unset_boleta: function(){
		this.set_tipo_boleta(false);
		this.set_boleta(false);
		this.orden_numero = false;
		this.sii_document_number = false;
	},
    // esto devolvera True si es Boleta(independiente si es exenta o afecta)
    // para diferenciar solo si es una factura o una boleta
	es_boleta: function(){
		return this.boleta;
	},
    // esto devolvera True si es Boleta exenta(code = 41)
	es_boleta_exenta: function(check_marcar=false){
		if(!this.es_boleta()){
			return false;
		}
		if (parseInt(this.sequence_id.l10n_latam_document_type_id.code) === 41){
			return true;
		}
		return false;
    },
    // esto devolvera True si es Boleta afecta(code = 39)
	es_boleta_afecta: function(check_marcar=false){
		if(!this.es_boleta()){
			return false;
		}
		if (parseInt(this.sequence_id.l10n_latam_document_type_id.code) === 39){
			return true;
		}
		return false;
	},
    get_total_exento:function(){
    	var taxes =  this.pos.taxes;
    	var exento = 0;
    	this.orderlines.each(function(line){
    		/*var product =  line.get_product();
    		var taxes_ids = product.taxes_id;
    		_(taxes_ids).each(function(el){
    			_.detect(taxes,function(t){
    				if(t.id === el && t.amount === 0){
    					exento += (line.get_unit_price() * line.get_quantity());
    				}
    			});
    		});*/
    		if(line.get_price_without_tax() == line.get_price_with_tax()){
                exento = line.get_price_with_tax();
    		}
    	});
    	return exento;
    },
	completa_cero(val){
    	if (parseInt(val) < 10){
    		return '0' + val;
    	}
    	return val;
    },
    encode: function(caracter){
    	var string = "";
    	for (var i=0; i< caracter.length; i++){
    		var l = caracter[i];
    		if(l.charCodeAt() >= 160){
    			l = "&#"+ l.charCodeAt()+';';
    		}
    		if(i < 40){
    			string += l;
    		}
    	}
    	return string;
	},
	timbrar: function(order){
		if (order.signature){ // no firmar otra vez
			return order.signature;
		}
		var caf_files = JSON.parse(order.sequence_id.caf_files);
		var caf_file = false;
		for (var x in caf_files){
			if(caf_files[x].AUTORIZACION.CAF.DA.RNG.D <= order.sii_document_number && order.sii_document_number <= caf_files[x].AUTORIZACION.CAF.DA.RNG.H){
				caf_file =caf_files[x]
			}
		}
		if (!caf_file){
		    Gui.showPopup('Error', {
                        title: this.comp.env._t('Sii'),
                        body: this.comp.env._t('No quedan más Folios Disponibles.'),
                    });

			return false;
		}
		var priv_key = caf_file.AUTORIZACION.RSASK;
		var pki = forge.pki;
		var privateKey = pki.privateKeyFromPem(priv_key);
		var md = forge.md.sha1.create();
		var partner_id = this.get_client();
		if(!partner_id){
			partner_id = {};
			partner_id.name = "Usuario Anonimo";
		}
		if(!partner_id.vat){
			partner_id.vat = "66666666-6";
		}
		var product_name = false;
		var ols = order.orderlines.models;
		var ols2 = ols;
		for (var p in ols){
			var es_menor = true;
			for(var i in ols2){
				if(ols[p].id !== ols2[i].id && ols[p].id > ols2[i].id){
					es_menor = false;
				}
				if(es_menor === true){
					product_name = this.encode(ols[p].product.name);
				}
			}
		}
		var d = order.validation_date;
		var curr_date = this.completa_cero(d.getDate());
		var curr_month = this.completa_cero(d.getMonth() + 1); // Months
																// are zero
																// based
		var curr_year = d.getFullYear();
		var hours = d.getHours();
		var minutes = d.getMinutes();
		var seconds = d.getSeconds();
		var date = curr_year + '-' + curr_month + '-' + curr_date + 'T' +
			this.completa_cero(hours) + ':' + this.completa_cero(minutes) + ':' + this.completa_cero(seconds);
		var rut_emisor = this.pos.company.vat.replace('.','').replace('.','');
		if (rut_emisor.charAt(0) == "0"){
			rut_emisor = rut_emisor.substr(1);
		}
		var string='<DD>' +
			'<RE>' + rut_emisor + '</RE>' +
			'<TD>' + order.sequence_id.l10n_latam_document_type_id.code + '</TD>' +
			'<F>' + order.sii_document_number + '</F>' +
			'<FE>' + curr_year + '-' + curr_month + '-' + curr_date + '</FE>' +
			'<RR>' + partner_id.vat.replace('.','').replace('.','') +'</RR>' +
			'<RSR>' + this.encode(partner_id.name) + '</RSR>' +
			'<MNT>' + Math.round(this.get_total_with_tax()) + '</MNT>' +
			'<IT1>' + product_name + '</IT1>' +
			'<CAF version="1.0"><DA><RE>' + caf_file.AUTORIZACION.CAF.DA.RE + '</RE>' +
				'<RS>' + caf_file.AUTORIZACION.CAF.DA.RS + '</RS>' +
				'<TD>' + caf_file.AUTORIZACION.CAF.DA.TD + '</TD>' +
				'<RNG><D>' + caf_file.AUTORIZACION.CAF.DA.RNG.D + '</D><H>' + caf_file.AUTORIZACION.CAF.DA.RNG.H + '</H></RNG>' +
				'<FA>' + caf_file.AUTORIZACION.CAF.DA.FA + '</FA>' +
				'<RSAPK><M>' + caf_file.AUTORIZACION.CAF.DA.RSAPK.M + '</M><E>' + caf_file.AUTORIZACION.CAF.DA.RSAPK.E + '</E></RSAPK>' +
				'<IDK>' + caf_file.AUTORIZACION.CAF.DA.IDK + '</IDK>' +
				'</DA>' +
				'<FRMA algoritmo="SHA1withRSA">' + caf_file.AUTORIZACION.CAF.FRMA["#text"] + '</FRMA>' +
			'</CAF>'+
			'<TSTED>' + date + '</TSTED></DD>';
		md.update(string);
		var signature = forge.util.encode64(privateKey.sign(md));
		string = '<TED version="1.0">' + string + '<FRMT algoritmo="SHA1withRSA">' + signature + '</FRMT></TED>';
		return string;
	},
    barcode_pdf417: function(){
    	var order = this.pos.get_order();
    	if (!order.sequence_id || !order.sii_document_number){
    		return false;
    	}
    	PDF417.ROWHEIGHT = 2;
    	PDF417.init(order.signature, 6);
    	var barcode = PDF417.getBarcodeArray();
    	var bw = 2;
    	var bh = 2;
    	var canvas = document.createElement('canvas');
    	canvas.width = bw * barcode['num_cols'];
    	canvas.height = 255;
    	var ctx = canvas.getContext('2d');
    	var y = 0;
    	for (var r = 0; r < barcode['num_rows']; ++r) {
    		var x = 0;
    		for (var c = 0; c < barcode['num_cols']; ++c) {
    			if (barcode['bcode'][r][c] == 1) {
    				ctx.fillRect(x, y, bw, bh);
    			}
    			x += bw;
    		}
    		y += bh;
    	}
    	return canvas.toDataURL("image/png");
	},

});

});
