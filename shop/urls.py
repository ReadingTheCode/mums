from django.conf.urls import url

from . import views

app_name = 'shop'
urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^details/(?P<order_id>[0-9]+)', views.details, name='details'),
    url(r'^order/', views.order, name='order'),
    url(r'^discounts/', views.discounts, name='discounts'),
]
