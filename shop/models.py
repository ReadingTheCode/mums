from __future__ import unicode_literals

import json
from decimal import Decimal
from copy import deepcopy
from datetime import datetime, time
from django.db import models

DISCOUNT_PERCENT_MENU = 20.0  # 20% discount for menus


class Product(models.Model):
    GRS = 'gr'
    UNITS = 'ud'

    OTHER = 'other'
    MAIN = 'main'
    DRINK = 'drink'
    DESSERT = 'dessert'

    name = models.CharField(max_length=200)
    uom = models.CharField(max_length=2, choices=(
        (GRS, 'grs'),
        (UNITS, 'uds'),
    ), default=UNITS)
    uom_factor = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=1.0)
    product_type = models.CharField(max_length=8, choices=(
        (OTHER, 'Other'),
        (MAIN, 'Main dish'),
        (DRINK, 'Drink'),
        (DESSERT, 'Dessert'),
    ), default=OTHER, db_index=True)
    offer_3x2 = models.BooleanField(default=False)
    image = models.ImageField()

    def __unicode__(self):
        """Product name"""
        return self.name


class Order(models.Model):
    firstname = models.CharField(max_length=200)
    lastname = models.CharField(max_length=200)
    email = models.EmailField(max_length=200)
    date = models.DateTimeField(auto_now_add=True)
    number = models.CharField(max_length=20, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    persistent_fields = {'firstname', 'lastname', 'email'}

    def __unicode__(self):
        """Order email, date and number"""
        return u"[%s/%s/%s]" % (
            self.email, self.date.strftime('%Y-%m-%d %H:%M:%S'), self.number)

    def numberSet(self):
        # Get all orders from today
        count = Order.objects.filter(
            date__range=[
                datetime.combine(self.date, time.min),
                datetime.combine(self.date, time.max)]
        ).exclude(id__exact=self.id).count()
        # Give next number
        number = count + 1
        if self.number != number:
            self.number = number
            self.save()
        return number

    def totalSet(self):
        total = Decimal(0.)
        for line in self.orderline_set.all():
            total += line.subtotalSet()
        for discount in self.discount_set.all():
            total += discount.subtotalSet()
        if self.total != total:
            self.total = total
            self.save()
        return total

    @classmethod
    def menuSearch(cls, lines):
        base = Decimal(0.)
        line_ids = []
        menu = {}
        values = deepcopy(lines)
        product_types = {Product.MAIN, Product.DRINK, Product.DESSERT}
        for product_type in product_types:
            for line in values:
                if line.get('product_type') == product_type:
                    price = Decimal(line.get('product_price', 0.))
                    uom_factor = int(line.get('product_uom_factor', 1))
                    qty = int(line.get('qty', 0))
                    line_id = line.get('id')
                    if line_id:
                        line_ids.append(line_id)
                    menu[product_type] = deepcopy(line)
                    if line.get('product_uom', False) == 'ud':
                        base += price
                        menu[product_type]['qty'] = 1
                        if qty > 1:
                            line['qty'] = qty - 1
                        else:
                            values.remove(line)
                    else:
                        base += ((price * qty) / uom_factor)
                        menu[product_type]['qty'] = qty
                        values.remove(line)
                    break
        if len(menu.keys()) == len(product_types):
            menu['base'] = base
            menu['line_ids'] = line_ids
            return menu, values
        return False, lines

    @classmethod
    def offerSearch(cls, lines):
        values = deepcopy(lines)
        offer = False
        for line in values:
            product_uom = line.get('product_uom', False)
            offer_3x2 = line.get('product_offer_3x2', False)
            qty = int(line.get('qty', 0))
            if offer_3x2 and product_uom == 'ud' and qty > 2:
                offer = deepcopy(line)
                offer['qty'] = qty / 3
                rest = qty % 3
                if rest:
                    line['qty'] = rest
                else:
                    values.remove(line)
        if offer:
            return offer, values
        return False, lines

    @classmethod
    def discountsCalculate(cls, lines):
        # Check for menu discounts first
        discounts = []
        menu, lines = cls.menuSearch(lines)
        while menu:
            discounts.append({
                'discount_type': 'percent',
                'description': 'Menu discount',
                'base': str(menu.get('base', 0.)),
                'percent': DISCOUNT_PERCENT_MENU,
                'line_ids': menu.get('line_ids', [])
            })
            menu, lines = cls.menuSearch(lines)
        # Then, look for lines with 3x2 offer products
        offer, lines = cls.offerSearch(lines)
        while offer:
            line_id = offer.get('id', False)
            discounts.append({
                'discount_type': 'qty',
                'description': 'Discount 3x2 (%s)' % offer.get('product_name'),
                'base': str(offer.get('product_price', 0.)),
                'qty': offer.get('qty', 0),
                'line_ids': [line_id] if line_id else [],
            })
            offer, lines = cls.offerSearch(lines)
        return discounts

    def discountsGet(self):
        lines = []
        for line in self.orderline_set.all():
            lines.append({
                'id': line.id,
                'product_id': line.product.id,
                'product_uom': line.product.uom,
                'product_uom_factor': line.product.uom_factor,
                'product_type': line.product.product_type,
                'product_name': line.product.name,
                'product_offer_3x2': line.product.offer_3x2,
                'product_price': line.product.price,
                'qty': line.qty,
            })
        return Order.discountsCalculate(lines)

    @classmethod
    def fromPOST(cls, data):
        lines = json.loads(data.get('lines', "[]"))
        if not lines:
            raise Exception('No lines to order')
        order = cls(
            firstname=data.get('firstname', ''),
            lastname=data.get('lastname', ''),
            email=data.get('email', ''),
            date=datetime.now(),
        )
        order.full_clean()
        order.save()
        # Process order lines
        for line in lines:
            order.orderline_set.create(
                product_id=line.get('product_id', False),
                qty=line.get('qty', False),
            )
        # Calculate discounts
        discounts = order.discountsGet()
        for discount in discounts:
            d = order.discount_set.create(
                discount_type=discount.get('discount_type'),
                description=discount.get('description', 'Discount'),
                base=Decimal(discount.get('base', 0.)),
                percent=Decimal(discount.get('percent', 0.)),
                qty=discount.get('qty', 1),
            )
            lines = [OrderLine.objects.get(id=x)
                     for x in discount.get('lines_ids', [])]
            if lines:
                d.add(*lines)
        order.numberSet()
        order.totalSet()
        order.save()
        return order


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.IntegerField(default=1)
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0)

    def __unicode__(self):
        """Order line: product name, qty"""
        return u"%s x %s" % (self.qty, self.product.name)

    def subtotalSet(self):
        subtotal = (self.product.price * self.qty) / self.product.uom_factor
        if self.subtotal != subtotal:
            self.subtotal = subtotal
            self.save()
        return subtotal


class Discount(models.Model):
    PERCENT = 'percent'
    QTY = 'qty'

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    discount_type = models.CharField(max_length=8, choices=(
        (PERCENT, 'Percentage'),
        (QTY, 'Quantity'),
    ), default=PERCENT, db_index=True)
    description = models.CharField(max_length=200, default='discount')
    base = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    percent = models.DecimalField(max_digits=5, decimal_places=2, default=20.0)
    qty = models.IntegerField(default=1)
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0)
    lines = models.ManyToManyField(OrderLine)

    def __unicode__(self):
        """Discount total"""
        return u"%s:%.02f" % (self.description, self.subtotal)

    def subtotalSet(self):
        subtotal = 0.
        if self.discount_type == self.PERCENT:
            subtotal = -(self.base * self.percent) / 100
        else:
            subtotal = -(self.base * self.qty)
        if self.subtotal != subtotal:
            self.subtotal = subtotal
            self.save()
        return subtotal
