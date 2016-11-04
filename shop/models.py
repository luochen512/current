# -*- coding: utf-8 -*-
from django.db import models


class Marketplace(models.Model):
    """
    Amazon 账号的销售站点
    """
    ZONE_CHOICES = (
        ('US/Pacific', u'Pacific'),
        ('UTC', u'Europe'),
        ('Asia/Tokyo', u'Tokyo')
    )
    marketplace = models.CharField(u'站点名字', max_length=50)
    marketplaceid = models.CharField(u'站点Amazon ID', max_length=50, unique=True)
    zone = models.CharField(u'时区', max_length=50, choices=ZONE_CHOICES, default='US/Pacific')
    create_time = models.DateTimeField(u'创建时间', auto_now_add=True)

    def __unicode__(self):
        return u'%s(%s)' % (self.marketplace, self.marketplaceid)

    class Meta:
        verbose_name = u'Amazon 销售站点'
        verbose_name_plural = u'Amazon 销售站点'


class Shop(models.Model):
    """
    Amazon 店铺数据库
    """
    MWS_URL_CHOICES = (
        ('https://mws.amazonservices.com', u'USA'),
        ('https://mws-eu.amazonservices.com', u'Europe'),
        ('https://mws.amazonservices.jp', u'Japan')
    )

    name = models.CharField(u'店铺名', max_length=50)
    brand_name = models.CharField(u'品牌名', max_length=50)
    email = models.EmailField(u'店铺注册Email')
    begin_sale_date = models.DateField(u'开始销售日期')
    sellerid = models.CharField(u'SellerID', max_length=50, unique=True)
    dev_account_number = models.CharField(u'开发者ID', max_length=50)
    access_key = models.CharField(u'Access Key', max_length=100)
    secret_key = models.CharField(u'Secret Key', max_length=100)
    mws_url = models.CharField(u'MWS接口地址', max_length=100, choices=MWS_URL_CHOICES, default='https://mws.amazonservices.com')
    vps_ip = models.GenericIPAddressField(u'MWS节点服务IP', unique=True, protocol="IPv4")
    marketplaces = models.ManyToManyField(Marketplace, verbose_name=u'站点')
    enable = models.BooleanField(u'有效', default=True)
    update_time = models.DateTimeField(u'更新时间', auto_now=True)
    create_time = models.DateTimeField(u'创建时间', auto_now_add=True)

    def app_name(self):
        self.name.strip()
        return self.name.strip()

    def app_version(self):
        return self.create_time.strftime("%Y-%m-%d")

    def request_url(self):
        return u'http://%s:8080/mws_node/mwsNode.html' % self.vps_ip

    def marketplaceIds(self):
        marketplaceids = self.marketplaces.all()
        params = {}
        for index, marketplace in enumerate(marketplaceids):
            key = 'MarketplaceId.Id.%ld' % (index + 1)
            params[key] = marketplace.marketplaceid
        return params

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = u'Amazon 店铺'
        verbose_name_plural = u'Amazon 店铺'
