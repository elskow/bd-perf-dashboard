import uvicorn
from app import app
import config
from cache import cache
import os
import sys
import logging

# Force-import all routes to ensure they're registered with FastAPI
from routes.health import *
from routes.salesteams import *
from routes.dashboard import *

# Add cache cleaning on exit
def cleanup():
    cache.clear()
    config.logger.info("Cache cleared on shutdown")

if __name__ == "__main__":
    # Register cleanup handler
    import atexit
    atexit.register(cleanup)

    # Run the app
    config.logger.info(f"Starting Odoo-PowerBI connector on port 7001")

    # Configure uvicorn logging to match our format
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = config.log_format
    log_config["formatters"]["default"]["fmt"] = config.log_format

    # Determine number of workers
    # Use the number of CPU cores, but capped at 4 (which is plenty for most use cases)
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
