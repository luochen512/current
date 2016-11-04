# -*- coding: utf-8 -*-
import requests
import logging
import json

logger = logging.getLogger('mws_log')
def request_node(url, mws_data):
    """
    请求mws node节点服务
    :param url:
    :param mws_data:
    :return:
    """
    try:
        headers = {"Content-type": "application/text;charset=utf-8"}
        response = requests.request('post', url, data=json.dumps(mws_data), headers=headers)
        # logger.info("response: %s" % str(response.content))
        data = response.json()
        #logger.info("response: %s" % str(response.content))
        return data
    except Exception as e:
        logger.info("%s  request error: %s" % (url, e.message))
        return None