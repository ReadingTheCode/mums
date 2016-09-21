import json
from decimal import Decimal
from django.test import TestCase

from .models import Order, Product


class OrderTests(TestCase):
    fixtures = ['products']

    def testOrderFromPOST(self):
        firstname = 'Piper'
        lastname = 'Chapman'
        email = 'piper@chapman.com'
        values = {
            'firstname': firstname,
            'lastname': lastname,
            'email': email,
            'lines': json.dumps([
                {'product_id': 1, 'qty': 150},  # 150grs Risotto
                {'product_id': 2, 'qty': 100},  # 100grs Ensalada de espinacas
                {'product_id': 4, 'qty': 250},  # 250grs Pollo al curry
                {'product_id': 4, 'qty': 150},  # 150grs Pollo al curry
                {'product_id': 6, 'qty': 2},    # 2x Pizza primavera
                {'product_id': 8, 'qty': 2},    # 2x Agua
                {'product_id': 9, 'qty': 4},    # 4x Zumo de naranja
                {'product_id': 10, 'qty': 6},   # 6x Manzana
                {'product_id': 11, 'qty': 3},   # 3x Tarta de queso
            ]),
        }
        order = Order.fromPOST(values)
        self.assertTrue(order)
        self.assertTrue(order.id)
        self.assertEqual(firstname, order.firstname)
        self.assertEqual(lastname, order.lastname)
        self.assertEqual(email, order.email)
        self.assertEqual(1, order.number)
        # Check order lines subtotals
        orderlines = order.orderline_set.all()
        self.assertEqual(5.25, float(orderlines[0].subtotal))
        self.assertEqual(1.65, float(orderlines[1].subtotal))
        self.assertEqual(3.88, float(orderlines[2].subtotal))
        self.assertEqual(2.32, float(orderlines[3].subtotal))
        self.assertEqual(4.00, float(orderlines[4].subtotal))
        self.assertEqual(2.40, float(orderlines[5].subtotal))
        self.assertEqual(8.00, float(orderlines[6].subtotal))
        self.assertEqual(12.00, float(orderlines[7].subtotal))
        self.assertEqual(7.5, float(orderlines[8].subtotal))
        # Check discounts subtotals
        discounts = order.discount_set.all()
        self.assertEqual(-1.69, float(discounts[0].subtotal))
        self.assertEqual('percent', discounts[0].discount_type)
        self.assertEqual(-0.97, float(discounts[1].subtotal))
        self.assertEqual('percent', discounts[1].discount_type)
        self.assertEqual(-1.58, float(discounts[2].subtotal))
        self.assertEqual('percent', discounts[2].discount_type)
        self.assertEqual(-1.26, float(discounts[3].subtotal))
        self.assertEqual('percent', discounts[3].discount_type)
        self.assertEqual(-1.20, float(discounts[4].subtotal))
        self.assertEqual('percent', discounts[4].discount_type)
        self.assertEqual(-1.20, float(discounts[5].subtotal))
        self.assertEqual('percent', discounts[5].discount_type)
        self.assertEqual(-2.50, float(discounts[6].subtotal))
        self.assertEqual('qty', discounts[6].discount_type)
        # Check total
        self.assertEqual(36.60, float(order.total))
        return values

    def testOrderNumber(self):
        values = {
            'firstname': 'Walter',
            'lastname': 'White',
            'email': 'ww@breakingbad.com',
            'lines': json.dumps([
                {'product_id': 1, 'qty': 150},  # 150grs Risotto
            ]),
        }
        order = Order.fromPOST(values)
        self.assertEqual(1, order.number)

        values = {
            'firstname': 'Piper',
            'lastname': 'Chapman',
            'email': 'piper@chapman.com',
            'lines': json.dumps([
                {'product_id': 2, 'qty': 100},  # 100grs Ensalada de espinacas
            ]),
        }
        order = Order.fromPOST(values)
        self.assertEqual(2, order.number)

    def testDiscountsGetNone(self):
        # No lines
        lines = []
        discounts = Order.discountsCalculate(lines)
        self.assertFalse(discounts)

        # No discounts
        lines = [{
            'product_name': 'Water',
            'product_uom': 'ud',
            'product_uom_factor': 1,
            'product_type': Product.DRINK,
            'product_offer_3x2': True,
            'product_price': Decimal(1.50),
            'qty': 2,
        }, {
            'product_name': 'Apple pie',
            'product_uom': 'ud',
            'product_uom_factor': 1,
            'product_type': Product.DESSERT,
            'product_offer_3x2': False,
            'product_price': Decimal(2.50),
            'qty': 3,
        }]
        discounts = Order.discountsCalculate(lines)
        self.assertFalse(discounts)

    def testDiscountsGetMenu(self):
        # Menu discount
        lines = [{
            'product_name': 'Risotto',
            'product_uom': 'gr',
            'product_uom_factor': 100,
            'product_type': Product.MAIN,
            'product_offer_3x2': False,
            'product_price': Decimal(3.50),
            'qty': 200,
        }, {
            'product_name': 'Water',
            'product_uom': 'ud',
            'product_uom_factor': 1,
            'product_type': Product.DRINK,
            'product_offer_3x2': True,
            'product_price': Decimal(1.50),
            'qty': 1,
        }, {
            'product_name': 'Soda',
            'product_uom': 'ud',
            'product_uom_factor': 1,
            'product_type': Product.DRINK,
            'product_offer_3x2': True,
            'product_price': Decimal(1.20),
            'qty': 1,
        }, {
            'product_name': 'Apple pie',
            'product_uom': 'ud',
            'product_uom_factor': 1,
            'product_type': Product.DESSERT,
            'product_offer_3x2': False,
            'product_price': Decimal(2.50),
            'qty': 1,
        }]
        discounts = Order.discountsCalculate(lines)
        self.assertTrue(discounts)
        self.assertEqual(1, len(discounts))
        self.assertEqual('percent', discounts[0]['discount_type'])
        self.assertEqual(Decimal(11.0), Decimal(discounts[0]['base']))

    def testDiscountsGetOffer(self):
        # Offer discount
        lines = [{
            'product_name': 'Water',
            'product_uom': 'ud',
            'product_uom_factor': 1,
            'product_type': Product.DRINK,
            'product_offer_3x2': True,
            'product_price': Decimal(1.50),
            'qty': 3,
        }, {
            'product_name': 'Soda',
            'product_uom': 'ud',
            'product_uom_factor': 1,
            'product_type': Product.DRINK,
            'product_offer_3x2': True,
            'product_price': Decimal(1.20),
            'qty': 1,
        }, {
            'product_name': 'Apple pie',
            'product_uom': 'ud',
            'product_uom_factor': 1,
            'product_type': Product.DESSERT,
            'product_offer_3x2': False,
            'product_price': Decimal(2.50),
            'qty': 1,
        }]
        discounts = Order.discountsCalculate(lines)
        self.assertTrue(discounts)
        self.assertEqual(1, len(discounts))
        self.assertEqual('qty', discounts[0]['discount_type'])
        self.assertEqual(Decimal(1.50), Decimal(discounts[0]['base']))
        self.assertEqual(1, discounts[0]['qty'])

    def testDiscountsGetMix(self):
        # Menu and offer discount
        lines = [{
            'product_name': 'Risotto',
            'product_uom': 'gr',
            'product_uom_factor': 100,
            'product_type': Product.MAIN,
            'product_offer_3x2': False,
            'product_price': Decimal(3.50),
            'qty': 200,
        }, {
            'product_name': 'Water',
            'product_uom': 'ud',
            'product_uom_factor': 1,
            'product_type': Product.DRINK,
            'product_offer_3x2': True,
            'product_price': Decimal(1.50),
            'qty': 6,
        }, {
            'product_name': 'Soda',
            'product_uom': 'ud',
            'product_uom_factor': 1,
            'product_type': Product.DRINK,
            'product_offer_3x2': True,
            'product_price': Decimal(1.20),
            'qty': 1,
        }, {
            'product_name': 'Apple pie',
            'product_uom': 'ud',
            'product_uom_factor': 1,
            'product_type': Product.DESSERT,
            'product_offer_3x2': False,
            'product_price': Decimal(2.50),
            'qty': 1,
        }]
        discounts = Order.discountsCalculate(lines)
        self.assertTrue(discounts)
        self.assertEqual(2, len(discounts))
        self.assertEqual('percent', discounts[0]['discount_type'])
        self.assertEqual(Decimal(11.0), Decimal(discounts[0]['base']))
        self.assertEqual('qty', discounts[1]['discount_type'])
        self.assertEqual(Decimal(1.50), Decimal(discounts[1]['base']))
        self.assertEqual(1, discounts[1]['qty'])
