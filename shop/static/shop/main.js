;( function( $, window, document, undefined ) {
"use strict";

// Some utils
var util = {
    uuid: function() {
        var i, random;
        var uuid = '';

        for (i = 0; i < 32; i++) {
            random = Math.random() * 16 | 0;
            if (i === 8 || i === 12 || i === 16 || i === 20) {
                uuid += '-';
            }
            uuid += (i === 12 ? 4 : (i === 16 ? (random & 3 | 8) : random)).toString(16);
        }

        return uuid;
    },
    pluralize: function(count, word) {
        return count === 1 ? word : word + 's';
    },
    store: function(namespace, data) {
        if (arguments.length > 1) {
            return localStorage.setItem(namespace, JSON.stringify(data));
        } else {
            var store = localStorage.getItem(namespace);
            return (store && JSON.parse(store)) || {};
        }
    },
    cookie: function (name) {
        var value = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    value = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return value;
    }
};

// Line object
function Line(data, qty) {
    $.extend(this, data);
    // this.product_id = product.id;
    // this.product_uom = product.uom;
    // this.product_uom_factor = product.uomFactor;
    // this.product_type = product.type;
    // this.product_name = product.name;
    // this.product_offer_3x2 = product.offer;
    // this.product_price = product.price;
    // if (product.uom == 'gr') {
    //     this.uuid = data.uuid || util.uuid();
    //     this.qty = qty || 100;
    // } else {
    //     this.uuid = product.id;
    //     this.qty = qty || 1;
    // }
    if (data.product_uom == 'gr') {
        this.uuid = data.uuid || util.uuid();
        this.qty = qty || 100;
    } else {
        this.uuid = data.product_id;
        this.qty = qty || 1;
    }
    return this.update();
}
$.extend( Line.prototype, {
    update: function(qty) {
        if (qty) {
            this.qty += qty;
        }
        this.uom_text = util.pluralize(this.qty, this.product_uom);
        this.subtotal = (this.qty * this.product_price) / this.product_uom_factor;
        this.subtotal_str = this.subtotal.toFixed(2);
        return this;
    }
});

// Discount object
function Discount(discount) {
    $.extend(this, discount);
    return this.update();
}
$.extend( Discount.prototype, {
    update: function() {
        if (this.discount_type == 'percent') {
            this.subtotal = -(this.base * this.percent) / 100;
        } else {
            this.subtotal = -(this.base * this.qty);
        }
        this.subtotal_str = this.subtotal.toFixed(2);
        return this;
    }
});


// Cart object
var Cart = {
    init: function(element) {
        this.$el = $(element);
        if (this.$el.length) {
            this.linesLoad();
            this.discounts = [];
            this.total = 0;
            this.total_str = '';
            this.lineTemplate = Handlebars.compile($('#line-template').html());
            this.discountTemplate = Handlebars.compile($('#discount-template').html());
            this.bindEvents().update().render();
        } else {
            this.linesSave({});
        }
        return this;
    },
    bindEvents: function() {
        // Click on products
        $('.product-box').on('click', this.productAdd.bind(this));
        // Click on Clear
        $('#cart-clear').on('click', this.linesClear.bind(this));
        // Click on Submit
        $('#cart-submit').on('click', this.submit.bind(this));
        return this;
    },
    linesLoad: function() {
        var data = util.store('mums-cart'),
            self = this;
        this.lines = {};
        $.each(data, function(idx, value){
            var line = new Line(value);
            self.lines[line.uuid] = line;
        });
        return this;
    },
    linesSave: function(lines) {
        util.store('mums-cart', lines || this.lines);
        return this;
    },
    linesBindEvents: function() {
        // Click on line buttons
        $('.cart-item-minus').on('click', this.lineMinus.bind(this));
        $('.cart-item-plus').on('click', this.linePlus.bind(this));
        $('.cart-item-remove').on('click', this.lineRemove.bind(this));
        return this;
    },
    update: function() {
        var total = 0;
        $.each(this.lines, function(idx, line){
            total += line.subtotal;
        });
        $.each(this.discounts, function(idx, discount){
            total += discount.subtotal;
        });
        this.total = total;
        this.total_str = total.toFixed(2) + ' €';
        this.linesSave();
        return this;
    },
    render: function() {
        // Render lines
        $('#cart-items').html(this.lineTemplate(this.linesGet()));
        this.linesBindEvents();
        if (!$.isEmptyObject(this.lines)) {
            $('#cart-loading').show();
            this.discountsGet()
                .done(this.renderDiscounts.bind(this))
                .fail(this.renderFailed.bind(this))
                .always(this.renderComplete.bind(this));
        } else {
            this.renderComplete();
        }
        return this;
    },
    renderDiscounts: function(data) {
        // Render discounts
        this.discounts = [];
        if ($.isArray(data)) {
            for (var i = 0, len = data.length; i < len; i++) {
                this.discounts.push(new Discount(data[i]));
            }
            $('#cart-discounts').html(this.discountTemplate(this.discounts));
        } else {
            $('#cart-discounts').html(data);
        }
        this.update();
        return this;
    },
    renderFailed: function(xhr, type, msg) {
        $('#cart-discounts').html(msg);
    },
    renderComplete: function() {
        $('#cart-loading').hide();
        // Render total
        $('#cart-total-amount').html(this.total_str);
        if (this.total > 0) {
            $('#cart-total').show(400);
        } else {
            $('#cart-total').hide();
        }
        return this;
    },
    submit: function(e) {
        $('input[name=lines]').val(JSON.stringify(this.linesGet()));
        $('#cart-form').submit();
    },
    discountsGet: function() {
        return $.ajax({
            url: '/discounts/',
            type: 'POST',
            data: {
                lines: JSON.stringify(this.linesGet()),
            },
            beforeSend: function(xhr) {
                xhr.setRequestHeader("X-CSRFToken", util.cookie('csrftoken'));
            },
        });
    },
    lineSearch: function(uuid) {
        return this.lines[uuid] || false;
    },
    lineChange: function(uuid, increment) {
        var line = this.lineSearch(uuid);
        if (line) {
            if (line.product_uom == 'gr') {
                increment = increment * 50;
            }
            line.update(increment);
            if (line.qty <= 0) {
                delete this.lines[line.uuid];
            }
            return this.update().render();
        }
        return this;
    },
    linesClear: function(e) {
        this.lines = {};
        return this.update().render();
    },
    linesGet: function(e) {
        var lines = [];
        for (var k in this.lines) {
            lines.push(this.lines[k]);
        }
        return lines;
    },
    lineRemove: function(e) {
        var line = this.lineSearch($(e.delegateTarget).parent().attr('id'));
        if (line) {
            delete this.lines[line.uuid];
            return this.update().render();
        }
        return this;
    },
    lineMinus: function(e) {
        return this.lineChange($(e.delegateTarget).parent().attr('id'), -1);
    },
    linePlus: function(e) {
        return this.lineChange($(e.delegateTarget).parent().attr('id'), 1);
    },
    productAdd: function(e) {
        var $el = $(e.delegateTarget),
            data = $el.data(),
            line = false;
        if (data.uom == 'ud') {
            line = this.lineSearch(data.id);
        }
        if (line) {
            // Add qty to current line
            line.update(1);
        } else {
            // Create a new line
            line = new Line({
                product_id: data.id,
                product_uom: data.uom,
                product_uom_factor: data.uomFactor,
                product_type: data.type,
                product_name: data.name,
                product_offer_3x2: data.offer,
                product_price: data.price,
            });
            this.lines[line.uuid] = line;
        }
        return this.update().render();
    },
};


$(document).ready(function(){
    Cart.init('#cart');
});

} )( jQuery, window, document );
