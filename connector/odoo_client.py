import time
import xmlrpc.client
import asyncio
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple
import concurrent.futures
from config import ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, MAX_RETRIES, RETRY_DELAY, logger
import threading

# Thread-local storage for XML-RPC connections
local = threading.local()

# Thread pool for async operations
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)

def connect_to_odoo():
    """Connect to Odoo instance with retry logic"""
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')

    for attempt in range(MAX_RETRIES):
        try:
            uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
            if uid:
                logger.info(f"Odoo authentication successful - user ID {uid}")
                models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
                return uid, models
            else:
                logger.error("Odoo authentication failed - invalid credentials")
        except Exception as e:
            logger.error(f"Odoo connection error (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)

    logger.critical("All connection attempts to Odoo failed - service unavailable")
    return None, None

def get_odoo_connection():
    """Get thread-local Odoo connection to prevent concurrency issues"""
    if not hasattr(local, 'odoo_uid') or not hasattr(local, 'odoo_models') or not local.odoo_uid:
        local.odoo_uid, local.odoo_models = connect_to_odoo()

    return local.odoo_uid, local.odoo_models

def execute_kw(model: str, method: str, args: List, kwargs: Optional[Dict] = None) -> Any:
    """Execute Odoo RPC call with error handling"""
    if kwargs is None:
        kwargs = {}

    # Auto-add groupby parameter for read_group calls
    if method == 'read_group' and 'groupby' not in kwargs:
        kwargs = kwargs.copy()  # Create a copy to avoid modifying the original
        kwargs['groupby'] = []  # Empty list if no grouping needed
        logger.info(f"Auto-adding missing 'groupby' parameter to {model}.{method} call")

    uid, models = get_odoo_connection()
    if not uid or not models:
        return None

    try:
        # Add timeout for the XML-RPC call
        result = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, method, args, kwargs)
        return result
    except xmlrpc.client.ProtocolError as e:
        logger.error(f"Protocol error executing {model}.{method}: {str(e)}")
        # Clear the thread-local connection so it will be recreated
        if hasattr(local, 'odoo_uid'):
            delattr(local, 'odoo_uid')
        if hasattr(local, 'odoo_models'):
            delattr(local, 'odoo_models')
        return None
    except Exception as e:
        logger.error(f"Error executing {model}.{method}: {str(e)}")
        return None

async def execute_kw_async(model: str, method: str, args: List, kwargs: Optional[Dict] = None) -> Any:
    """Asynchronous version of execute_kw using thread pool with better error handling"""
    if kwargs is None:
        kwargs = {}

    # Auto-add groupby parameter for read_group calls
    if method == 'read_group' and 'groupby' not in kwargs:
        kwargs = kwargs.copy()  # Create a copy to avoid modifying the original
        kwargs['groupby'] = []
        logger.info(f"Auto-adding missing 'groupby' parameter to {model}.{method} call")

    try:
        loop = asyncio.get_running_loop()
        # Pass a new function instead of lambda to avoid capturing variables
        result = await loop.run_in_executor(
            thread_pool,
            execute_kw,
            model, method, args, kwargs
        )

        # Add special handling for count methods which should never be None
        if method == 'search_count' and result is None:
            logger.warning(f"Got None for {model}.{method}, returning 0 instead")
            return 0

        return result
    except Exception as e:
        logger.error(f"Error in async execution of {model}.{method}: {str(e)}")
        # Return appropriate defaults based on method
        if method == 'search_count':
            return 0
        elif method == 'read_group':
            return [{'expected_revenue': 0.0}]
        elif method == 'search_read':
            return []
        else:
            return None

@lru_cache(maxsize=100)
def get_field_info(model: str) -> Dict[str, Dict]:
    """Get field information for a model with caching"""
    return execute_kw(model, 'fields_get', [], {'attributes': ['string', 'type', 'required', 'relation']})

async def batch_execute(calls: List[Tuple[str, str, List, Dict]]) -> List:
    """Execute multiple Odoo calls in parallel with better error handling and rate limiting"""
    # Split into smaller batches to avoid overwhelming the server
    batch_size = 5  # Process 5 calls at a time
    all_results = []

    for i in range(0, len(calls), batch_size):
        batch_calls = calls[i:i + batch_size]
        tasks = []

        for model, method, args, kwargs in batch_calls:
            # Create a new task for each call - the groupby parameter will be added in execute_kw_async
            if method == 'read_group' and 'groupby' not in kwargs:
                # Make a copy of kwargs to avoid modifying the original
                modified_kwargs = kwargs.copy()
                modified_kwargs['groupby'] = []
                tasks.append(execute_kw_async(model, method, args, modified_kwargs))
            else:
                tasks.append(execute_kw_async(model, method, args, kwargs))

        try:
            # Use gather with return_exceptions=True to prevent one failed task from failing all
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results, replacing exceptions with appropriate defaults
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error in batch execution: {str(result)}")
                    model, method, _, _ = batch_calls[j]
                    # Return appropriate defaults based on method
                    if method == 'search_count':
                        all_results.append(0)
                    elif method == 'read_group':
                        all_results.append([{'expected_revenue': 0.0}])
                    elif method == 'search_read':
                        all_results.append([])
                    else:
                        all_results.append(None)
                else:
                    all_results.append(result)

            # Add a small delay between batches to avoid overwhelming the server
            if i + batch_size < len(calls):
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Failed to execute batch operations: {str(e)}")
            # Add appropriate number of None values for this batch
            all_results.extend([None] * len(batch_calls))

    return all_results