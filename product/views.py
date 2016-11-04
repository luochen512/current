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
    for task in tasklist:
        process_task(shop, task)
    return JsonResponse(data)


def do_request_Post( uri, data):
    try:
        headers = {"Content-type": "application/json"}
        url = "http://sales.sundix.net" + uri
        response = requests.request('post', url, data=json.dumps(data), headers=headers)
        data = response.content
        return data
    except Exception as e:
        return None
    return None


def do_request_Get(sellerid, uri, data):
    try:
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
        url = "http://sales.sundix.net/MonitorSkuManage/MwsAPI?seller_id=%s" % sellerid
        response = requests.request('GET', url, data=None, headers=headers)
        data = response.json()
        return data
    except Exception:
        return None
    return None


def process_task(shop, task):
    params = {}
    params['Version'] = "2011-10-01"
    params['AWSAccessKeyId'] = shop.access_key
    params['SellerId'] = shop.sellerid
    params['SellerSKU'] = task['sellersku']
    params['MarketplaceId'] = task['marketplaceid']
    params['ItemCondition'] = "New"
    params['Action'] = 'GetLowestPricedOffersForSKU'
    params.update(mwssignature.normal_params())
    request_params = mwssignature.dict_params_urlcode(params, True)
    params['Signature'] = mwssignature.calc_signature(shop.mws_url, '/Products/2011-10-01', shop.secret_key,
                                                      request_params)
    mws_data = {
        "sellerid": shop.sellerid,
        "nodeIP": shop.vps_ip,
        "url": shop.mws_url,
        "action": params['Action'],
        "uri": "/Products/2011-10-01",
        "appName": shop.app_name(),
        "appVersion": shop.app_version(),
        "params": mwssignature.dict_params_urlcode(params)
    }
    url = shop.request_url()
    response = mwsnode.request_node(url, mws_data)
    _process_response(shop,  response)
    return

def _process_response(shop, response):
    """
    处理返回结果
    :param task:
    :return:
    """
    reponseok = True
    if response is None or response['code'] !=  '00000':
        logger.info("response error %s " % response)
        reponseok = False
        return
    tree = mwsdecode.tree_ignore_namepace(response['mwsResponse'])
    if tree is None:
        reponseok = False
        return
    if mwsdecode.is_error_response(tree):
        logger.info("%s reponse error: %s" % (shop.sellerid, response))
        reponseok = False
    if not reponseok:
        reponse_api(code="00014", msg="error")
        return
    data = {}
    data["sellerid"] = shop.sellerid
    data["marketplaceid"] = mwsdecode.element_auto_text(tree, 'GetLowestPricedOffersForSKUResult/Identifier/MarketplaceId')
    data["sellersku"] =  mwsdecode.element_auto_text(tree, 'GetLowestPricedOffersForSKUResult/Identifier/SellerSKU')
    data["numberOfOffers"] = int(
        mwsdecode.element_auto_text(tree, 'GetLowestPricedOffersForSKUResult/Summary/TotalOfferCount', '0'))
    data["currency"] = ""
    data['lowestLandPrice'] = 10000.0
    data['lowestListingPrice'] = 10000.0
    data['lowestShippingPrice'] = 10000.0
    lowestPrices = mwsdecode.element_auto_list(tree, 'GetLowestPricedOffersForSKUResult/Summary/LowestPrices/LowestPrice')
    for lowest in lowestPrices:
        condition = lowest.get("condition", 'used')
        fulfillmentChannel = lowest.get('fulfillmentChannel', 'Merchant')
        if condition not in ['new', 'New']:
            continue
        lowest_land_price = float(_currency_money(data, lowest, 'LandedPrice'))
        lowest_listing_price = float(_currency_money(data, lowest, 'ListingPrice'))
        lowest_shipping_price = float(_currency_money(data, lowest, 'Shipping'))
        if data['lowestListingPrice'] < lowest_listing_price:
            continue
        data["lowestFulfillment"] = fulfillmentChannel
        data['lowestLandPrice'] = lowest_land_price
        data['lowestListingPrice'] = lowest_listing_price
        data['lowestShippingPrice'] = lowest_shipping_price
    buyboxps = mwsdecode.element_auto_list(tree, 'GetLowestPricedOffersForSKUResult/Summary/BuyBoxPrices/BuyBoxPrice')
    for buybox in buyboxps:
        condition = lowest.get("condition", 'used')
        if condition not in ['New', 'new']:
            continue
        data["buyboxLandPrice"] = float(_currency_money(data, buybox, 'LandedPrice'))
        data['buyboxListingPrice'] = float(_currency_money(data, buybox, 'ListingPrice'))
        data['buyboxShippingPrice'] = float(_currency_money(data, buybox, 'Shipping'))
    if data["numberOfOffers"] > 0:
        offers = mwsdecode.element_auto_list(tree, 'GetLowestPricedOffersForSKUResult/Offers/Offer')
        for offer in offers:
            myoffer = mwsdecode.mws_boolean(mwsdecode.element_auto_text(offer, 'MyOffer', 'false'))
            if not myoffer:
                continue
            isFBA = mwsdecode.mws_boolean(mwsdecode.element_auto_text(offer, 'IsFulfilledByAmazon', 'false'))
            data['myFulfillment'] = 'Amazon' if isFBA else 'Merchant'
            data['myListingPrice'] = float(_currency_money(data, offer, 'ListingPrice'))
            data['myShippingPrice'] = float(_currency_money(data, offer, 'Shipping'))
            data['buyboxWinner'] = mwsdecode.mws_boolean(mwsdecode.element_auto_text(offer, 'IsBuyBoxWinner', 'false'))
    if data['lowestListingPrice'] == 10000.0:
        data['lowestLandPrice'] = data['lowestListingPrice'] = data['lowestShippingPrice'] = 0.0
    reponse_api(code="00000", msg="success", data=data)


def reponse_api(code="00000", msg='success', data=None):
    params = {"code": code, "msg": msg}
    uri = "/MwsReturnBuyBoxDatas/mwsReturnDatas"
    if data is not None:
        params['data'] = data
    ds = do_request_Post(uri=uri, data=params)


def _currency_money(data, element, tag):
    amount = tag + "/Amount"
    currency = tag + '/CurrencyCode'
    amount_value = mwsdecode.element_auto_text(element, amount, '0.0')
    cureency_code = mwsdecode.element_auto_text(element, currency)
    if cureency_code is not None and data["currency"] is None:
        data["currency"] = cureency_code
    return amount_value