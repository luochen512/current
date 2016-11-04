# -*- coding: utf-8 -*-
from utils import db_utils

database = u'sale'


def item_dict(sql):
    return db_utils.item_dict(database, sql)


def item(sql):
    return db_utils.item(database, sql)


def items_dict(sql):
    return db_utils.items_dict(database, sql)


def items(sql):
    return db_utils.items(database, sql)


def insert_or_update(sql):
    return db_utils.insert_or_update(database, sql)