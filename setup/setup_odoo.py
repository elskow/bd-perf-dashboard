import xmlrpc.client
import time
import sys
import logging
import argparse
import base64


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def wait_for_odoo(url, max_retries=20):
    """Wait for Odoo to be available"""
    logger.info(f"Waiting for Odoo to be available at {url}")
    for i in range(max_retries):
        try:
            common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
            common.version()
            logger.info("Odoo server is up and running!")
            return True
        except Exception as e:
            logger.info(f"Attempt {i+1}/{max_retries}: Odoo not ready yet. Waiting 5 seconds...")
            time.sleep(5)

    logger.error(f"Odoo did not become available after {max_retries} attempts")
    return False

def create_database(url, master_password, db_name, admin_password):
    """Create a new Odoo database using XML-RPC"""
    logger.info(f"Creating database '{db_name}'")

    try:
        # Get server version
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        version = common.version()
        logger.info(f"Connected to Odoo {version.get('server_version', 'unknown')}")

        # List existing databases
        db = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/db')
        existing_dbs = db.list(master_password)

        if db_name in existing_dbs:
            logger.info(f"Database '{db_name}' already exists")
            return True

        # Create the database
        result = db.create_database(
            master_password,      # Master password
            db_name,              # Database name
            False,                # Demo data (False = no demo data)
            "en_US",              # Language
            admin_password        # Admin password
        )

        if result:
            logger.info(f"Database '{db_name}' created successfully")
            return True
        else:
            logger.error("Database creation failed")
            return False

    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False

def install_modules(url, db_name, admin_password, modules):
    """Install modules in the database"""
    try:
        # Authenticate
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db_name, 'admin', admin_password, {})

        if not uid:
            logger.error("Authentication failed")
            return False

        logger.info(f"Authenticated with user ID: {uid}")

        # Get module objects
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

        # Install each module
        module_list = modules.split(',')
        for module in module_list:
            module = module.strip()
            logger.info(f"Installing module: {module}")

            # Check if module exists
            module_ids = models.execute_kw(
                db_name, uid, admin_password,
                'ir.module.module', 'search',
                [[['name', '=', module]]]
            )

            if not module_ids:
                logger.error(f"Module '{module}' not found")
                continue

            # Install the module
            models.execute_kw(
                db_name, uid, admin_password,
                'ir.module.module', 'button_immediate_install',
                [module_ids]
            )

            logger.info(f"Module '{module}' installed successfully")

        return True, uid, models

    except Exception as e:
        logger.error(f"Error installing modules: {e}")
        return False, None, None

def configure_crm_stages(url, db_name, admin_password, uid, models):
    """Configure custom CRM stages"""
    logger.info("Setting up custom CRM stages...")

    try:
        # Define the custom stages
        stages = [
            {"name": "CRM NEW LEADS", "sequence": 1},
            {"name": "COLD - NOT POTENTIAL", "sequence": 2},
            {"name": "POTENTIAL", "sequence": 3},
            {"name": "PUSH TO WARM", "sequence": 4},
            {"name": "WARM", "sequence": 5},
            {"name": "FOCUS LEADS", "sequence": 6},
            {"name": "SEND CONTRACT", "sequence": 7},
            {"name": "WON", "sequence": 8, "is_won": True},
            {"name": "LOST", "sequence": 9, "fold": True}
        ]

        # Get existing stages (to avoid duplicates)
        existing_stages = models.execute_kw(db_name, uid, admin_password,
                                           'crm.stage', 'search_read',
                                           [[]], {'fields': ['name']})
        existing_stage_names = [stage['name'] for stage in existing_stages]

        # Delete existing default CRM stages
        if existing_stages:
            existing_stage_ids = [stage['id'] for stage in existing_stages]
            models.execute_kw(db_name, uid, admin_password,
                             'crm.stage', 'unlink',
                             [existing_stage_ids])
            logger.info(f"Removed {len(existing_stage_ids)} default CRM stages")

        # Create the new custom stages
        for stage in stages:
            stage_id = models.execute_kw(db_name, uid, admin_password,
                                        'crm.stage', 'create',
                                        [stage])
            logger.info(f"Created CRM stage: {stage['name']}")

        return True

    except Exception as e:
        logger.error(f"Error configuring CRM stages: {e}")
        return False

def configure_company_info(db_name, admin_password, uid, models):
    """Configure company information"""
    logger.info("Setting up company information...")

    try:
        # Read the company logo
        logo_path = "/setup/assets/icon.png"
        with open(logo_path, 'rb') as f:
            company_logo = f.read()

        # Company data
        company_data = {
            'name': 'HashMicro',
            'email': 'info@hashmicro.com',
            'website': 'https://www.hashmicro.com',
            'phone': '+62 21 5091 7887',
            'street': 'Jl. Casablanca Raya Kav. 88',
            'street2': 'Menara Mulia Lt.16 Unit B',
            'city': 'Jakarta Selatan',
            'zip': '12870',
            'country_id': 99,  # ID for Indonesia, may need to be adjusted
            'logo': base64.b64encode(company_logo).decode('utf-8'),  # Set company logo
        }

        # Update the main company (ID 1)
        models.execute_kw(
            db_name, uid, admin_password,
            'res.company', 'write',
            [[1], company_data]
        )

        # Update web.base.url parameter
        config_parameter_obj = 'ir.config_parameter'
        models.execute_kw(
            db_name, uid, admin_password,
            config_parameter_obj, 'set_param',
            ['web.base.url', f'http://localhost:8069']
        )

        logger.info("Company information updated successfully")
        return True

    except Exception as e:
        logger.error(f"Error setting up company information: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Set up Odoo database and modules')
    parser.add_argument('--url', default='http://localhost:8069', help='Odoo URL')
    parser.add_argument('--db', default='crm_project', help='Database name to create')
    parser.add_argument('--master-password', default='admin', help='Master password')
    parser.add_argument('--admin-password', default='admin', help='Admin user password')
    parser.add_argument('--modules', default='crm,code_backend_theme', help='Comma-separated list of modules to install')
    args = parser.parse_args()

    # Wait for Odoo to be available
    if not wait_for_odoo(args.url):
        sys.exit(1)

    # Create the database
    if not create_database(args.url, args.master_password, args.db, args.admin_password):
        sys.exit(1)

    # Wait a bit for database initialization
    logger.info("Waiting for database initialization...")
    time.sleep(5)

    # Install modules
    result, uid, models = install_modules(args.url, args.db, args.admin_password, args.modules)
    if not result:
        sys.exit(1)

    # Configure company information
    if not configure_company_info(args.db, args.admin_password, uid, models):
        logger.warning("Failed to configure company information")

    # Configure custom CRM stages (only if CRM module was installed)
    if 'crm' in args.modules.split(','):
        logger.info("CRM module detected, configuring custom stages...")
        if not configure_crm_stages(args.url, args.db, args.admin_password, uid, models):
            logger.warning("Failed to configure custom CRM stages")

    logger.info("Odoo setup completed successfully!")

if __name__ == "__main__":
    main()
