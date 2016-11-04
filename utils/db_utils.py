# -*- coding: utf-8 -*-
from django.db import connections
import logging

logger = logging.getLogger("mws_log")


def item_dict(dbname, sql):
    cursor = connections[dbname].cursor()
    cursor.execute(sql)   
    one=cursor.fetchone()
    if one == None or len(one)==0:
        return {}
    col_names = [desc[0] for desc in cursor.description]
    cursor.close()
    # logger.info("one: " + str(one))
    return dict(zip(col_names,one))

def item(dbname, sql):
    cursor=connections[dbname].cursor()
    cursor.execute(sql)
    i = cursor.fetchone()
    cursor.close()
    return i

def items_dict(dbname, sql):
    cursor = connections[dbname].cursor()
    cursor.execute(sql)
    #"将游标返回的结果保存到一个字典对象中"
    col_names = [desc[0] for desc in cursor.description]
    # logger.info("name : " + str(col_names))
    items=[]
    for item in cursor.fetchall():
        # logger.info("item: " + str(item))
        items.append(dict(zip(col_names,item)))
    cursor.close()
    return items

def items(dbname, sql):
    cursor = connections[dbname].cursor()
    cursor.execute(sql)
    its = cursor.fetchall()
    cursor.close()
    return its

def insert_or_update(dbname, sql):
    cursor=connections[dbname].cursor()
    cursor.execute(sql)
    connections[dbname].connection.commit()
    cursor.close()