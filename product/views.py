# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import JsonResponse
from shop.models import Shop
from order.models import OrderListTask, Order
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from datetime import datetime, timedelta
from utils import mwssignature, mwsdatetime, mwsnode, mwsdecode
import requests
import json
import logging

logger = logging.getLogger('mws_product')
def lowest_priced_sku(request, sellerid):
    data = {'code': '00000', 'msg': 'Success'}
    if sellerid is None:
        data['code'] = u'00001'
        data['msg'] = u'sellerid is None!'
        return JsonResponse(data)
    shop = Shop.objects.get(sellerid=sellerid)
    uri = '/MonitorSkuManage/MwsAPI'
    params = {'seller_id': sellerid}
    response = do_request_Get(sellerid=sellerid, uri=uri, data=params)
    if response is None or response.get('code', None) != '00000' or response.get('datas', None) is None:
        data['code'] = u'00004'
        data['msg'] = u'LowestPricedSKU (%s) no sku !' % str(sellerid)
        return JsonResponse(data)
    tasklist = response.get('datas').get('sellerskuTaskList')
    pbtasks = []
    for task in tasklist:
        pbtasks.append(process_task(shop, task))
    return JsonResponse(data)


def do_request_Post( uri, data):
    try:
        headers = {"Content-type": "application/json"}
        url = "http://119.29.4.96:8081" + uri
        response = requests.request('post', url, data=json.dumps(data), headers=headers)
        data = response.content
        return data
    except Exception:
        return None
    return None


def do_request_Get(sellerid, uri, data):
    try:
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        url = "http://119.29.4.96:8081/MonitorSkuManage/MwsAPI?seller_id=%s" % sellerid
        response = requests.request('GET', url, data=None, headers=headers)
        data = response.json()
        return data
    except Exception:
        return None
    return None


def process_task(shop, task):
    params = {}
    params['SellerSKU'] = task['sellersku']
    params['MarketplaceId'] = task['marketplaceid']
    params['ItemCondition'] = "New"
    params['Action'] = 'GetLowestPricedOffersForSKU'
    params_str = self.dict_params_urlcode(self.get_params(params))
    pb = mws_pb2.MWSTask()
    pb.taskid = 0
    pb.uri = self.URI
    pb.name = "unname"
    pb.uuid = "uicn"
    pb.action = 'GetLowestPricedOffersForSKU'
    pb.url = self.shop.mws_url
    pb.params = params_str
    pb.appname = self.shop.app_name()
    pb.appversion = self.shop.app_version()
    return pb