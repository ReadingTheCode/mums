import json
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.urls import reverse
from django.template.defaulttags import register
from django.template.defaultfilters import stringfilter
from django.core.exceptions import ValidationError
from .models import Product, Order


def index(request, error='', error_fields={}, values={}):
    types = (Product.MAIN, Product.DRINK, Product.DESSERT, Product.OTHER)
    return render(request, 'shop/index.html', {
        'groups': [(t, Product.objects.filter(product_type=t)) for t in types],
        'error_message': error,
        'error_fields': error_fields,
        'values': values,
    })


def details(request, order_id):
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        raise Http404("Order does not exist")
    return render(request, 'shop/details.html', {
        'order': order,
        'lines': order.orderline_set.all(),
        'discount': order.discount_set.all(),
    })


def discounts(request):
    lines = request.POST['lines']
    try:
        discounts = Order.discountsCalculate(json.loads(lines))
    except Exception as e:
        raise
        discounts = unicode(e)
    return HttpResponse(json.dumps(discounts), content_type='application/json')


def order(request):
    try:
        order = Order.fromPOST(request.POST)
    except ValidationError as e:
        values = {
            k: request.POST[k] for k in Order.persistent_fields}
        return index(request, error_fields=e.message_dict, values=values)
    except Exception as e:
        return index(request, error=unicode(e))
    return HttpResponseRedirect(reverse('shop:details', args=(order.id,)))
