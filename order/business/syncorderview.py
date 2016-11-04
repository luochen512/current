# -*- coding: utf-8 -*-
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from order.models import Order, OrderItem
from db_sales import stamps
from datetime import timedelta
import time
import logging

logger = logging.getLogger('mws_info')

@csrf_exempt
def unshipped_sync(request):
    data={'code': '0000', 'msg': 'Success'}
    start = time.time()
    stamps.update_order_status()
    logger.info('update_order_status: ' + str(time.time()-start))
    orders = Order.objects.filter(order_status='Unshipped', fulfillment_channel='MFN', marketplaceid='ATVPDKIKX0DER' ,pulled_items__gt=0)
    logger.info("orders: " + str(orders.count()))
    for order in orders:
        if order.phone is not None and (order.phone.endswith('8365') or order.phone.endswith('6583')):
            continue
        stamp_order = stamps.stamp_order(order.amazon_order_id, order.sellerid)
        if not stamp_order.has_key('amazon_order_id'):
            stamps.insert_order(order)
        items = OrderItem.objects.filter(amazon_order_id=order.amazon_order_id, sellerid=order.sellerid, marketplaceid=order.marketplaceid)
        dictitems = {}
        for item in items:
            key = '%s-%s-%s-%s' % (item.amazon_order_id, item.sellerid, item.marketplaceid, item.seller_sku)
            value = {"quantity": item.quantity_ordered, "item": item}
            if dictitems.has_key(key):
                dictitems.get(key)['quantity'] += item.quantity_ordered
            else:
                dictitems[key] = value
        for k, v in dictitems.items():
            order_item = stamps.order_item(order, v['item'])
            if order_item.has_key('amazon_order_id'):
                continue
            stamps.insert_order_item(order, v['item'], v['quantity'])
    start2 = time.time()
    logger.info('sync order: ' + str(start2-start))
    stamps.update_order_marketplaceid()
    stamps.update_order_item_stampsid()
    stamps.update_order_item_shop_productid()
    logger.info('update id: ' + str(time.time()-start2))
    logger.info("total : " + str(time.time() - start))
    return JsonResponse(data)