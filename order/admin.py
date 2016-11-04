# -*- coding: utf-8 -*-
from django.contrib import admin
from order.models import OrderListTask

class OrderListTaskAdmin(admin.ModelAdmin):
    list_display = ('shop_name', 'last_request_datetime', 'sellerid')
    fields = ('shop_name', 'start_work_datetime', 'sellerid')
    readonly_fields = ('shop_name', 'start_work_datetime', 'sellerid')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(OrderListTask, OrderListTaskAdmin)
