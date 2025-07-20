import uvicorn
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
import config
from cache import cache

from routes.health import *
from routes.salesteams import *
from routes.dashboard import *

def cleanup():
    cache.clear()
    config.logger.info("Cache cleared on shutdown")

if __name__ == "__main__":
    import atexit
    atexit.register(cleanup)

    config.logger.info(f"Starting Odoo-PowerBI connector on port 7001")

    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = config.log_format
    log_config["formatters"]["default"]["fmt"] = config.log_format

    workers = min(os.cpu_count() or 1, 4)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=7001,
        reload=False,
        workers=workers,  # Multiple worker processes for better performance
        log_level=config.log_level.lower(),
        log_config=log_config
    )
