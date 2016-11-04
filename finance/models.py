# -*- coding: utf-8 -*-
from django.db import models
from datetime import datetime, timedelta
from utils import mwsdatetime


class ListFinanceEventTask(models.Model):
    """
    ListFinanceEvent任务管理
    """
    STATUS_CHOICES = (
        ('idle', u'idle'),
        ('working', u'working')
    )
    shop_name = models.CharField(u'ShopName', max_length=100, blank=True, null=True)
    sellerid = models.CharField(u'SellerID', max_length=50, unique=True)
    before_datetime = models.DateTimeField(u'BeforeDateTime', blank=True, null=True)
    after_datetime = models.DateTimeField(u'AfterDateTime', blank=True, null=True)
    last_before_datetime = models.DateTimeField(u'BeforeDateTime', blank=True, null=True)
    last_after_datetime = models.DateTimeField(u'AfterDateTime', blank=True, null=True)
    status = models.CharField(u'Status', max_length=15, choices=STATUS_CHOICES, default='idle')
    start_work_datetime = models.DateTimeField(u'StartWorkDateTime', blank=True, null=True)
    has_next = models.BooleanField(u'HasNextToken', default=False)
    next_token = models.CharField(u'NextToken', max_length=1024, blank=True, null=True)

    def is_timeout(self):
        now = datetime.utcnow() - timedelta(minutes=5)
        working_date = mwsdatetime.to_naive(self.start_work_datetime)
        if now > working_date:
            return True
        return False

    def is_throttling(self):
        now = datetime.utcnow() - timedelta(seconds=3)
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
        if mwsdatetime.dbdatetime_timedelta(self.last_after_datetime, self.after_datetime).total_seconds() < 0:
            self.after_datetime = self.last_after_datetime
        if mwsdatetime.dbdatetime_timedelta(self.last_before_datetime, self.before_datetime).total_seconds() > 0:
            self.before_datetime = self.last_before_datetime
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
        verbose_name = u'ListFinanceEventTask'
        verbose_name_plural = u'ListFinanceEventTask'


class AdjustmentEvent(models.Model):
    """
    An adjustment to your account.
    """
    sellerid = models.CharField(u'SellerId', max_length=50)
    adjustmenttype = models.CharField(u'AdjustmentType', max_length=50)
    adjustmentamount = models.DecimalField(u'AdjustmentAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'CurrencyCode', max_length=5, blank=True, null=True)
    # post date=ListFinancialEventsTask.postedafter
    post_date = models.DateTimeField(u'PostDate')

    def __unicode__(self):
        return self.adjustmenttype

    class Meta:
        verbose_name = u'AdjustmentEvent'
        verbose_name_plural = u'AdjustmentEvent'


class AdjustmentItem(models.Model):
    """
    An item of an adjustment to your account.
    """
    adjustmentevnet = models.ForeignKey(AdjustmentEvent, verbose_name=u'AdjustmentEvent')
    quantity = models.IntegerField(u'Qantity', default=0)
    perunitamount = models.DecimalField(u'PerUnitAmount', max_digits=10, decimal_places=2, default=0)
    totalamount = models.DecimalField(u'TotalAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)
    seller_sku = models.CharField(u'SellerSKU', max_length=50, blank=True, null=True)
    fnsku = models.CharField(u'FnSKU', max_length=50, blank=True, null=True)
    productdescription = models.TextField(u'ProductDescription', blank=True, null=True)
    asin = models.CharField(u'ASIN', max_length=50, blank=True, null=True)

    def __unicode__(self):
        return self.asin

    class Meta:
        verbose_name = u'AdjustmentItem'
        verbose_name_plural = u'AdjustmentItem'


class DebtRecoveryEvent(models.Model):
    """
    A debt payment or debt adjustment.
    """
    sellerid = models.CharField(u'SellerId', max_length=50)
    debtrecoverytype = models.CharField(u'DebtRecoveryType', max_length=50, blank=True, null=True)
    recoveryamount = models.DecimalField(u'RecoveryAmount', max_digits=10, decimal_places=2, default=0)
    overpaymentcredit = models.DecimalField(u'OverPaymentCredit', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.debtrecoverytype

    class Meta:
        verbose_name = u'DebtRecoveryEvent'
        verbose_name_plural = u'DebtRecoveryEvent'


class DebtRecoveryItem(models.Model):
    """
    An item of a debt payment or debt adjustment.
    """
    debtrecoveryevent = models.ForeignKey(DebtRecoveryEvent,  verbose_name=u'DebtRecoveryEvent')
    recoveryamount = models.DecimalField(u'RecoveryAmount', max_digits=10, decimal_places=2, default=0)
    originalamount = models.DecimalField(u'OriginalAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)
    groupbegindate = models.DateTimeField(u'GroupBeginDate', blank=True, null=True)
    groupenddate = models.DateTimeField(u'GroupBeginDate', blank=True, null=True)

    def __unicode__(self):
        return self.currency

    class Meta:
        verbose_name = u"DebtRecoveryItem"
        verbose_name_plural = u'DebtRecoveryItem'


class DebtRecoveryChargeInstrumentItem(models.Model):
    """
    charge instruments used for DebtPayment or DebtPaymentFailure recovery types.
    """
    debtrecoveryevent = models.ForeignKey(DebtRecoveryEvent,  verbose_name=u'DebtRecoveryEvent')
    description = models.CharField(u'Description', max_length=1024, blank=True, null=True)
    tail = models.CharField(u'Tail', max_length=512, blank=True, null=True)
    amount = models.DecimalField(u'Amount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.description

    class Meta:
        verbose_name = u'DebtRecoveryChargeInstrumentItem'
        verbose_name_plural = u'DebtRecoveryChargeInstrumentItem'


class LoanServicingEvent(models.Model):
    """
    A loan advance, loan payment, or loan refund.
    """
    sellerid = models.CharField(u'SellerId', max_length=50)
    sourcebusinesseventtype = models.CharField(u'SourceBusinessEventType', max_length=50, blank=True, null=True)
    loanamount = models.DecimalField(u'LoanAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.sourcebusinesseventtype

    class Meta:
        verbose_name = u'LoanServicingEvent'
        verbose_name_plural = u'LoanServicingEvent'


class PayWithAmazonEvent(models.Model):
    """
    An event related to your Pay with Amazon account.
    """
    sellerid = models.CharField(u'SellerId', max_length=50)
    sellerorderid = models.CharField(u'SellerOrderId', max_length=512, blank=True, null=True)
    transactionposteddate = models.DateTimeField(u'TransactionPostedDate', blank=True, null=True)
    businessobjecttype = models.CharField(u'BusinessObjectType', max_length=50, blank=True, null=True)
    saleschannel = models.CharField(u'SalesChannel', max_length=255, blank=True, null=True)
    charge_type = models.CharField(u'ChargeType', max_length=50, blank=True, null=True)
    charge_amount = models.DecimalField(u'ChargeAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)
    paymentamounttype = models.CharField(u'PaymentAmountType', max_length=50, blank=True, null=True)
    amountdescription = models.CharField(u'AmountDescription', max_length=512, blank=True, null=True)
    fulfillmentchannel = models.CharField(u'FulfillmentChannel', max_length=10, blank=True, null=True)
    storename = models.CharField(u'StoreName', max_length=255, blank=True ,null=True)

    def __unicode__(self):
        return self.businessobjecttype

    class Meta:
        verbose_name = u'PayWithAmazonEvent'
        verbose_name_plural = u'PayWithAmazonEvent'


class PayWithAmazonFeeItem(models.Model):
    """
    fees associated with PayWithAmazonEvent.
    """
    paywithamazonevent = models.ForeignKey(PayWithAmazonEvent, verbose_name=u'PayWithAmazonEvent')
    feetype = models.CharField(u'FeeType', max_length=50, blank=True, null=True)
    feeamount = models.DecimalField(u'FeeAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.feetype

    class Meta:
        verbose_name = u'PayWithAmazonFeeItem'
        verbose_name_plural = u'PayWithAmazonFeeItem'


class PerformanceBondRefundEvent(models.Model):
    """
    A refund of a seller performance bond that is issued when a seller in China stops selling in certain categories.
    """
    sellerid = models.CharField(u'SellerId', max_length=50)
    marketplacecountrycode = models.CharField(u'MarketplaceCountryCode', max_length=5, blank=True, null=True)
    amount = models.DecimalField(u'Amount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)
    productgrouplist = models.TextField(u'ProductGroupList', blank=True, null=True)

    def __unicode__(self):
        return self.marketplacecountrycode

    class Meta:
        verbose_name = u'PerformanceBondRefundEvent'
        verbose_name_plural = u'PerformanceBondRefundEvent'


class RentalTransactionEvent(models.Model):
    """
    An event related to a rental transaction.
    """
    sellerid = models.CharField(u'SellerId', max_length=50)
    amazonorderid = models.CharField(u'AmazonOrderId', max_length=20, blank=True, null=True)
    rentaleventtype = models.CharField(u'RentalEventType', max_length=50, blank=True, null=True)
    extensionlength = models.IntegerField(u'ExtensionLength', default=0)
    posteddate = models.DateTimeField(u'PostedDate', blank=True, null=True)
    marketplacename = models.CharField(u'MarketplaceName', max_length=50, blank=True, null=True)
    rentalinitialvalue = models.DecimalField(u'RentalInitialValue',  max_digits=10, decimal_places=2, default=0)
    rentalreimbursement = models.DecimalField(u'RentalReimbursement', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.amazonorderid

    class Meta:
        verbose_name = u'RentalTransactionEvent'
        verbose_name_plural = u'RentalTransactionEvent'


class RentalTransactionChargeItem(models.Model):
    """
     charges accociated with the rental event.
    """
    rentaltransactionevent = models.ForeignKey(RentalTransactionEvent, verbose_name=u'RentalTransactionEvent')
    charegetype = models.CharField(u'ChargeType', max_length=50, blank=True, null=True)
    charegeamount = models.DecimalField(u'ChargeAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.charegetype

    class Meta:
        verbose_name = u'RentalTransactionChargeItem'
        verbose_name_plural = u'RentalTransactionChargeItem'


class RentalTransactionFeeItem(models.Model):
    """
     fees associated with the rental event.
    """
    rentaltransactionevent = models.ForeignKey(RentalTransactionEvent, verbose_name=u'RentalTransactionEvent')
    feetype = models.CharField(u'FeeType', max_length=50, blank=True, null=True)
    feeamount = models.DecimalField(u'FeeAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.feetype

    class Meta:
        verbose_name = u'RentalTransactionFeeItem'
        verbose_name_plural = u'RentalTransactionFeeItem'


class RetrochargeEvent(models.Model):
    """
    A retrocharge or retrocharge reversal.
    """
    sellerid = models.CharField(u'SellerId', max_length=50)
    retrochargeeventtype = models.CharField(u'RetrochargeEventType', max_length=50, blank=True, null=True)
    amazonorderid = models.CharField(u'AmazonOrderId', max_length=20, blank=True, null=True)
    posteddate = models.DateTimeField(u'PostedDate', blank=True, null=True)
    basetax = models.DecimalField(u'BaseTax', max_digits=10, decimal_places=2, default=0)
    shippingtax = models.DecimalField(u'ShippingTax', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)
    marketplacename = models.CharField(u'MarketplaceName', max_length=50, blank=True, null=True)

    def __unicode__(self):
        return self.retrochargeeventtype

    class Meta:
        verbose_name = u'RetrochargeEvent'
        verbose_name_plural = u'RetrochargeEvent'


class ServiceFeeEvent(models.Model):
    """
    A service fee on your account.
    """
    sellerid = models.CharField(u'SellerId', max_length=50)
    amazonorderid = models.CharField(u'AmazonOrderId', max_length=20, blank=True, null=True)
    feereason = models.CharField(u'FeeReason', max_length=512, blank=True, null=True)
    sellersku = models.CharField(u'SellerSKU', max_length=50, blank=True, null=True)
    fnsku = models.CharField(u'FnSKU', max_length=50, blank=True, null=True)
    feedescription = models.CharField(u'FeeDescription', max_length=512, blank=True, null=True)
    asin = models.CharField(u'ASIN', max_length=50, blank=True, null=True)
    postdate = models.DateTimeField(u'PostDate')

    def __unicode__(self):
        return self.feereason

    class Meta:
        verbose_name = u'ServiceFeeEvent'
        verbose_name_plural = u'ServiceFeeEvent'


class ServiceFeeEventFeeItem(models.Model):
    """
    fee components associated with the service fee.
    """
    servicefeeevent = models.ForeignKey(ServiceFeeEvent, verbose_name=u'ServiceFeeEventFeeItem')
    feetype = models.CharField(u'FeeType', max_length=50, blank=True, null=True)
    feeamount = models.DecimalField(u'FeeAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.feetype

    class Meta:
        verbose_name = u'ServiceFeeEventFeeItem'
        verbose_name_plural = u'ServiceFeeEventFeeItem'


class ShipmentEvent(models.Model):
    """
    A shipment, refund, guarantee claim, or chargeback.
    """
    CATEGORY = (
        ('normal', 'Normal'),
        ('refund', 'Refund'),
        ('guarantee_claim', 'GuaranteeClaim'),
        ('chargeback', 'ChargeBack')
    )
    sellerid = models.CharField(u'SellerId', max_length=50)
    category = models.CharField(u'Category', max_length=20, choices=CATEGORY, default='normal')
    amazonorderid = models.CharField(u'AmazonOrderId', max_length=20, blank=True, null=True)
    sellerorderid = models.CharField(u'SellerOrderId', max_length=50, blank=True, null=True)
    marketplacename = models.CharField(u'MarketplaceName', max_length=50, blank=True, null=True)
    posteddate = models.DateTimeField(u'PostedDate', blank=True, null=True)


class ShipmentChargeItem(models.Model):
    """
     order-level charges. These charges are applicable to Multi-Channel Fulfillment (MCF) COD orders.
    """
    CATEGORY = (
        ('order', 'Order'),
        ('orderadjustment', 'OrderAdjustment')
    )
    shipmentevent = models.ForeignKey(ShipmentEvent, verbose_name=u'ShipmentEvent')
    category = models.CharField(u'Category', max_length=20, choices=CATEGORY, default='order')
    charegetype = models.CharField(u'ChargeType', max_length=50, blank=True, null=True)
    charegeamount = models.DecimalField(u'ChargeAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.charegetype

    class Meta:
        verbose_name = u'ShipmentChargeItem'
        verbose_name_plural = u'ShipmentChargeItem'


class ShipmentFeeItem(models.Model):
    """
     shipment-level fee adjustments.
    """
    CATEGORY = (
        ('shipment', 'Shipment'),
        ('shipmentadjustment', 'ShipmentAdjustment'),
        ('order', 'Order'),
        ('orderadjustment', 'OrderAdjustment')
    )
    shipmentevent = models.ForeignKey(ShipmentEvent, verbose_name=u'ShipmentEvent')
    category = models.CharField(u'Category', max_length=20, choices=CATEGORY, default='shipment')
    feetype = models.CharField(u'FeeType', max_length=50, blank=True, null=True)
    feeamount = models.DecimalField(u'FeeAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.feetype

    class Meta:
        verbose_name = u'ShipmentFeeItem'
        verbose_name_plural = u'ShipmentFeeItem'


class ShipmentDirectPaymentItem(models.Model):
    """
    order-level fee adjustments. These adjustments are applicable to Multi-Channel Fulfillment (MCF) orders.
    """
    shipmentevent = models.ForeignKey(ShipmentEvent, verbose_name=u'ShipmentEvent')
    directpaymentpype = models.CharField(u'DirectPaymentType', max_length=50, blank=True, null=True)
    directpaymentamount = models.DecimalField(u'DirectPaymentAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.directpaymentpype

    class Meta:
        verbose_name = u'ShipmentDirectPaymentItem'
        verbose_name_plural = u'ShipmentDirectPaymentItem'


class ShipmentItem(models.Model):
    """
    An item of a shipment, refund, guarantee claim, or chargeback.
    """
    CATEGORY = (
        ('normal', 'Normal'),
        ('adjustment', 'Adjustment')
    )
    shipmentevent = models.ForeignKey(ShipmentEvent, verbose_name=u'ShipmentEvent')
    category = models.CharField(u'Category', max_length=20, choices=CATEGORY, default='normal')
    sellersku = models.CharField(u'SellerSKU', max_length=50, blank=True, null=True)
    orderitemid = models.CharField(u'OrderItemId', max_length=50, blank=True, null=True)
    orderadjustmentitemid = models.CharField(u'OrderAdjustmentItemId', max_length=50, blank=True, null=True)
    quantityshipped = models.IntegerField(u'QuantityShipped', default=0)
    costofpointsgranted = models.DecimalField(u'CostOfPointsGranted', max_digits=10, decimal_places=2, default=0)
    cotofpointsreturned = models.DecimalField(u'CostOfPointsReturned', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)
    charger = models.DecimalField(u'Charger', max_digits=10, decimal_places=2, default=0)
    fee = models.DecimalField(u'Fee', max_digits=10, decimal_places=2, default=0)
    promotion = models.DecimalField(u'Promotion', max_digits=10, decimal_places=2, default=0)

    def __unicode__(self):
        return self.sellersku

    class Meta:
        verbose_name = u'ShipmentItem'
        verbose_name_plural = u'ShipmentItem'


class ShipmentItemChargeItem(models.Model):
    """

    """
    CATEGORY = (
        ('normal', 'Normal'),
        ('adjustment', 'Adjustment')
    )
    shipmentitem = models.ForeignKey(ShipmentItem, verbose_name=u'ShipmentEvent')
    category = models.CharField(u'Category', max_length=20, choices=CATEGORY, default='normal')
    charegetype = models.CharField(u'ChargeType', max_length=50, blank=True, null=True)
    charegeamount = models.DecimalField(u'ChargeAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.charegetype

    class Meta:
        verbose_name = u'ShipmentItemChargeItem'
        verbose_name_plural = u'ShipmentItemChargeItem'


class ShipmentItemFeeItem(models.Model):
    """
     fees associated with the shipment item.
    """
    CATEGORY = (
        ('normal', 'Normal'),
        ('adjustment', 'Adjustment')
    )
    shipmentitem = models.ForeignKey(ShipmentItem, verbose_name=u'ShipmentEvent')
    category = models.CharField(u'Category', max_length=20, choices=CATEGORY, default='normal')
    feetype = models.CharField(u'FeeType', max_length=50, blank=True, null=True)
    feeamount = models.DecimalField(u'FeeAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.feetype

    class Meta:
        verbose_name = u'ShipmentItemFeeItem'
        verbose_name_plural = u'ShipmentItemFeeItem'


class ShipmentItemPromotionItem(models.Model):
    """
    promotions associated with the shipment item.
    """
    CATEGORY = (
        ('normal', 'Normal'),
        ('adjustment', 'Adjustment')
    )
    shipmentitem = models.ForeignKey(ShipmentItem, verbose_name=u'ShipmentEvent')
    category = models.CharField(u'Category', max_length=20, choices=CATEGORY, default='normal')
    promotiontype = models.CharField(u'PromotionType', max_length=50, blank=True, null=True)
    promotionid = models.CharField(u'PromotionId', max_length=50, blank=True, null=True)
    promotionamount = models.DecimalField(u'PromotionAmount', max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(u'Currency', max_length=5, blank=True, null=True)

    def __unicode__(self):
        return self.promotiontype

    class Meta:
        verbose_name = u'ShipmentItemPromotionItem'
        verbose_name_plural = u'ShipmentItemPromotionItem'


class SolutionProviderCreditEvent(models.Model):
    """
    credit given to a solution provider.
    """
    sellerid = models.CharField(u'SellerId', max_length=50)
    providertransactiontype = models.CharField(u'ProviderTransactionType', max_length=50, blank=True, null=True)
    sellerorderid = models.CharField(u'SellerOrderId', max_length=50, blank=True, null=True)
    marketplaceid = models.CharField(u'MarketplaceId', max_length=50, blank=True, null=True)
    marketplacecountrycode = models.CharField(u'MarketplaceCountryCode', max_length=5, blank=True, null=True)
    sellerstorename = models.CharField(u'SellerStoreName', max_length=255, blank=True, null=True)
    providerid = models.CharField(u'ProviderId', max_length=50, blank=True, null=True)
    providerstorename = models.CharField(u'ProviderStoreName', max_length=100, blank=True, null=True)

    def __unicode__(self):
        return self.providerid

    class Meta:
        verbose_name = u'SolutionProviderCreditEvent'
        verbose_name_plural = u'SolutionProviderCreditEvent'

