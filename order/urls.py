# -*- coding: utf-8 -*-
from django.conf.urls import url
from order.business import ListOrdersView, listorderitemsview, syncorderview

urlpatterns = [
    url(r'^mws/ListOrders/(?P<sellerid>\w+)/$', ListOrdersView.ListOrder),
    url(r'^mws/ListOrderItems/(?P<sellerid>\w+)/$', listorderitemsview.listorderitems),
    url(r'^unshipped/sync/$', syncorderview.unshipped_sync)
]