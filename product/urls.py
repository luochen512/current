# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from django.conf.urls import url
from product import views
urlpatterns = [
    url(r'^mws/LowestPricedSKU/(?P<sellerid>\w+)/$', views.lowest_priced_sku)
]