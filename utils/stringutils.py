# -*- coding: utf-8 -*-

def isEmpty(str):
    """
    check the String is Empty
    :param str:
    :return:
    """
    if str is None or str.strip()=='':
        return True
    return False