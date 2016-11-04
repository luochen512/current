# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import JsonResponse
from shop.models import Shop
from order.models import OrderListItemTask, Order, OrderItem
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from datetime import datetime, timedelta
from utils import mwssignature, mwsdatetime, mwsnode, mwsdecode
import logging


logger = logging.getLogger('mws_orderitem')
# Create your views here.
def listorderitems(request, sellerid):
    data = {'code': '00000', 'msg': 'Success'}
    if sellerid is None:
        data['code'] = u'00001'
        data['msg'] = u'sellerid is None!'
        return JsonResponse(data)
    try:
        shop = Shop.objects.get(sellerid=sellerid)
        task, created = OrderListItemTask.objects.get_or_create(sellerid=sellerid)
        if created:
            task.shop_name = shop.brand_name
            task.start_work_datetime = datetime.utcnow()
            task.save()
        timeout = task.is_timeout()
        working = task.is_working()
        throttling = task.is_throttling()
        if throttling:
            data['code'] = u'00004'
            data['msg'] = u'ListOrderItems (%s) is throttling !' % str(sellerid)
            return JsonResponse(data)
        if working and not timeout:
            data['code'] = u'00005'
            data['msg'] = u'ListOrderItems (%s) is Working !' % str(sellerid)
            return JsonResponse(data)
        if timeout:
            logger.info("time out, rest  task")
            task.reset_init()
        data = _dispatch_task(shop, task)
    except ObjectDoesNotExist as e:
        data['code'] = u'00002'
        data['msg'] = u'sellerid(%s) is not Exist ListOrderItems !' % str(sellerid)
        return JsonResponse(data)
    except MultipleObjectsReturned as e:
        data['code'] = u'00003'
        data['msg'] = u'ListOrderItems multiple sellerids %s' % str(sellerid)
        return JsonResponse(data)
    return JsonResponse(data)


def _dispatch_task(shop, task):
    data = {'code': '00000', 'msg': 'Success'}
    url = shop.request_url()
    params = {}
    params['Version'] = "2013-09-01"
    params['AWSAccessKeyId'] = shop.access_key
    params['SellerId'] = shop.sellerid
    params.update(mwssignature.normal_params())
    if task.has_next:
        params['Action'] = 'ListOrderItemsByNextToken'
        params['NextToken'] = task.next_token
    else:
        params['Action'] = 'ListOrderItems'
        amazon_order_id = _get_amazon_order_id(task)
        if amazon_order_id is None:
            return {'code': '00010', 'msg': 'unfind order id %s' % (amazon_order_id)}
        params['AmazonOrderId'] = amazon_order_id
    request_params = mwssignature.dict_params_urlcode(params, True)
    params['Signature'] = mwssignature.calc_signature(shop.mws_url, '/Orders/2013-09-01', shop.secret_key,
                                                      request_params)
    mws_data = {
        "sellerid": shop.sellerid,
        "nodeIP": shop.vps_ip,
        "url": shop.mws_url,
        "action": params['Action'],
        "uri": "/Orders/2013-09-01",
        "appName": shop.app_name(),
        "appVersion": shop.app_version(),
        "params": mwssignature.dict_params_urlcode(params)
    }
    url = shop.request_url()
    task.start_working()
    response = mwsnode.request_node(url, mws_data)
    _process_response(task, response)
    return data


def _get_amazon_order_id(task):
    orders = Order.objects.filter(sellerid=task.sellerid, pulled_items=0, order_status='Unshipped')[:3]
    if orders.count() > 0:
        logger.info("unshipped order")
        return orders[0].amazon_order_id

    orders = Order.objects.filter(sellerid=task.sellerid, pulled_items=0, order_status='Pending', fulfillment_channel='AFN')[:3]
    if orders.count() > 0:
        logger.info("Pending order")
        return orders[0].amazon_order_id

    orders = Order.objects.filter(sellerid=task.sellerid, pulled_items=0, order_status='Shipped').order_by(
        '-purchase_date')[:3]
    if orders.count() > 0:
        logger.info("Shipped order")
        return orders[0].amazon_order_id

    orders = Order.objects.filter(sellerid=task.sellerid, pulled_items=1,) \
                 .order_by('-purchase_date')[:3]
    if orders.count() > 0:
        return orders[0].amazon_order_id
    return None


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
    result = ""
    if response['action'] == 'ListOrderItems':
        result = 'ListOrderItemsResult'
    elif response['action'] == 'ListOrderItemsByNextToken':
        result = 'ListOrderItemsByNextTokenResult'
    items = mwsdecode.element_auto_list(tree, ('%s/OrderItems/OrderItem' % result))
    amazon_order_id = mwsdecode.element_auto_text(tree, ('%s/AmazonOrderId' % result))
    try:
        order = Order.objects.get(sellerid=task.sellerid, amazon_order_id=amazon_order_id)
        for item in items:
            _process_orderitem(order=order, amazon_order_id=amazon_order_id, itemele=item)
        if order.order_status in ['Shipped', 'InvoiceUnconfirmed', 'Canceled', 'Unfulfillable']:
            order.pulled_items = 2
        else:
            order.pulled_items = 1
        order.save()
    except MultipleObjectsReturned:
        logger.info("find MultipleObjectsReturned on order %s-%s" % task.sellerid, amazon_order_id )
    nexttoken = mwsdecode.element_auto_text(tree, ('%s/NextToken' % result))
    if nexttoken is None:
        task.task_finished()
    else:
        task.need_nexttoken(nexttoken)

def _process_orderitem(order, amazon_order_id, itemele):
    orderitemid = mwsdecode.element_auto_text(itemele, 'OrderItemId')
    item, created = OrderItem.objects.get_or_create(order_item_id=orderitemid,
                                                    sellerid=order.sellerid,
                                                    amazon_order_id=order.amazon_order_id )
    if created:
        item.purchase_date = order.purchase_date
        item.fulfillment_channel = order.fulfillment_channel
        item.phone = order.phone
        item.marketplaceid = order.marketplaceid
        item.asin = mwsdecode.element_auto_text(itemele, 'ASIN')
        item.seller_sku = mwsdecode.element_auto_text(itemele, 'SellerSKU')
    item.customized_url = mwsdecode.element_auto_text(itemele, 'BuyerCustomizedInfo/CustomizedURL')
    item.title = mwsdecode.element_auto_text(itemele, 'Title')
    item.quantity_ordered = int(mwsdecode.element_auto_text(itemele, 'QuantityOrdered', '0'))
    item.quantity_shipped = int(mwsdecode.element_auto_text(itemele, 'QuantityShipped', '0'))
    item.points_number = int(mwsdecode.element_auto_text(itemele, 'PointsGranted/PointsNumber', '0'))
    item.points_monetary_value = _orderitem_money(item, itemele, 'PointsGranted/PointsMonetaryValue')
    item.item_price = _orderitem_money(item, itemele, 'ItemPrice')
    item.shipping_price = _orderitem_money(item, itemele, 'ShippingPrice')
    item.gift_wrap_price = _orderitem_money(item, itemele, 'GiftWrapPrice')
    item.item_tax = _orderitem_money(item, itemele, 'ItemTax')
    item.shipping_tax = _orderitem_money(item, itemele, 'ShippingTax')
    item.gift_wrap_tax = _orderitem_money(item, itemele, 'GiftWrapTax')
    item.shipping_discount = _orderitem_money(item, itemele, 'ShippingDiscount')
    item.promotion_discount = _orderitem_money(item, itemele, 'PromotionDiscount')
    promotionids = mwsdecode.element_auto_list(itemele, 'PromotionIds/PromotionId')
    pids = map(lambda x: x.text, promotionids)
    item.promotion_ids = ",".join(pids)
    item.cod_fee = _orderitem_money(item, itemele, 'CODFee')
    item.cod_fee_discount = _orderitem_money(item, itemele, 'CODFeeDiscount')
    item.gift_message_text = mwsdecode.element_auto_text(itemele, 'GiftMessageText')
    item.gift_wrap_level = mwsdecode.element_auto_text(itemele, 'GiftWrapLevel')
    item.invoice_requirement = mwsdecode.element_auto_text(itemele, 'InvoiceData/InvoiceRequirement')
    item.buyer_selected_invoice_category = mwsdecode.element_auto_text(itemele, 'InvoiceData/BuyerSelectedInvoiceCategory')
    item.invoice_title = mwsdecode.element_auto_text(itemele, 'InvoiceData/InvoiceTitle')
    item.invoice_information = mwsdecode.element_auto_text(itemele, 'InvoiceData/InvoiceInformation')
    item.condition_note = mwsdecode.element_auto_text(itemele, 'ConditionNote')
    item.conditionid = mwsdecode.element_auto_text(itemele, 'ConditionId')
    item.condition_subtype_id = mwsdecode.element_auto_text(itemele, 'ConditionSubtypeId')
    item.scheduled_delivery_start_date = mwsdecode.element_auto_text(itemele, 'ScheduledDeliveryStartDate')
    item.scheduled_delivery_end_date = mwsdecode.element_auto_text(itemele, 'ScheduledDeliveryEndDate')
    item.price_designation = mwsdecode.element_auto_text(itemele, 'PriceDesignation')
    item.save()


def _orderitem_money(orderitem, element, tag):
    amount = tag + "/Amount"
    currency = tag + '/CurrencyCode'
    amount_value = mwsdecode.element_auto_text(element, amount, '0.0')
    cureency_code = mwsdecode.element_auto_text(element, currency)
    if cureency_code is not None and orderitem.item_currency is None:
        orderitem.item_currency = cureency_code
    return amount_value