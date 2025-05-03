import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds

# Environment variables for configuration
ODOO_URL = os.environ.get('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.environ.get('ODOO_DB', 'crm_project')
ODOO_USERNAME = os.environ.get('ODOO_USERNAME', 'admin')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', 'admin')
API_KEY = os.environ.get('API_KEY', 'your-secure-api-key')