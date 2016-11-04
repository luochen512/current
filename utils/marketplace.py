# -*- coding: utf-8 -*-


def rooturl(marketplaceid):
    marketplaces = {
        'A2EUQ1WTGCTBG2': 'https://www.amazon.ca/',
        'ATVPDKIKX0DER': 'https://www.amazon.com/',
        'A1AM78C64UM0Y8': 'https://www.amazon.com.mx/',
        'A1PA6795UKMFR9': 'https://www.amazon.de/',
        'A1RKKUPIHCS9HS': 'https://www.amazon.es/',
        'A13V1IB3VIYZZH': 'https://www.amazon.fr/',
        'A21TJRUUN4KGV': 'https://www.amazon.in/',
        'APJ6JRA9NG5V4': 'https://www.amazon.it/',
        'A1F83G8C2ARO7P': 'https://www.amazon.co.uk/'
    }
    return marketplaces.get(marketplaceid, None)