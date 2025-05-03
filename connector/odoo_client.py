import time
import xmlrpc.client
from config import ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, MAX_RETRIES, RETRY_DELAY, logger

# Global connection objects
odoo_uid = None
odoo_models = None

def connect_to_odoo():
    """Connect to Odoo instance with retry logic"""
    global odoo_uid, odoo_models

    if odoo_uid and odoo_models:
        return odoo_uid, odoo_models

    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')

    for attempt in range(MAX_RETRIES):
        try:
            uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
            if uid:
                logger.info(f"Successfully authenticated with Odoo using user ID {uid}")
                models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
                odoo_uid, odoo_models = uid, models
                return uid, models
            else:
                logger.error("Authentication with Odoo failed")
        except Exception as e:
            logger.error(f"Connection error (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    logger.critical("All connection attempts to Odoo failed")
    return None, None

def execute_kw(model, method, args, kwargs=None):
    """Execute Odoo RPC call with error handling"""
    if kwargs is None:
        kwargs = {}

    uid, models = connect_to_odoo()
    if not uid or not models:
        return None

    try:
        result = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, method, args, kwargs)
        return result
    except Exception as e:
        logger.error(f"Error executing {model}.{method}: {str(e)}")
        return None