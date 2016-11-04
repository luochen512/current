# -*- coding: utf-8 -*-
import db_sales

def shop(seller_id):
    sql = "SELECT shop_id, seller_id FROM `t_amazon_shop` where seller_id = '%s'" % seller_id
    return db_sales.item_dict(sql)

def insert_shop(seller_id, name, brandname, email):
    sql = "insert into t_amazon_shop (name, brand_name, seller_id, email) " \
          "value ('%s', '%s', '%s', '%s')" % (name, brandname, seller_id, email)
    return db_sales.insert_or_update(sql)

def marketplace(seller_id, marketplaceid):
    sql = "select marketplace_id, amazon_shop_id, seller_id, amazon_marketplaceid from t_amazon_marketplace " \
          "where seller_id='%s' and amazon_marketplaceid='%s' " % (seller_id, marketplaceid)
    return db_sales.item_dict(sql)

def insert_marketplace(seller_id, marketplaceid, marketplace):
    sql = "insert into t_amazon_marketplace (marketplace, seller_id, amazon_marketplaceid) " \
           "values ('%s', '%s', '%s')" % (marketplace, seller_id, marketplaceid)
    return db_sales.insert_or_update(sql)

def update_marketplace_shopid():
    sql = "update t_amazon_shop s, t_amazon_marketplace m set m.amazon_shop_id=s.shop_id where " \
          " s.seller_id=m.seller_id"
    return db_sales.insert_or_update(sql)


def marketplace_shop():
    sql = "select m.marketplace_id, m.amazon_marketplaceid, s.seller_id, s.shop_id from t_amazon_marketplace m " \
          "inner join t_amazon_shop s on m.amazon_shop_id=s.shop_id"
    return db_sales.items_dict(sql)