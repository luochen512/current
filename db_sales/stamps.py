# -*- coding: utf-8 -*-
import db_sales
import logging
import MySQLdb
logger = logging.getLogger("mws_info")

def last_update_date():
    """
    :return:
    """
    sql = 'SELECT MAX(last_update_date) as last_update_date FROM t_stamps_amazon '
    return db_sales.item_dict(sql)


def stamp_order(amazon_id, sellerid):
    sql = "select amazon_id, amazon_order_id, marketplace_id,last_update_date, order_status from t_stamps_amazon " \
          "where amazon_order_id='%s' and seller_id='%s'" % (amazon_id, sellerid)
    return db_sales.item_dict(sql)


def insert_order(order):
    phone = "" if order.phone is None else order.phone
    is_virtual = 1 if phone is not None and (phone.endswith('6583') or phone.endswith('8365')) else 0
    purchase_date = "" if order.purchase_date is None \
        else order.purchase_date.strftime('%Y-%m-%d %H:%M:%S')
    last_update_date = "" if order.last_update_date is None else order.last_update_date.strftime('%Y-%m-%d %H:%M:%S')
    logger.info('insert_order: ' + str(is_virtual))
    shipment_service = "" if order.shipment_service_level_category is None else order.shipment_service_level_category
    recipient_name = "" if order.recipient_name is None else order.recipient_name
    address_line1 = "" if order.address_line1 is None else order.address_line1
    address_line2 = "" if order.address_line2 is None else order.address_line2
    address_line3 = "" if order.address_line3 is None else order.address_line3
    city = "" if order.city is None else order.city
    county = "" if order.county is None else order.county
    district = "" if order.district is None else order.district
    state_or_region = "" if order.state_or_region is None else order.state_or_region
    postal_code = "" if order.postal_code is None else order.postal_code
    country_code = "" if order.country_code is None else order.country_code
    sql = "insert into t_stamps_amazon (amazon_order_id, seller_id, amazon_marketplaceid, purchase_date, " \
          "last_update_date, order_status, " \
          "shipment_service_level, `name`, address_line1, address_line2, address_line3, city, county, district, " \
          "state_or_region, postal_code, country_code,phone, is_virtual) VALUE ('%s', '%s', '%s', '%s', '%s', '%s'," \
          "'%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s'," \
          "'%s', '%s','%s', '%s', %d)" % (
          order.amazon_order_id, order.sellerid, order.marketplaceid, purchase_date, last_update_date, order.order_status,
         shipment_service,  MySQLdb.escape_string(recipient_name),
           MySQLdb.escape_string(address_line1),  MySQLdb.escape_string(address_line2),  MySQLdb.escape_string(address_line3), MySQLdb.escape_string(city),
         MySQLdb.escape_string(county),  MySQLdb.escape_string(district),  MySQLdb.escape_string(state_or_region),
        postal_code, country_code, phone, is_virtual)
    return db_sales.insert_or_update(sql)

def update_order_marketplaceid():
    sql = 'update t_stamps_amazon s, t_amazon_marketplace m set s.marketplace_id = m.marketplace_id ' \
          ' where s.marketplace_id = 0 and s.seller_id = m.seller_id and s.amazon_marketplaceid = m.amazon_marketplaceid '
    return db_sales.insert_or_update(sql)


def update_order(stampsid, order):
    last_update_date = "" if order.last_update_date is None \
        else order.last_update_date.strftime('%Y-%m-%d %H:%M:%S')
    sql = "UPDATE t_stamps_amazon set last_update_date = '%s', order_status = '%s' " \
          "WHERE amazon_id=%ld" % (last_update_date, order.order_status, stampsid)
    return db_sales.insert_or_update(sql)


def order_item(order, orderitem):
    sql = "select amazon_order_id from t_stamps_amazon_item " \
          " where amazon_order_id='%s' and seller_id='%s' and amazon_marketplaceid='%s'" \
          "  and seller_sku='%s' " % (order.amazon_order_id, order.sellerid, order.marketplaceid, orderitem.seller_sku)
    return db_sales.item_dict(sql)

def insert_order_item(order, orderitem, quantity=0):
    sql = "insert into t_stamps_amazon_item (amazon_order_id, seller_id, amazon_marketplaceid, seller_sku, quantity_ordered) " \
          "VALUE ('%s', '%s', '%s', '%s', %ld)" % (order.amazon_order_id, order.sellerid, order.marketplaceid,
                                                   orderitem.seller_sku, quantity)
    return db_sales.insert_or_update(sql)

def update_order_item_stampsid():
    sql = 'update t_stamps_amazon_item t, t_stamps_amazon s set t.stamps_amazon_id=s.amazon_id ' \
          'where t.stamps_amazon_id=0 and t.amazon_order_id=s.amazon_order_id and t.seller_id=s.seller_id'
    return db_sales.insert_or_update(sql)

def update_order_item_shop_productid():
    sql = 'update t_stamps_amazon_item t, t_amazon_shop_product p set t.shop_product_id=p.shop_product_id where ' \
          ' t.shop_product_id = 0 and t.seller_id=p.seller_id and t.amazon_marketplaceid=p.amazon_marketplaceid' \
          ' and t.seller_sku=p.seller_sku'
    return db_sales.insert_or_update(sql)

def update_order_status():
    sql = "update amazon_sale.t_stamps_amazon s, mws_sundix.t_order_order o set s.order_status=o.order_status WHERE " \
          " s.order_status = 'Unshipped' and o.fulfillment_channel='MFN' and o.order_status != 'Unshipped' " \
          "and o.sellerid=s.seller_id and s.amazon_order_id=o.amazon_order_id and o.marketplaceid = s.amazon_marketplaceid"
    return db_sales.insert_or_update(sql)