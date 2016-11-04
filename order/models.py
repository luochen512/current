# -*- coding: utf-8 -*-
from django.db import models
from datetime import datetime, timedelta
from utils import mwsdatetime


class OrderListTask(models.Model):
    """
    OrderList任务管理
    """
    STATUS_CHOICES = (
        ('idle', u'idle'),
        ('working', u'working')
    )
    shop_name = models.CharField(u'ShopName', max_length=100, blank=True, null=True)
    sellerid = models.CharField(u'SellerID', max_length=50, unique=True, null=True)
    before_datetime = models.DateTimeField(u'BeforeDateTime', blank=True, null=True)
    after_datetime = models.DateTimeField(u'AfterDateTime', blank=True, null=True)
    last_before_datetime = models.DateTimeField(u'BeforeDateTime', blank=True, null=True)
    last_after_datetime = models.DateTimeField(u'AfterDateTime', blank=True, null=True)
    status = models.CharField(u'Status', max_length=15, choices=STATUS_CHOICES, default='idle')
    start_work_datetime = models.DateTimeField(u'StartWorkDateTime', blank=True, null=True)
    has_next = models.BooleanField(u'HasNextToken', default=False)
    next_token = models.CharField(u'NextToken', max_length=1024, blank=True, null=True)
    last_request_datetime = models.DateTimeField(u'LastRequestTime', blank=True, null=True)

    def is_timeout(self):
        now = datetime.utcnow() - timedelta(minutes=5)
        working_date = mwsdatetime.to_naive(self.start_work_datetime)
        if now > working_date:
            return True
        return False

    def is_throttling(self):
        now = datetime.utcnow() - timedelta(minutes=1)
        working_date = mwsdatetime.to_naive(self.start_work_datetime)
        if now < working_date:
            return True
        return False

    def is_working(self):
        if self.status == 'working':
            return True
        return False

    def reset_init(self):
        self.status = 'idle'
        self.hasNext = False
        self.nextToken = ''
        self.save()

    def start_working(self):
        self.start_work_datetime = datetime.utcnow()
        self.status = 'working'
        self.save()

    def task_finished(self):
        self.has_next = False
        self.next_token = ""
        if mwsdatetime.dbdatetime_timedelta(self.last_after_datetime , self.after_datetime).total_seconds() < 0:
            self.after_datetime = self.last_after_datetime
        if mwsdatetime.dbdatetime_timedelta(self.last_before_datetime, self.before_datetime).total_seconds()>0:
            self.before_datetime = self.last_before_datetime
        self.status = 'idle'
        self.save()

    def need_nexttoken(self, nexttoken):
        self.has_next = True
        self.next_token = nexttoken
        self.status = 'idle'
        self.save()

    def update_last_request_time(self):
        self.last_request_datetime = datetime.utcnow()
        self.save()

    def __unicode__(self):
        return self.shop_name

    class Meta:
        verbose_name = u'OrderListTask'
        verbose_name_plural = u'OrderListTask'


class OrderListItemTask(models.Model):
    """
    OrderList任务管理
    """
    STATUS_CHOICES = (
        ('idle', u'idle'),
        ('working', u'working')
    )
    shop_name = models.CharField(u'ShopName', max_length=100, blank=True, null=True)
    sellerid = models.CharField(u'SellerID', max_length=50, unique=True, null=True)
    status = models.CharField(u'Status', max_length=15, choices=STATUS_CHOICES, default='idle')
    start_work_datetime = models.DateTimeField(u'StartWorkDateTime', blank=True, null=True)
    has_next = models.BooleanField(u'HasNextToken', default=False)
    next_token = models.CharField(u'NextToken', max_length=1024, blank=True, null=True)

    def is_throttling(self):
        now = datetime.utcnow() - timedelta(seconds=3)
        working_date = mwsdatetime.to_naive(self.start_work_datetime)
        if now < working_date:
            return True
        return False

    def is_timeout(self):
        now = datetime.utcnow() - timedelta(minutes=5)
        working_date = mwsdatetime.to_naive(self.start_work_datetime)
        if now > working_date:
            return True
        return False

    def is_working(self):
        if self.status == 'working':
            return True
        return False

    def reset_init(self):
        self.status = 'idle'
        self.hasNext = False
        self.nextToken = ''
        self.save()

    def start_working(self):
        self.start_work_datetime = datetime.utcnow()
        self.status = 'working'
        self.save()

    def task_finished(self):
        self.has_next = False
        self.next_token = ""
        self.status = 'idle'
        self.save()

    def need_nexttoken(self, nexttoken):
        self.has_next = True
        self.next_token = nexttoken
        self.status = 'idle'
        self.save()

    def __unicode__(self):
        return self.shop_name

    class Meta:
        verbose_name = u'OrderListItemTask'
        verbose_name_plural = u'OrderListItemTask'


class Order(models.Model):
    """
    Order information
    """
    sellerid = models.CharField(u'SellerID', max_length=50)
    amazon_order_id = models.CharField(u'AmazonOrderId', max_length=20)
    purchase_date = models.DateTimeField(u'PurchaseDate', blank=True, null=True)
    last_update_date = models.DateTimeField(u'LastUpdateDate', blank=True, null=True)
    order_status = models.CharField(u'OrderStatus', max_length=50, blank=True, null=True)
    fulfillment_channel = models.CharField(u'FulfillmentChannel', max_length=20, blank=True, null=True)
    sales_channel = models.CharField(u'SalesChannel', max_length=100, blank=True, null=True)
    order_channel = models.CharField(u'OrderChannel', max_length=100, blank=True, null=True)
    ship_service_level = models.CharField(u'ShipServiceLevel', max_length=100, blank=True, null=True)
    recipient_name = models.CharField(u'Recipient Name', max_length=100, blank=True, null=True)
    address_line1 = models.CharField(u'AddressLine1', max_length=512, blank=True, null=True)
    address_line2 = models.CharField(u'AddressLine2', max_length=255, blank=True, null=True)
    address_line3 = models.CharField(u'AddressLine3', max_length=255, blank=True, null=True)
    city = models.CharField(u'City', max_length=50, blank=True, null=True)
    county = models.CharField(u'County', max_length=50, blank=True, null=True)
    district = models.CharField(u'District', max_length=50, blank=True, null=True)
    state_or_region = models.CharField(u'StateOrRegion', max_length=50, blank=True, null=True)
    postal_code = models.CharField(u'PostalCode', max_length=50, blank=True, null=True)
    country_code = models.CharField(u'CountryCode', max_length=5, blank=True, null=True)
    phone = models.CharField(u'Phone', max_length=50, blank=True, null=True)
    order_currency_code = models.CharField(u'OrderCurrencyCode', max_length=5, blank=True, null=True)
    order_total_amount = models.DecimalField(u'OrderTotalAmount', max_digits=10, decimal_places=2, default=0)
    number_items_shipped = models.PositiveIntegerField(u'NumberOfItemsShipped', default=0)
    number_items_unshipped = models.PositiveIntegerField(u'NumberOfItemsUnshipped', default=0)
    payment_method = models.CharField(u'PaymentMethod', max_length=10, blank=True, null=True)
    marketplaceid = models.CharField(u'MarketplaceId', max_length=50, blank=True, null=True)
    buyer_email = models.EmailField(u'BuyerEmail', blank=True, null=True)
    buyer_name = models.CharField(u'BuyerName', max_length=50, blank=True, null=True)
    shipment_service_level_category = models.CharField(u'ShipmentServiceLevelCategory', max_length=50, blank=True, null=True)
    shipped_by_amazon_tfm = models.BooleanField(u'ShippedByAmazonTFM', default=False)
    tfm_shipment_status = models.CharField(u'TFMShipmentStatus', max_length=50, blank=True, null=True)
    cba_displayable_shipping_label = models.CharField(u'CbaDisplayableShippingLabel', max_length=255, blank=True, null=True)
    order_type = models.CharField(u'OrderType', max_length=30, blank=True, null=True)
    earliest_ship_date = models.DateTimeField(u'EarliestShipDate', blank=True, null=True)
    latest_ship_date = models.DateTimeField(u'LatestShipDate', blank=True, null=True)
    earliest_delivery_date = models.DateTimeField(u'EarliestDeliveryDate', blank=True, null=True)
    latest_delivery_date = models.DateTimeField(u'LatestDeliveryDate', blank=True, null=True)
    is_business_order = models.BooleanField(u'IsBusinessOrder', default=False)
    purchase_order_number = models.CharField(u'PurchaseOrderNumber', max_length=100, blank=True, null=True)
    is_prime = models.BooleanField(u'IsPrime', default=False)
    is_premenum_order = models.BooleanField(u'IsPremiumOrder', default=False)
    pulled_items = models.IntegerField(u'HasPulledItems', default=0)
    is_virtual = models.BooleanField(u'IsVirtual', default=False)

    def __unicode__(self):
        return self.amazon_order_id

    class Meta:
        verbose_name = u'Order information'
        verbose_name_plural = u'Order information'


class OrderItem(models.Model):
    """
    OrderItem information.
    """
    sellerid = models.CharField(u'SellerID', max_length=50)
    amazon_order_id = models.CharField(u'AmazonOrderId', max_length=20)
    seller_order_id = models.CharField(u'SellerOrderId', max_length=100, blank=True, null=True)
    purchase_date = models.DateTimeField(u'PurchaseDate', blank=True, null=True)
    fulfillment_channel = models.CharField(u'FulfillmentChannel', max_length=20, blank=True, null=True)
    phone = models.CharField(u'Phone', max_length=50, blank=True, null=True)
    marketplaceid = models.CharField(u'MarketplaceId', max_length=50, blank=True, null=True)
    asin = models.CharField(u'ASIN', max_length=50, blank=True, null=True)
    order_item_id = models.CharField(u'OrderItemId', max_length=30)
    seller_sku = models.CharField(u'SellerSKU', max_length=100, blank=True, null=True)
    customized_url = models.CharField(u'CustomizedURL', max_length=255, blank=True, null=True)
    title = models.CharField(u'Title', max_length=512, blank=True, null=True)
    quantity_ordered = models.PositiveIntegerField(u'QuantityOrdered', default=0)
    quantity_shipped = models.PositiveIntegerField(u'QuantityShipped', default=0)
    points_number = models.IntegerField(u'PointsNumber', blank=True, null=True)
    points_monetary_value = models.DecimalField(u'PointsMonetaryValue', max_digits=10, decimal_places=2, default=0)
    item_currency = models.CharField(u'Item Currency', max_length=5, blank=True, null=True)
    item_price = models.DecimalField(u'ItemPrice', max_digits=10, decimal_places=2, default=0)
    shipping_price = models.DecimalField(u'ShippingPrice', max_digits=10, decimal_places=2, default=0)
    gift_wrap_price = models.DecimalField(u'GiftWrapPrice', max_digits=10, decimal_places=2, default=0)
    item_tax = models.DecimalField(u'ItemTax', max_digits=10, decimal_places=2, default=0)
    shipping_tax = models.DecimalField(u'ShippingTax', max_digits=10, decimal_places=2, default=0)
    gift_wrap_tax = models.DecimalField(u'GiftWrapTax', max_digits=10, decimal_places=2, default=0)
    shipping_discount = models.DecimalField(u'ShippingDiscount', max_digits=10, decimal_places=2, default=0)
    promotion_discount = models.DecimalField(u'PromotionDiscount', max_digits=10, decimal_places=2, default=0)
    promotion_ids = models.CharField(u'PromotionIds', max_length=255, blank=True, null=True)
    cod_fee = models.DecimalField(u'CODFee', max_digits=10, decimal_places=2, default=0)
    cod_fee_discount = models.DecimalField(u'CODFeeDiscount', max_digits=10, decimal_places=2, default=0)
    gift_message_text = models.CharField(u'GiftMessageText', max_length=255, blank=True, null=True)
    gift_wrap_level = models.CharField(u'GiftWrapLevel', max_length=255, blank=True, null=True)
    invoice_requirement = models.CharField(u'InvoiceRequirement', max_length=30, blank=True, null=True)
    buyer_selected_invoice_category = models.CharField(u'BuyerSelectedInvoiceCategory', max_length=255, blank=True, null=True)
    invoice_title = models.CharField(u'InvoiceTitle', max_length=255, blank=True, null=True)
    invoice_information = models.CharField(u'InvoiceInformation', max_length=255, blank=True, null=True)
    condition_note = models.CharField(u'ConditionNote', max_length=255, blank=True, null=True)
    conditionid = models.CharField(u'ConditionId', max_length=30, blank=True, null=True)
    condition_subtype_id = models.CharField(u'ConditionSubtypeId', max_length=30, blank=True, null=True)
    scheduled_delivery_start_date = models.CharField(u'ScheduledDeliveryStartDate', max_length=50, blank=True, null=True)
    scheduled_delivery_end_date = models.CharField(u'ScheduledDeliveryEndDate', max_length=50, blank=True, null=True)
    price_designation = models.CharField(u'PriceDesignation', max_length=100, blank=True, null=True)
    is_virtual = models.BooleanField(u'IsVirtual', default=False)

    def __unicode__(self):
        return self.order_item_id

    class Meta:
        verbose_name = u'OrderItem information'
        verbose_name_plural = u'OrderItem information'


class PaymentExecutionDetailItem(models.Model):
    """
    Information about a sub-payment method used to pay for a COD order.
    """
    payment_method = models.CharField(u'PaymentMethod', max_length=20)
    payment_amount = models.DecimalField(u'PaymentAmount', max_digits=10, decimal_places=2)
    payment_currency = models.CharField(u'PaymentCurrency', max_length=5)
    order = models.ForeignKey(Order, verbose_name=u'Order')

    def __unicode__(self):
        return self.payment_method

    class Meta:
        verbose_name = u'PaymentExecutionDetailItem'
        verbose_name_plural = u'PaymentExecutionDetailItem'
