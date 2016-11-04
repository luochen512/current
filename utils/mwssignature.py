# -*- coding: utf-8 -*-
import hashlib
import hmac
import base64
import urllib2
from datetime import datetime

def dict_params_urlcode(params, sort=False):
    if sort:
        return '&'.join(['%s=%s' % (k, urllib2.quote(params[k], safe='-_.~').encode('utf-8')) for k in sorted(params)])
    return '&'.join(['%s=%s' % (k, urllib2.quote(params[k], safe='-_.~').encode('utf-8')) for k in params])


def calc_signature(mws_url, uri, secret_key, request_description):
    """Calculate MWS signature to interface with Amazon
    """
    sig_data = "POST" + '\n' + mws_url.replace('https://', '').lower() + '\n' \
               + uri + '\n' + request_description
    return base64.b64encode(hmac.new(str(secret_key), sig_data, hashlib.sha256).digest())

def normal_params():
    """
    :param kwargs:
    :return:
    """
    params = {}
    params['SignatureMethod'] = 'HmacSHA256'
    params['SignatureVersion'] = '2'
    params['Timestamp'] = datetime.utcnow().isoformat() + "Z"
    return params