from django.contrib import admin
from .models import Product, Order, OrderLine, Discount


class OrderLineInline(admin.StackedInline):
    model = OrderLine


class DiscountInline(admin.StackedInline):
    model = Discount


class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderLineInline, DiscountInline]

admin.site.register(Product)
admin.site.register(Order, OrderAdmin)
