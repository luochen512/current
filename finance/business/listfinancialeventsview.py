# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import JsonResponse
from shop.models import Shop
from finance.models import *
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from datetime import datetime, timedelta
from utils import mwssignature, mwsdatetime, mwsnode, mwsdecode
from decimal import Decimal
import logging


logger = logging.getLogger('mws_finance')
# Create your views here.
def listfinancialevents(request, sellerid):
    data = {'code': '00000', 'msg': 'Success'}
    if sellerid is None:
        data['code'] = u'00001'
        data['msg'] = u'sellerid is None!'
        return JsonResponse(data)
    try:
        shop = Shop.objects.get(sellerid=sellerid)
        task, created = ListFinanceEventTask.objects.get_or_create(sellerid=sellerid)
        if created:
            task.shop_name = shop.brand_name
            task.before_datetime = datetime.utcnow()
            task.after_datetime = datetime.utcnow()
            task.start_work_datetime = datetime.utcnow()
            task.save()
        timeout = task.is_timeout()
        working = task.is_working()
        throttling = task.is_throttling()
        if throttling:
            data['code'] = u'00004'
            data['msg'] = u'ListFinanceEvent (%s) is throttling !' % str(sellerid)
            return JsonResponse(data)
        if working and not timeout:
            data['code'] = u'00005'
            data['msg'] = u'ListFinanceEvent (%s) is Working !' % str(sellerid)
            return JsonResponse(data)
        if timeout:
            logger.info("time out, rest ListFinanceEvent task")
            task.reset_init()
        data = _dispatch_task(shop, task)
    except ObjectDoesNotExist as e:
        data['code'] = u'00002'
        data['msg'] = u'sellerid(%s) is not Exist ListFinanceEvent !' % str(sellerid)
        return JsonResponse(data)
    except MultipleObjectsReturned as e:
        data['code'] = u'00003'
        data['msg'] = u'ListFinanceEvent multiple sellerids %s' % str(sellerid)
        return JsonResponse(data)
    return JsonResponse(data)


def _dispatch_task(shop, task):
    data = {'code': '00000', 'msg': 'Success'}
    url = shop.request_url()
    params = {}
    params['Version'] = "2015-05-01"
    params['AWSAccessKeyId'] = shop.access_key
    params['SellerId'] = shop.sellerid
    params.update(mwssignature.normal_params())
    if task.has_next:
        params['Action'] = 'ListFinancialEventsByNextToken'
        params['NextToken'] = task.next_token
    else:
        params['Action'] = 'ListFinancialEvents'
        update_times = _last_update_time(shop, task)
        if update_times is None:
            data['code'] = '00009'
            data['msg'] = 'lastupdatetime error'
            return data
        params.update(update_times)
    request_params = mwssignature.dict_params_urlcode(params, True)
    params['Signature'] = mwssignature.calc_signature(shop.mws_url, '/Finances/2015-05-01', shop.secret_key,
                                                      request_params)
    mws_data = {
        "sellerid": shop.sellerid,
        "nodeIP": shop.vps_ip,
        "url": shop.mws_url,
        "action": params['Action'],
        "uri": "/Finances/2015-05-01",
        "appName": shop.app_name(),
        "appVersion": shop.app_version(),
        "params": mwssignature.dict_params_urlcode(params)
    }
    url = shop.request_url()
    task.start_working()
    response = mwsnode.request_node(url, mws_data)
    _process_response(task, response)
    return data


def _last_update_time(shop, task):
    last_before_datetime = mwsdatetime.to_naive(task.before_datetime)
    last_after_datetime = mwsdatetime.to_naive(task.after_datetime)
    params = {}
    after_date = None
    before_date = None
    utcnow = datetime.utcnow()
    if (last_before_datetime + timedelta(minutes=22)) <= utcnow:
        after_date = last_before_datetime - timedelta(seconds=1)
        before_date = after_date + timedelta(minutes=20)
    elif shop.begin_sale_date < task.after_datetime.date():
        before_date = last_after_datetime + timedelta(seconds=1)
        after_date = before_date - timedelta(minutes=20)
    else:
        return None
    params['PostedAfter'] = after_date.isoformat() + "Z"
    params['PostedBefore'] = before_date.isoformat() + "Z"
    task.last_before_datetime = before_date
    task.last_after_datetime = after_date
    task.save()
    return params


def _process_response(task, response):
    """
    处理返回结果
    :param task:
    :return:
    """
    if response is None or response['code'] != '00000':
        logger.info("response error %s " % response)
        task.reset_init()
        return
    tree = mwsdecode.tree_ignore_namepace(response['mwsResponse'])
    if tree is None:
        return
    if mwsdecode.is_error_response(tree):
        logger.info("%s reponse error: %s" % (task.sellerid, response))
        return
    result = ''
    if response['action'] == 'ListFinancialEvents':
        result = 'ListFinancialEventsResult'
    elif response['action'] == 'ListFinancialEventsByNextToken':
        result = 'ListFinancialEventsByNextTokenResult'
    financial_tree_path = result + '/FinancialEvents'
    financial_tree = tree.find(financial_tree_path)
    shipmentevents = mwsdecode.element_auto_list(financial_tree, "ShipmentEventList/ShipmentEvent")
    for item in shipmentevents:
        _process_shipmentevents(task, item, 'normal')
    refundevents = mwsdecode.element_auto_list(financial_tree, "RefundEventList/ShipmentEvent")
    for rf in refundevents:
        _process_shipmentevents(task, rf, 'refund')
    guaranteeclaimevents = mwsdecode.element_auto_list(financial_tree, "GuaranteeClaimEventList/ShipmentEvent")
    for gc in guaranteeclaimevents:
        _process_shipmentevents(task, gc, 'guarantee_claim')
    chargebackevents = mwsdecode.element_auto_list(financial_tree, "ChargebackEventList/ShipmentEvent")
    for cb in chargebackevents:
        _process_shipmentevents(task, cb, 'chargeback')

    paywithamazonevents = mwsdecode.element_auto_list(financial_tree, 'PayWithAmazonEventList/PayWithAmazonEvent')
    for pwa in paywithamazonevents:
        _process_paywithamazon_event(task, pwa)

    serviceprovidercreditevents = mwsdecode.element_auto_list(financial_tree,
                                                         'ServiceProviderCreditEventList/SolutionProviderCreditEvent')
    for spc in serviceprovidercreditevents:
        _process_serviceprovider_event(task, spc)

    retrochargeevents = mwsdecode.element_auto_list(financial_tree, 'RetrochargeEventList/RetrochargeEvent')
    for rc in retrochargeevents:
        _process_retrocharge_event(task, rc)

    rentaltransactionevents = mwsdecode.element_auto_list(financial_tree,
                                                     'RentalTransactionEventList/RentalTransactionEvent')
    for rte in rentaltransactionevents:
        _process_rental_event(task, rte)

    performancebondrefundevents = mwsdecode.element_auto_list(financial_tree,
                                                         'PerformanceBondRefundEventList/PerformanceBondRefundEvent')
    for pb in performancebondrefundevents:
        _process_performance_event(task, pb)

    servicefeeevents = mwsdecode.element_auto_list(financial_tree, 'ServiceFeeEventList/ServiceFeeEvent')
    for sf in servicefeeevents:
        _process_servicefee_event(task, sf)

    debtrecoveryevents = mwsdecode.element_auto_list(financial_tree, 'DebtRecoveryEventList/DebtRecoveryEvent')
    for dr in debtrecoveryevents:
        _process_debt_event(task, dr)

    loanservicingevents = mwsdecode.element_auto_list(financial_tree, 'LoanServicingEventList/LoanServicingEvent')
    for ls in loanservicingevents:
        _process_loan_event(task, ls)

    adjustmentevents = mwsdecode.element_auto_list(financial_tree, 'AdjustmentEventList/AdjustmentEvent')
    for ae in adjustmentevents:
        _process_adjustment_event(task, ae)

    nexttoken_path = result + "/NextToken"
    nexttoken = mwsdecode.element_auto_text(tree, nexttoken_path)
    if nexttoken is None:
        task.task_finished()
    else:
        task.need_nexttoken(nexttoken)

def _process_shipmentevents(task, event, category):
    posteddate = mwsdecode.mws_datestr_to_datetime(mwsdecode.element_auto_text(event, 'PostedDate'))
    amazonorderid = mwsdecode.element_auto_text(event, 'AmazonOrderId')
    shipment, created = ShipmentEvent.objects.get_or_create(sellerid=task.sellerid, category=category,
                                                            amazonorderid=amazonorderid, posteddate=posteddate)
    if not created:
        # ignore if the evnet is recorded
        return
    shipment.sellerorderid = mwsdecode.element_auto_text(event, 'SellerOrderId')
    shipment.marketplacename = mwsdecode.element_auto_text(event, 'MarketplaceName')
    shipment.save()
    orderchargementlist = mwsdecode.element_auto_list(event, 'OrderChargeList/ChargeComponent')
    for ordercharge in orderchargementlist:
        _process_shipmentevent_charge(shipment, ordercharge, 'order')
    orderchargeadjustmentlist = mwsdecode.element_auto_list(event, 'OrderChargeAdjustmentList/ChargeComponent')
    for oj in orderchargeadjustmentlist:
        _process_shipmentevent_charge(shipment, oj, 'orderadjustment')
    shipmentfeelist = mwsdecode.element_auto_list(event, 'ShipmentFeeList/FeeComponent')
    for sf in shipmentfeelist:
        _process_shipmentevent_fee(shipment, sf, 'shipment')
    shipmentfeeadjustmentlist = mwsdecode.element_auto_list(event, 'ShipmentFeeAdjustmentList/FeeComponent')
    for sfa in shipmentfeeadjustmentlist:
        _process_shipmentevent_fee(shipment, sfa, 'shipmentadjustment')
    orderfeelist = mwsdecode.element_auto_list(event, 'OrderFeeList/FeeComponent')
    for of in orderfeelist:
        _process_shipmentevent_fee(shipment, of, 'order')
    orderfeeadjustmentlist = mwsdecode.element_auto_list(event, 'OrderFeeAdjustmentList/FeeComponent')
    for ofa in orderfeeadjustmentlist:
        _process_shipmentevent_fee(shipment, ofa, 'orderadjustment')
    directpaymentlist = mwsdecode.element_auto_list(event, 'DirectPaymentList/DirectPayment')
    for dp in directpaymentlist:
        _process_shipmentevent_direct(shipment, dp)
    shipmentitemlist = mwsdecode.element_auto_list(event, 'ShipmentItemList/ShipmentItem')
    for si in shipmentitemlist:
        _process_shipmentevent_item(shipment, si, 'normal')
    shipmentitemadjustmentlist = mwsdecode.element_auto_list(event, 'ShipmentItemAdjustmentList/ShipmentItem')
    for sia in shipmentitemadjustmentlist:
        _process_shipmentevent_item(shipment, sia, 'adjustment')


def _process_shipmentevent_charge(shipment, event, category):
    item = ShipmentChargeItem(shipmentevent=shipment, category=category)
    item.charegetype = mwsdecode.element_auto_text(event, 'ChargeType')
    item.charegeamount = _currency_money(item, event, 'ChargeAmount')
    item.save()


def _process_shipmentevent_fee(shipment, event, category):
    item = ShipmentFeeItem(shipmentevent=shipment, category=category)
    item.feetype = mwsdecode.element_auto_text(event, 'FeeType')
    item.feeamount = _currency_money(item, event, 'FeeAmount')
    item.save()


def _process_shipmentevent_direct(shipment, event):
    item = ShipmentDirectPaymentItem(shipmentevent=shipment)
    item.directpaymentpype = mwsdecode.element_auto_text(event, 'DirectPaymentType')
    item.directpaymentamount = _currency_money(item, event, 'DirectPaymentAmount')
    item.save()


def _process_shipmentevent_item(shipment, event, category):
    item = ShipmentItem(shipmentevent=shipment, category=category)
    item.sellersku = mwsdecode.element_auto_text(event, 'SellerSKU')
    item.orderitemid = mwsdecode.element_auto_text(event, 'OrderItemId')
    item.orderadjustmentitemid = mwsdecode.element_auto_text(event, 'OrderAdjustmentItemId')
    item.quantityshipped = int(mwsdecode.element_auto_text(event, 'QuantityShipped', '0'))
    item.costofpointsgranted = _currency_money(item, event, 'CostOfPointsGranted')
    item.cotofpointsreturned = _currency_money(item, event, 'CostOfPointsReturned')
    item.save()

    chargers = []
    itemchargelist = mwsdecode.element_auto_list(event, 'ItemChargeList/ChargeComponent')
    for ic in itemchargelist:
        chargers.append(_process_shipmentitem_charge(item, ic, 'normal'))
    itemchargeadjustmentlist = mwsdecode.element_auto_list(event, 'ItemChargeAdjustmentList/ChargeComponent')
    for ica in itemchargeadjustmentlist:
        chargers.append(_process_shipmentitem_charge(item, ica, 'adjustment'))
    for charger in chargers:
        item.charger = Decimal(item.charger) + Decimal(charger.charegeamount)
        item.currency = charger.currency

    fees = []
    itemfeelist = mwsdecode.element_auto_list(event, 'ItemFeeList/FeeComponent')
    for ifee in itemfeelist:
        fees.append(_process_shipmentitem_fee(item, ifee, 'normal'))
    itemfeeadjustmentlist = mwsdecode.element_auto_list(event, 'ItemFeeAdjustmentList/FeeComponent')
    for ifeea in itemfeeadjustmentlist:
        fees.append(_process_shipmentitem_fee(item, ifeea, 'adjustment'))
    for fee in fees:
        item.fee = Decimal(item.fee) + Decimal(fee.feeamount)

    promotions = []
    promotionlist = mwsdecode.element_auto_list(event, 'PromotionList/Promotion')
    for p in promotionlist:
        promotions.append(_process_shipmentitem_promoion(item, p, 'normal'))
    promotionadjustmentlist = mwsdecode.element_auto_list(event, 'PromotionAdjustmentList/Promotion')
    for pa in promotionadjustmentlist:
        promotions.append(_process_shipmentitem_promoion(item, pa, 'adjustment'))
    for promotion in promotions:
        item.promotion = Decimal(item.promotion) + Decimal(promotion.promotionamount)

    item.save()


def _process_shipmentitem_charge(shipmentitem, event, category):
    item = ShipmentItemChargeItem(shipmentitem=shipmentitem, category=category)
    item.charegetype = mwsdecode.element_auto_text(event, 'ChargeType')
    item.charegeamount = _currency_money(item, event, 'ChargeAmount')
    item.save()
    return item


def _process_shipmentitem_fee(shipmentitem, event, category):
    item = ShipmentItemFeeItem(shipmentitem=shipmentitem, category=category)
    item.feetype = mwsdecode.element_auto_text(event, 'FeeType')
    item.feeamount = _currency_money(item, event, 'FeeAmount')
    item.save()
    return item


def _process_shipmentitem_promoion(shipmentitem, event, category):
    item = ShipmentItemPromotionItem(shipmentitem=shipmentitem, category=category)
    item.promotiontype = mwsdecode.element_auto_text(event, 'PromotionType')
    item.promotionid = mwsdecode.element_auto_text(event, 'PromotionId')
    item.promotionamount = _currency_money(item, event, 'PromotionAmount')
    item.save()
    return item


def _process_paywithamazon_event(task, event):
    item = PayWithAmazonEvent(sellerid=task.sellerid)
    item.sellerorderid = mwsdecode.element_auto_text(event, 'SellerOrderId')
    item.transactionposteddate = mwsdecode.mws_datestr_to_datetime(mwsdecode.element_auto_text(event, 'TransactionPostedDate'))
    item.businessobjecttype = mwsdecode.element_auto_text(event, 'businessobjecttype')
    item.saleschannel = mwsdecode.element_auto_text(event, 'SalesChannel')
    item.charge_type = mwsdecode.element_auto_text(event, 'Charge/ChargeType')
    item.charge_amount = _currency_money(item, event, 'Charge/ChargeAmount')
    item.paymentamounttype = mwsdecode.element_auto_text(event, 'PaymentAmountType')
    item.amountdescription = mwsdecode.element_auto_text(event, 'AmountDescription')
    item.fulfillmentchannel = mwsdecode.element_auto_text(event, 'FulfillmentChannel')
    item.storename = mwsdecode.element_auto_text(event, 'StoreName')
    item.save()
    feelist = mwsdecode.element_auto_list(event, 'FeeList/FeeComponent')
    for fee in feelist:
        _process_paywithamazon_fee(item, event)


def _process_paywithamazon_fee(paywithamazon, event):
    item = PayWithAmazonFeeItem(paywithamazonevent=paywithamazon)
    item.feetype = mwsdecode.element_auto_text(event, 'FeeType')
    item.feeamount = _currency_money(item, event, 'FeeAmount')
    item.save()


def _process_serviceprovider_event(task, event):
    item = SolutionProviderCreditEvent(sellerid=task.sellerid)
    item.providertransactiontype = mwsdecode.element_auto_text(event, 'ProviderTransactionType')
    item.sellerorderid = mwsdecode.element_auto_text(event, 'SellerOrderId')
    item.marketplaceid = mwsdecode.element_auto_text(event, 'MarketplaceId')
    item.marketplacecountrycode = mwsdecode.element_auto_text(event, 'MarketplaceCountryCode')
    item.sellerstorename = mwsdecode.element_auto_text(event, 'SellerStoreName')
    item.providerid = mwsdecode.element_auto_text(event, 'ProviderId')
    item.providerstorename = mwsdecode.element_auto_text(event, 'ProviderStoreName')
    item.save()


def _process_retrocharge_event(task, event):
    amazonid = mwsdecode.element_auto_text(event, 'AmazonOrderId')
    posteddate = mwsdecode.mws_datestr_to_datetime(mwsdecode.element_auto_text(event, 'PostedDate'))
    item, created = RetrochargeEvent.objects.get_or_create(sellerid=task.sellerid, amazonorderid=amazonid,
                                                           posteddate=posteddate)
    if not created:
        return
    item.retrochargeeventtype = mwsdecode.element_auto_text(event, 'RetrochargeEventType')
    item.basetax = _currency_money(item, event, 'BaseTax')
    item.shippingtax = _currency_money(item, event, 'ShippingTax')
    item.marketplacename = mwsdecode.element_auto_text(event, 'MarketplaceName')
    item.save()


def _process_rental_event(task, event):
    amazonid = mwsdecode.element_auto_text(event, 'AmazonOrderId')
    posteddate = mwsdecode.mws_datestr_to_datetime(mwsdecode.element_auto_text(event, 'PostedDate'))
    tetype = mwsdecode.element_auto_text(event, 'RentalEventType')
    item, created = RentalTransactionEvent.objects.get_or_create(sellerid=task.sellerid, amazonorderid=amazonid,
                                                                 posteddate=posteddate, rentaleventtype=tetype)
    if not created:
        return
    item.extensionlength = int(mwsdecode.element_auto_text(event, 'ExtensionLength', '0'))
    item.marketplacename = mwsdecode.element_auto_text(event, 'MarketplaceName')
    item.rentalinitialvalue = _currency_money(item, event, 'RentalInitialValue')
    item.rentalreimbursement = _currency_money(item, event, 'RentalReimbursement')
    item.save()
    chargelist = mwsdecode.element_auto_list(event, 'RentalChargeList/ChargeComponent')
    for cl in chargelist:
       _process_rental_event_charge(item, cl)
    feelist = mwsdecode.element_auto_list(event, 'RentalFeeList/FeeComponent')
    for fl in feelist:
       _process_rental_event_fee(item, fl)


def _process_rental_event_charge(rental, event):
    item = RentalTransactionChargeItem(rentaltransactionevent=rental)
    item.charegetype = mwsdecode.element_auto_text(event, 'ChargeType')
    item.charegeamount = _currency_money(item, event, 'ChargeAmount')
    item.save()


def _process_rental_event_fee(rental, event):
    item = RentalTransactionFeeItem(rentaltransactionevent=rental)
    item.feetype = mwsdecode.element_auto_text(event, 'FeeType')
    item.feeamount = _currency_money(item, event, 'FeeAmount')
    item.save()


def _process_performance_event(task, event):
    item = PerformanceBondRefundEvent(sellerid=task.sellerid)
    item.marketplacecountrycode = mwsdecode.element_auto_text(event, 'MarketplaceCountryCode')
    item.amount = _currency_money(item, event, 'Amount')
    groupids = mwsdecode.element_auto_list(event, 'ProductGroupList/ProductGroup')
    pgids = map(lambda x: x.text, groupids)
    item.productgrouplist = ",".join(pgids)
    item.save()


def _process_servicefee_event(task, event):
    item = ServiceFeeEvent(sellerid=task.sellerid)
    item.amazonorderid = mwsdecode.element_auto_text(event, 'AmazonOrderId')
    item.feereason = mwsdecode.element_auto_text(event, 'FeeReason')
    item.sellersku = mwsdecode.element_auto_text(event, 'SellerSKU')
    item.fnsku = mwsdecode.element_auto_text(event, 'FnSKU')
    item.feedescription = mwsdecode.element_auto_text(event, 'FeeDescription')
    item.asin = mwsdecode.element_auto_text(event, 'ASIN')
    item.postdate = task.last_after_datetime
    item.save()
    feelist = mwsdecode.element_auto_list(event, 'FeeList/FeeComponent')
    for fl in feelist:
        _process_servicefee_event_fee(item, fl)


def _process_servicefee_event_fee( service, event):
    item = ServiceFeeEventFeeItem(servicefeeevent=service)
    item.feetype = mwsdecode.element_auto_text(event, 'FeeType')
    item.feeamount = _currency_money(item, event, 'FeeAmount')
    item.save()

def _process_debt_event(task, event):
    item = DebtRecoveryEvent(sellerid=task.sellerid)
    item.debtrecoverytype = mwsdecode.element_auto_text(event, 'DebtRecoveryType')
    item.recoveryamount = _currency_money(item, event, 'RecoveryAmount')
    item.overpaymentcredit = _currency_money(item, event, 'OverPaymentCredit')
    item.save()
    debtitems = mwsdecode.element_auto_list(event, 'DebtRecoveryItemList/DebtRecoveryItem')
    for db in debtitems:
        _process_debt_event_item(item, db)

    chargeinstruments = mwsdecode.element_auto_list(event, 'ChargeInstrumentList/ChargeInstrument')
    for ci in chargeinstruments:
        _process_debt_event_charge(item, ci)


def _process_debt_event_item(debt, event):
    item = DebtRecoveryItem(debtrecoveryevent=debt)
    item.recoveryamount = _currency_money(item, event, 'RecoveryAmount')
    item.originalamount = _currency_money(item, event, 'OriginalAmount')
    item.groupbegindate = mwsdecode.mws_datestr_to_datetime(mwsdecode.element_auto_text(event, 'GroupBeginDate'))
    item.groupenddate = mwsdecode.mws_datestr_to_datetime(mwsdecode.element_auto_text(event, 'GroupEndDate'))
    item.save()


def _process_debt_event_charge(debt, event):
    item = DebtRecoveryChargeInstrumentItem(debtrecoveryevent=debt)
    item.description = mwsdecode.element_auto_text(event, 'Description')
    item.tail = mwsdecode.element_auto_text(event, 'Tail')
    item.amount = _currency_money(item, event, 'Amount')
    item.save()


def _process_loan_event(task, event):
    item = LoanServicingEvent(sellerid=task.sellerid)
    item.loanamount = _currency_money(item, event, 'LoanAmount')
    item.sourcebusinesseventtype = mwsdecode.element_auto_text(event, 'SourceBusinessEventType')
    item.save()


def _process_adjustment_event(task, event):
    item = AdjustmentEvent(sellerid=task.sellerid)
    item.adjustmenttype = mwsdecode.element_auto_text(event, 'AdjustmentType')
    item.adjustmentamount = _currency_money(item, event, 'AdjustmentAmount')
    item.post_date = task.last_after_datetime
    item.save()
    items = mwsdecode.element_auto_list(event, 'AdjustmentItemList/AdjustmentItem')
    for it in items:
        _process_adjustment_event_item(item, it)


def _process_adjustment_event_item(ad, event):
    item = AdjustmentItem(adjustmentevnet=ad)
    item.quantity = int(mwsdecode.element_auto_text(event, 'Quantity', '0'))
    item.perunitamount = _currency_money(item, event, 'PerUnitAmount')
    item.totalamount = _currency_money(item, event, 'TotalAmount')
    item.seller_sku = mwsdecode.element_auto_text(event, 'SellerSKU')
    item.fnsku = mwsdecode.element_auto_text(event, 'FnSKU')
    item.productdescription = mwsdecode.element_auto_text(event, 'ProductDescription')
    item.asin = mwsdecode.element_auto_text(event, 'ASIN')
    item.save()


def _currency_money(dbmodel, element, tag):
    amount = tag + "/CurrencyAmount"
    currency = tag + '/CurrencyCode'
    amount_value = mwsdecode.element_auto_text(element, amount, '0.0')
    cureency_code = mwsdecode.element_auto_text(element, currency)
    if cureency_code is not None and dbmodel.currency is None:
        dbmodel.currency = cureency_code
    return amount_value