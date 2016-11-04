# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import JsonResponse
from shop.models import Shop
from order.models import OrderListTask, Order
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from datetime import datetime, timedelta
from utils import mwssignature, mwsdatetime, mwsnode, mwsdecode
import logging


logger = logging.getLogger('mws_listorder')
def ListOrder(request, sellerid):
    data={'code': '00000', 'msg': 'Success'}
    if sellerid is None:
        data['code'] = u'00001'
        data['msg'] = u'sellerid is None!'
        return JsonResponse(data)
    try:
        shop = Shop.objects.get(sellerid=sellerid)
        task, created = OrderListTask.objects.get_or_create(sellerid=sellerid)
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
            data['msg'] = u'ListOrder (%s) is throttling !' % str(sellerid)
            return JsonResponse(data)
        if working and not timeout:
            data['code'] = u'00005'
            data['msg'] = u'ListOrder (%s) is Working !' % str(sellerid)
            return JsonResponse(data)
        if timeout:
            logger.info("time out, rest  task")
            task.reset_init()
        data = _dispatch_task(shop, task)
    except ObjectDoesNotExist as e:
        data['code'] = u'00002'
        data['msg'] = u'sellerid(%s) is not Exist !' % str(sellerid)
        return JsonResponse(data)
    except MultipleObjectsReturned as e:
        data['code'] = u'00003'
        data['msg'] = u'multiple sellerids %s' % str(sellerid)
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
        params['Action'] = 'ListOrdersByNextToken'
        params['NextToken'] = task.next_token
    else:
        params['Action'] = 'ListOrders'
        params.update(shop.marketplaceIds())
        update_times = _last_update_time(shop, task)
        if update_times is None:
            data['code'] = '00009'
            data['msg'] = 'lastupdatetime error'
            return data
        params.update(update_times)
    request_params = mwssignature.dict_params_urlcode(params, True)
    params['Signature'] = mwssignature.calc_signature(shop.mws_url, '/Orders/2013-09-01', shop.secret_key, request_params)
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
    params['LastUpdatedAfter'] = after_date.isoformat() + "Z"
    params['LastUpdatedBefore'] = before_date.isoformat() + "Z"
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
    if response is None or response['code'] !=  '00000':
        logger.info("response error %s " % response)
        task.reset_init()
        return
    tree = mwsdecode.tree_ignore_namepace(response['mwsResponse'])
    if tree is None:
        return
    task.update_last_request_time()
    if mwsdecode.is_error_response(tree):
        logger.info("%s reponse error: %s" % (task.sellerid, response))
        return
    result = ''
    if response['action'] == 'ListOrders':
        result = 'ListOrdersResult'
    elif response['action'] == 'ListOrdersByNextToken':
        result = 'ListOrdersByNextTokenResult'
    orders_path = result + '/Orders/Order'
    orders = mwsdecode.element_auto_list(tree, orders_path)
    for item in orders:
        _process_order(task, item)
    nexttoken_path = result + "/NextToken"
    nexttoken = mwsdecode.element_auto_text(tree, nexttoken_path)
    if nexttoken is None:
        task.task_finished()
    else:
        task.need_nexttoken(nexttoken)


def _process_order(task, order):
    torder, created = Order.objects.get_or_create(sellerid=task.sellerid,
                                                  amazon_order_id=mwsdecode.element_auto_text(order, 'AmazonOrderId'))
    status = mwsdecode.element_auto_text(order, 'OrderStatus')
    if created or torder.order_status != status:
        torder.seller_order_id = mwsdecode.element_auto_text(order, 'SellerOrderId')
        torder.purchase_date = mwsdecode.mws_datestr_to_datetime(mwsdecode.element_auto_text(order, 'PurchaseDate'))
        torder.last_update_date = mwsdecode.mws_datestr_to_datetime(mwsdecode.element_auto_text(order, 'LastUpdateDate'))
        torder.order_status = status
        torder.fulfillment_channel = mwsdecode.element_auto_text(order, 'FulfillmentChannel')
        torder.sales_channel = mwsdecode.element_auto_text(order, 'SalesChannel')
        torder.order_channel = mwsdecode.element_auto_text(order, 'OrderChannel')
        torder.ship_service_level = mwsdecode.element_auto_text(order, 'ShipServiceLevel')
        torder.recipient_name = mwsdecode.element_auto_text(order, 'ShippingAddress/Name')
        torder.address_line1 = mwsdecode.element_auto_text(order, 'ShippingAddress/AddressLine1')
        torder.address_line2 = mwsdecode.element_auto_text(order, 'ShippingAddress/AddressLine2')
        torder.address_line3 = mwsdecode.element_auto_text(order, 'ShippingAddress/AddressLine3')
        torder.city = mwsdecode.element_auto_text(order, 'ShippingAddress/City')
        torder.county = mwsdecode.element_auto_text(order, 'ShippingAddress/County')
        torder.district = mwsdecode.element_auto_text(order, 'ShippingAddress/district')
        torder.state_or_region = mwsdecode.element_auto_text(order, 'ShippingAddress/StateOrRegion')
        torder.postal_code = mwsdecode.element_auto_text(order, 'ShippingAddress/PostalCode')
        torder.country_code = mwsdecode.element_auto_text(order, 'ShippingAddress/CountryCode')
        torder.phone = mwsdecode.element_auto_text(order, 'ShippingAddress/Phone')
        torder.order_currency_code = mwsdecode.element_auto_text(order, 'OrderTotal/CurrencyCode')
        torder.order_total_amount = mwsdecode.element_auto_text(order, 'OrderTotal/Amount', '0.0')
        torder.number_items_shipped = int(mwsdecode.element_auto_text(order, 'NumberOfItemsShipped', '0'))
        torder.number_items_unshipped = int(mwsdecode.element_auto_text(order, 'NumberOfItemsUnshipped', '0'))
        # payment_execution_detail = order.get("PaymentExecutionDetail", None) # object ignore
        torder.payment_method = mwsdecode.element_auto_text(order, 'PaymentMethod')
        torder.marketplaceid = mwsdecode.element_auto_text(order, 'MarketplaceId')
        torder.buyer_email = mwsdecode.element_auto_text(order, 'BuyerEmail')
        torder.buyer_name = mwsdecode.element_auto_text(order, 'BuyerName')
        torder.shipment_service_level_category = mwsdecode.element_auto_text(order, 'ShipmentServiceLevelCategory')
        torder.shipped_by_amazon_tfm = mwsdecode.mws_boolean(mwsdecode.element_auto_text(order, 'ShippedByAmazonTFM', 'false'))
        torder.tfm_shipment_status = mwsdecode.element_auto_text(order, 'TFMShipmentStatus')
        torder.cba_displayable_shipping_label = mwsdecode.element_auto_text(order, 'CbaDisplayableShippingLabel')
        torder.order_type = mwsdecode.element_auto_text(order, 'OrderType')
        torder.earliest_ship_date = mwsdecode.mws_datestr_to_datetime(mwsdecode.element_auto_text(order, 'EarliestShipDate'))
        torder.latest_ship_date = mwsdecode.mws_datestr_to_datetime(mwsdecode.element_auto_text(order, 'LatestShipDate'))
        torder.earliest_delivery_date = mwsdecode.mws_datestr_to_datetime( mwsdecode.element_auto_text(order, 'EarliestDeliveryDate'))
        torder.latest_delivery_date = mwsdecode.mws_datestr_to_datetime(mwsdecode.element_auto_text(order, 'LatestDeliveryDate'))
        torder.is_business_order = mwsdecode.mws_boolean(mwsdecode.element_auto_text(order, 'IsBusinessOrder', 'false'))
        torder.purchase_order_number = mwsdecode.element_auto_text(order, 'PurchaseOrderNumber')
        torder.is_prime = mwsdecode.mws_boolean(mwsdecode.element_auto_text(order, 'IsPrime', 'false'))
        torder.is_premenum_order = mwsdecode.mws_boolean(mwsdecode.element_auto_text(order, 'IsPremiumOrder', 'false'))
        torder.save()