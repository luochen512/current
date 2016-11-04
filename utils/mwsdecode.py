# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
from datetime import datetime


def tree_ignore_namepace( mwsresponse, namespace='xmlns'):
    if mwsresponse is None:
        return None
    try:
        replace = namespace + "ignore="
        nspace = namespace + "="
        source = mwsresponse.replace(nspace, replace)
        tree = ET.fromstring(source)
        return tree
    except Exception:
        return None


def element_auto_text( element, tag, text=None):
    ele = element.find(tag)
    if ele is None:
        return text
    # print tag + " : " + ele.text
    return ele.text


def element_auto_list(element, tag):
    lt = element.findall(tag)
    if lt is None:
        return []
    return lt


def mws_datestr_to_datetime(datestr):
    if datestr is None:
        return None
    utc = datetime.strptime(datestr, '%Y-%m-%dT%H:%M:%SZ')
    return utc


def mws_boolean(bl):
    if bl is None:
        return False
    if bl == 'true':
        return True
    return False

def is_error_response(tree):
    if tree.tag == 'ErrorResponse':
        return True
    return False
