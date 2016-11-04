# -*- coding: utf-8 -*-
from django.contrib import admin
from shop.models import Marketplace, Shop


class MarketplaceAdmin(admin.ModelAdmin):
    list_display = ("marketplace", "marketplaceid", "zone")
    fields = ("marketplace", "marketplaceid", "zone")

class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "sellerid", "begin_sale_date", "vps_ip")
    fields = ("name", "brand_name", "email", "begin_sale_date", "sellerid", "dev_account_number",
"access_key", "secret_key", "mws_url", "vps_ip", "marketplaces", "enable")
    filter_horizontal = ("marketplaces",)

admin.site.register(Marketplace, MarketplaceAdmin)
admin.site.register(Shop, ShopAdmin)

# Register your models here.
