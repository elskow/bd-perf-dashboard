import os
import logging
from logging import StreamHandler
import sys

# Configure consistent logging format
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[StreamHandler(sys.stdout)]
)

# Create logger for this application
logger = logging.getLogger("odoo-connector")

# Set log level from environment (default: INFO)
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger.setLevel(getattr(logging, log_level, logging.INFO))

# Constants
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds

# Environment variables for configuration
ODOO_URL = os.environ.get('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.environ.get('ODOO_DB', 'crm_project')
ODOO_USERNAME = os.environ.get('ODOO_USERNAME', 'admin')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', 'admin')
API_KEY = os.environ.get('API_KEY', 'your-secure-api-key')