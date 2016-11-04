# -*- coding: utf-8 -*-
import db_sales


def get_shop_product(seller_id, marketplaceid, seller_sku):
    sql = "select shop_product_id, seller_id, amazon_marketplaceid,  seller_sku from t_amazon_shop_product " \
          " where seller_id='%s' and amazon_marketplaceid='%s' and seller_sku='%s' " % (seller_id,
                                                                                        marketplaceid,
                                                                                        seller_sku)
    return db_sales.item_dict(sql)

def insert_shop_product(seller_id, marketplaceid, seller_sku, asin):
    sql = "insert into t_amazon_shop_product (seller_id, amazon_marketplaceid,  seller_sku, asin) " \
          " value ('%s', '%s', '%s', '%s')" % (seller_id, marketplaceid, seller_sku, asin)
    return db_sales.insert_or_update(sql)

def update_shop_product_marketplaceid():
    sql = "update t_amazon_shop_product p, t_amazon_marketplace m set p.marketplace_id = m.marketplace_id " \
          " where p.marketplace_id = 0 and p.seller_id = m.seller_id and p.amazon_marketplaceid=m.amazon_marketplaceid"
    return db_sales.insert_or_update(sql)

def get_products():
    """
    :param marketplaceid:
    :param seller_sku:
    :return:
    """
    sql = "select p.shop_product_id, p.marketplace_id, p.seller_sku, m.amazon_marketplaceid from t_amazon_shop_product p" \
           " inner join t_amazon_marketplace m on p.marketplace_id = m.marketplace_id"
    return db_sales.items_dict(sql)