# -*- coding: utf-8 -*-
from django.conf.urls import url
from finance import views
from finance.business import listfinancialeventsview

urlpatterns = [
    url(r'^mws/ListFinancialEvents/(?P<sellerid>\w+)/$', listfinancialeventsview.listfinancialevents)
]