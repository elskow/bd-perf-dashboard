#!/usr/bin/env python3

import argparse
import csv
import logging
import os
import random
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta, time as dt_time
from typing import Any, Dict, List, Optional, Tuple, Union

# Third-party imports
import xmlrpc.client
from babel.numbers import format_currency
from faker import Faker
import locale

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_LOCALE = 'id_ID.UTF-8'
FALLBACK_LOCALE = 'id_ID'
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds

# Try to set Indonesian locale
try:
    locale.setlocale(locale.LC_ALL, DEFAULT_LOCALE)
except:
    try:
        locale.setlocale(locale.LC_ALL, FALLBACK_LOCALE)
    except:
        logger.warning("Could not set Indonesian locale, using default")


class OdooUtils:
    """Utility class for Odoo connection and common operations"""

    @staticmethod
    def format_idr(amount: float) -> str:
        """Format amount as IDR currency"""
        try:
            return format_currency(amount, 'IDR', locale='id_ID')
        except:
            return f"Rp {amount:,.0f},-"

    @staticmethod
    def connect_to_odoo(url: str, db: str, username: str, password: str, max_retries: int = MAX_RETRIES) -> Tuple[Optional[int], Optional[xmlrpc.client.ServerProxy]]:
        """Establish connection to Odoo instance with retries"""
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')

        for attempt in range(max_retries):
            try:
                uid = common.authenticate(db, username, password, {})
                if uid:
                    logger.info(f"Successfully authenticated with user ID: {uid}")
                    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
                    return uid, models
                else:
                    logger.error("Authentication failed")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {RETRY_DELAY} seconds... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(RETRY_DELAY)
            except Exception as e:
                logger.error(f"Connection error: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {RETRY_DELAY} seconds... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(RETRY_DELAY)

        return None, None

    @staticmethod
    @contextmanager
    def odoo_context(tracking_disabled: bool = True):
        """Context manager to provide standard context for Odoo operations"""
        context = {
            'mail_auto_subscribe_no_notify': tracking_disabled,
            'tracking_disable': tracking_disabled,
            'mail_create_nosubscribe': tracking_disabled,
            'mail_create_nolog': tracking_disabled
        }
        yield context


class CrmDataGenerator:
    """Main class for generating CRM data in Odoo"""

    # Stage mapping constants
    STAGE_WEIGHTS = {
        'NEW': 25,        # 25% new leads
        'COLD': 15,       # 15% cold leads
        'POTENTIAL': 15,  # 15% potential
        'PUSH TO WARM': 10, # 10% push to warm
        'WARM': 10,       # 10% warm
        'FOCUS': 8,       # 8% focus
        'CONTRACT': 7,    # 7% contract
        'WON': 5,         # 5% won
        'LOST': 5,        # 5% lost
    }

    STAGE_TO_REVENUE_FACTOR = {
        'NEW': 0.5,
        'COLD': 0.6,
        'POTENTIAL': 0.7,
        'PUSH TO WARM': 0.75,
        'WARM': 0.8,
        'FOCUS': 0.85,
        'CONTRACT': 0.95,
        'WON': 1.0,
        'LOST': 0.0
    }

    # Lead source constants
    LEAD_SOURCES = {
        'Website': 25,
        'Referral': 15,
        'Event': 10,
        'Cold Call': 10,
        'Email Campaign': 12,
        'Social Media': 8,
        'Partner': 10,
        'Paid Search': 5,
        'Organic Search': 5
    }

    # Tag categories
    TAG_CATEGORIES = {
        'Industry': [
            'Technology', 'Healthcare', 'Finance', 'Manufacturing', 'Retail',
            'Education', 'Hospitality', 'Construction', 'Energy', 'Agriculture',
            'Transportation', 'Media', 'Professional Services', 'Government', 'Non-profit'
        ],
        'Source': [
            'Website', 'Event', 'Referral', 'Cold Call', 'Email Campaign',
            'Social Media', 'Webinar', 'Content Download', 'Partner', 'Paid Search',
            'Organic Search', 'Trade Show', 'Direct Mail'
        ],
        'Product Interest': [
            'Core Product', 'Enterprise Package', 'Basic Plan', 'Premium Plan',
            'Add-on Services', 'Integration Services', 'Training', 'Consulting',
            'Maintenance Contract', 'Custom Development'
        ]
    }

    # Sales roles
    SALES_ROLES = {
        'Indonesia': [
            ("Budi Santoso", "id.sales.director@example.com", "Sales Director Indonesia"),
            ("Ahmad Wijaya", "id.enterprise.manager@example.com", "Enterprise Manager Indonesia"),
            ("Dewi Lestari", "id.sam.enterprise@example.com", "Enterprise Sales Indonesia"),
            ("Bambang Suparno", "id.enterprise.sales@example.com", "Enterprise Sales Indonesia"),
            ("Siti Rahma", "id.smb.manager@example.com", "SMB Manager Indonesia"),
            ("Agus Setiawan", "id.smb.sales1@example.com", "SMB Sales Indonesia"),
            ("Ratna Sari", "id.smb.sales2@example.com", "SMB Sales Indonesia"),
        ],
        'Singapore': [
            ("Michael Tan", "sg.sales.director@example.com", "Sales Director Singapore"),
            ("Sarah Wong", "sg.enterprise.manager@example.com", "Enterprise Manager Singapore"),
            ("David Lim", "sg.sam.enterprise@example.com", "Enterprise Sales Singapore"),
            ("Jennifer Chen", "sg.enterprise.sales@example.com", "Enterprise Sales Singapore"),
            ("Kenneth Ng", "sg.smb.manager@example.com", "SMB Manager Singapore"),
            ("Grace Lee", "sg.smb.sales1@example.com", "SMB Sales Singapore"),
            ("Marcus Goh", "sg.smb.sales2@example.com", "SMB Sales Singapore"),
        ]
    }

    def __init__(self, uid: int, models: xmlrpc.client.ServerProxy, db: str, password: str):
        self.uid = uid
        self.models = models
        self.db = db
        self.password = password
        self.fake = Faker()
        self.now = datetime.now()

        # Initialize key data structures
        self.tag_ids = {}
        self.users = {}
        self.stages = []
        self.stage_ids = []
        self.stage_names = {}
        self.activity_types = []
        self.companies = []

    def execute_kw(self, model: str, method: str, args: List, kwargs: Dict = None) -> Any:
        """Execute Odoo RPC call with error handling"""
        if kwargs is None:
            kwargs = {}

        try:
            return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs)
        except Exception as e:
            logger.error(f"Error executing {model}.{method}: {e}")
            raise

    def setup_crm_tags(self) -> Dict[str, List[int]]:
        """Set up realistic CRM tags for lead categorization"""
        try:
            logger.info("Setting up CRM tags...")

            tag_ids = defaultdict(list)

            for category, tags in self.TAG_CATEGORIES.items():
                for tag in tags:
                    tag_name = f"{category}: {tag}"

                    # Check if tag already exists
                    existing_tag = self.execute_kw('crm.tag', 'search_read',
                                               [[['name', '=', tag_name]]], {'fields': ['id']})

                    if existing_tag:
                        tag_ids[category].append(existing_tag[0]['id'])
                    else:
                        tag_id = self.execute_kw('crm.tag', 'create', [{'name': tag_name}])
                        tag_ids[category].append(tag_id)

            logger.info(f"Created {sum(len(tags) for tags in tag_ids.values())} tags across {len(tag_ids)} categories")

            self.tag_ids = tag_ids
            return tag_ids

        except Exception as e:
            logger.error(f"Error setting up CRM tags: {e}")
            return {}

    def setup_user_roles(self) -> Dict[int, Dict]:
        """Set up user roles with team assignments"""
        try:
            logger.info("Setting up user roles...")

            # Set up teams first
            sales_teams = self.execute_kw('crm.team', 'search_read',
                                        [[('name', 'in', ['Sales Indonesia', 'Sales Singapore'])]],
                                        {'fields': ['id', 'name']})
            team_map = {team['name']: team['id'] for team in sales_teams}

            # Get the required groups
            groups = self.execute_kw('res.groups', 'search_read',
                                [[('name', 'in', [
                                    'User: Own Documents Only',
                                    'Sales: User',
                                    'Contact Creation',
                                    'Internal User'
                                ])]],
                                {'fields': ['id', 'name']})
            group_ids = [group['id'] for group in groups]

            # Create or update users for each team
            for team_name, team_members in self.SALES_ROLES.items():
                team_id = team_map.get(f'Sales {team_name}')
                if not team_id:
                    logger.error(f"Could not find team ID for Sales {team_name}")
                    continue

                for name, login, title in team_members:
                    # Check if user exists
                    existing_user = self.execute_kw('res.users', 'search_read',
                                                [[('login', '=', login)]],
                                                {'fields': ['id']})

                    user_vals = {
                        'name': name,
                        'login': login,
                        'password': 'demo123',
                        'company_id': 1,
                        'email': login,
                        'sale_team_id': team_id,
                        'groups_id': [(6, 0, group_ids)],  # Assign all required groups
                        'share': False,  # Internal user
                        'notification_type': 'email',
                    }

                    try:
                        if existing_user:
                            # Update existing user
                            user_id = existing_user[0]['id']
                            self.execute_kw('res.users', 'write', [[user_id], user_vals])
                            logger.info(f"Updated user '{name}' with team {team_name}")
                        else:
                            # Create new user
                            user_id = self.execute_kw('res.users', 'create', [user_vals])
                            logger.info(f"Created user '{name}' with team {team_name}")

                        # Get the partner id for this user
                        user_data = self.execute_kw('res.users', 'read',
                                                [user_id],
                                                {'fields': ['partner_id']})
                        user_partner_id = user_data[0]['partner_id'][0] if user_data and user_data[0]['partner_id'] else False

                        if user_partner_id:
                            # Check if user is already in the team
                            existing_member = self.execute_kw('crm.team.member', 'search',
                                                        [[('crm_team_id', '=', team_id),
                                                        ('user_id', '=', user_id)]])

                            if not existing_member:
                                # Add user as team member - this is key for team membership!
                                member_data = {
                                    'crm_team_id': team_id,
                                    'user_id': user_id,
                                    'member_warning': False,
                                    'create_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'write_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                }
                                self.execute_kw('crm.team.member', 'create', [member_data])
                                logger.info(f"Added user {name} as member of Sales {team_name} team")

                    except Exception as e:
                        logger.error(f"Error creating/updating user {name}: {e}")

            # Verify team memberships
            logger.info("\nVerifying team memberships:")
            for team_name, team_id in team_map.items():
                team_members = self.execute_kw('crm.team.member', 'search_read',
                                        [[('crm_team_id', '=', team_id)]],
                                        {'fields': ['user_id']})

                member_ids = [member['user_id'][0] for member in team_members]
                member_names = []
                if member_ids:
                    users_data = self.execute_kw('res.users', 'read',
                                            [member_ids],
                                            {'fields': ['name']})
                    member_names = [user['name'] for user in users_data]

                logger.info(f"Team '{team_name}' has {len(member_ids)} members: {', '.join(member_names) if member_names else 'None'}")

            # Get final user list with team assignments
            users = self.execute_kw('res.users', 'search_read',
                                [[('share', '=', False)]],
                                {'fields': ['id', 'name', 'login', 'sale_team_id']})

            users_dict = {user['id']: user for user in users}
            self.users = users_dict
            return users_dict

        except Exception as e:
            logger.error(f"Error setting up user roles: {e}")
            return {}

    def setup_sales_teams(self) -> Dict[str, int]:
        """Set up sales teams for Indonesia and Singapore"""
        try:
            logger.info("Setting up sales teams...")
            team_ids = {}

            for team_name in ['Indonesia', 'Singapore']:
                full_team_name = f'Sales {team_name}'
                # Check if team already exists
                existing_team = self.execute_kw('crm.team', 'search_read',
                                            [[['name', '=', full_team_name]]],
                                            {'fields': ['id', 'name']})

                if existing_team:
                    team_ids[team_name] = existing_team[0]['id']
                    logger.info(f"Found existing sales team '{full_team_name}' with ID {team_ids[team_name]}")
                else:
                    # Create new team
                    team_vals = {
                        'name': full_team_name,
                        'company_id': 1,
                    }
                    team_ids[team_name] = self.execute_kw('crm.team', 'create', [team_vals])
                    logger.info(f"Created sales team '{full_team_name}' with ID {team_ids[team_name]}")

            return team_ids

        except Exception as e:
            logger.error(f"Error setting up sales teams: {e}")
            return {}

    def load_company_data(self) -> List[Dict]:
        """Load realistic company data or generate it if file not found"""
        companies = []
        try:
            # Try to load from CSV file in the same directory as the script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            csv_path = os.path.join(script_dir, 'sample_companies.csv')

            if os.path.exists(csv_path):
                with open(csv_path, 'r') as f:
                    reader = csv.DictReader(f)
                    companies = list(reader)
                    logger.info(f"Loaded {len(companies)} companies from sample data")
            else:
                # Generate companies with Faker
                industries = self.TAG_CATEGORIES['Industry']
                company_sizes = ['1-10', '11-50', '51-200', '201-500', '501-1000', '1000+']

                # Ensure we have a good mix of Indonesian and Singaporean companies
                countries = ['Indonesia'] * 40 + ['Singapore'] * 40 + [self.fake.country() for _ in range(20)]
                random.shuffle(countries)

                for country in countries:
                    companies.append({
                        'name': self.fake.company(),
                        'industry': random.choice(industries),
                        'size': random.choice(company_sizes),
                        'country': country,
                        'website': 'www.' + self.fake.domain_name()
                    })
                logger.info("Generated 100 fake companies as sample data")
        except Exception as e:
            logger.error(f"Error loading company data: {e}")
            # Create a minimal set as fallback
            industries = self.TAG_CATEGORIES['Industry'][:5]
            company_sizes = ['1-10', '11-50', '51-200', '201-500', '501-1000', '1000+']
            for _ in range(50):
                companies.append({
                    'name': self.fake.company(),
                    'industry': random.choice(industries),
                    'size': random.choice(company_sizes),
                    'country': self.fake.country(),
                    'website': 'www.' + self.fake.domain_name()
                })

        self.companies = companies
        return companies

    def get_crm_stages(self) -> List[Dict]:
        """Get CRM stages from Odoo"""
        stages = self.execute_kw('crm.stage', 'search_read', [[]], {'fields': ['id', 'name', 'sequence']})
        if not stages:
            logger.error("No CRM stages found. Ensure CRM module is properly installed.")
            return []

        # Log the available stages
        stage_names = [stage['name'] for stage in stages]
        logger.info(f"Found {len(stages)} stages: {', '.join(stage_names)}")

        # Sort stages by sequence
        stages.sort(key=lambda x: x['sequence'])
        self.stages = stages
        self.stage_ids = [stage['id'] for stage in stages]
        self.stage_names = {stage['id']: stage['name'] for stage in stages}

        return stages

    def get_activity_types(self) -> List[Dict]:
        """Get activity types from Odoo"""
        activity_types = self.execute_kw('mail.activity.type', 'search_read', [[]], {'fields': ['id', 'name']})
        logger.info(f"Found {len(activity_types)} activity types")
        self.activity_types = activity_types
        return activity_types

    def get_note_subtype_id(self) -> int:
        """Get the note subtype ID for messages"""
        try:
            note_subtype = self.execute_kw('mail.message.subtype', 'search_read',
                                         [[['name', '=', 'Note']]], {'fields': ['id']})
            if note_subtype:
                return note_subtype[0]['id']
            else:
                logger.warning("Note subtype not found, using default subtype ID 1")
                return 1
        except Exception as e:
            logger.warning(f"Error getting note subtype ID: {e}")
            return 1

    def generate_business_datetime(self, start_date: datetime, end_date: datetime) -> datetime:
        """Generate a datetime during business hours (9am-5pm) on weekdays only"""
        # Get a random date
        time_delta = end_date - start_date
        days_delta = time_delta.days + 1

        if days_delta <= 0:
            random_date = start_date
        else:
            random_days = random.randint(0, days_delta)
            random_date = start_date + timedelta(days=random_days)

        # Check if it's a weekend and adjust
        while random_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            random_date += timedelta(days=1)
            if random_date > end_date:
                random_date = end_date
                # If end_date is a weekend, move to previous Friday
                while random_date.weekday() >= 5:
                    random_date -= timedelta(days=1)

        # Set to business hours (using 24-hour format)
        business_start = dt_time(8, 0, 0)  # 8:00 (start earlier for Indonesian business hours)
        business_end = dt_time(17, 0, 0)   # 17:00

        # Random time during business hours
        random_hour = random.randint(business_start.hour, business_end.hour - 1)
        random_minute = random.choice([0, 15, 30, 45])  # Realistic meeting start times

        return random_date.replace(hour=random_hour, minute=random_minute, second=0)

    def _get_user_partner_id(self, user_id: int) -> Optional[int]:
        """Get the partner ID associated with a user"""
        try:
            user_data = self.execute_kw('res.users', 'read', [user_id], {'fields': ['partner_id']})
            if user_data and user_data[0]['partner_id']:
                return user_data[0]['partner_id'][0]
        except Exception as e:
            logger.error(f"Error getting partner ID for user {user_id}: {e}")
        return None

    def create_lead_message(self, lead_id: int, body: str, author_id: int,
                          message_date: datetime, subtype_id: Optional[int] = None) -> Optional[int]:
        """Create a message for a lead with specific historical date"""
        try:
            note_subtype_id = subtype_id or self.get_note_subtype_id()

            # Get the user partner ID
            partner_id = self._get_user_partner_id(author_id)

            message_vals = {
                'body': body,
                'model': 'crm.lead',
                'res_id': lead_id,
                'author_id': partner_id,
                'message_type': 'comment',
                'subtype_id': note_subtype_id,
                'date': message_date.strftime('%Y-%m-%d %H:%M:%S')
            }

            message_id = self.execute_kw('mail.message', 'create', [message_vals])
            return message_id
        except Exception as e:
            logger.error(f"Error creating lead message: {e}")
            return None

    def add_stage_change_log(self, lead_id: int, old_stage_name: str, new_stage_name: str,
                            user_id: int, date: datetime) -> Optional[int]:
        """Add a log note about stage change for analytics with correct historical timestamp"""
        try:
            user_name = self.users.get(user_id, {}).get('name', "Administrator")

            message = f"Stage changed from '{old_stage_name}' to '{new_stage_name}'"
            message_with_tag = f"{message} #stage_change_log#"

            analytics_data = {
                "type": "stage_change",
                "old_stage": old_stage_name,
                "new_stage": new_stage_name,
                "timestamp": date.strftime('%Y-%m-%d %H:%M:%S'),
                "user_id": user_id,
                "user_name": user_name,
            }

            analytics_message = f"{message_with_tag}\n\n<!-- ANALYTICS_DATA: {str(analytics_data)} -->"

            return self.create_lead_message(lead_id, analytics_message, user_id, date)

        except Exception as e:
            logger.error(f"Error adding stage change log: {e}")
            return None

    def create_calendar_event(self, lead_id: int, event_name: str, start_datetime: datetime,
                             duration_hours: float, user_id: int, partner_id: Optional[int] = None) -> Optional[int]:
        """Create a calendar event with proper historical dates"""
        try:
            end_datetime = start_datetime + timedelta(hours=duration_hours)

            # Create event with all tracking disabled
            event_vals = {
                'name': event_name,
                'start': start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'stop': end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'duration': duration_hours,
                'user_id': user_id,
                'opportunity_id': lead_id,
                'location': 'Virtual Meeting' if random.random() < 0.7 else 'Office Meeting Room',
                'description': self.fake.paragraph(nb_sentences=2),
            }

            if partner_id:
                event_vals['partner_ids'] = [(4, partner_id)]

            with OdooUtils.odoo_context() as context:
                # Create the event with context to disable auto-messages
                event_id = self.execute_kw('calendar.event', 'create', [event_vals], {'context': context})

                # Add a message with the historical timestamp
                if start_datetime < self.now:
                    # Get user name for the message
                    user_name = "Administrator"
                    if user_id in self.users:
                        user_name = self.users[user_id].get('name', "Administrator")

                    # Calendar message with meeting details
                    message_body = f"<p>Meeting scheduled at '{start_datetime.strftime('%Y-%m-%d %H:%M:%S')}'<br/>Subject: {event_name}<br/>Duration: {duration_hours} hours</p>"

                    # Create message with historical timestamp
                    self.create_lead_message(
                        lead_id,
                        message_body,
                        user_id,
                        start_datetime - timedelta(days=random.randint(1, 5))  # Schedule a few days before
                    )

                return event_id
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return None

    def add_custom_stage_change_message(self, lead_id: int, old_stage_id: int, new_stage_id: int,
                                       user_id: int, date: datetime) -> Optional[int]:
        """Add a user-friendly stage change message with historical timestamp"""
        try:
            old_stage_name = self.stage_names.get(old_stage_id, "Unknown")
            new_stage_name = self.stage_names.get(new_stage_id, "Unknown")

            # Get user name
            user_name = "Administrator"
            if user_id in self.users:
                user_name = self.users[user_id].get('name', "Administrator")

            # Different message format based on stage transition
            if 'WON' in new_stage_name.upper():
                message_body = f"<p>Opportunity won</p><p>Salesperson: {user_name}</p><p>Stage: {old_stage_name}<br/>{new_stage_name}</p>"
            elif 'LOST' in new_stage_name.upper():
                message_body = f"<p>Opportunity lost</p><p>Salesperson: {user_name}</p><p>Stage: {old_stage_name}<br/>{new_stage_name}</p>"
            else:
                message_body = f"<p>Stage changed</p><p>Salesperson: {user_name}</p><p>Stage: {new_stage_name}<br/>{old_stage_name}</p>"

            # Create message with historical timestamp
            return self.create_lead_message(lead_id, message_body, user_id, date)
        except Exception as e:
            logger.error(f"Error adding custom stage change message: {e}")
            return None

    def get_probability_data(self, date_created: datetime) -> Dict:
        """Calculate probability and other metrics based on lead age"""
        lead_age = (self.now - date_created).days

        # Define stage weights for distribution
        stage_weights = {}
        for stage in self.stages:
            stage_name = stage['name'].upper()
            for key in self.STAGE_WEIGHTS:
                if key in stage_name:
                    stage_weights[stage['id']] = self.STAGE_WEIGHTS[key]
                    break
            else:
                stage_weights[stage['id']] = 10  # Default weight

        # Use weighted random selection for stage
        stage_ids_list = list(stage_weights.keys())
        weights = list(stage_weights.values())
        stage_id = random.choices(stage_ids_list, weights=weights, k=1)[0]
        stage_index = self.stage_ids.index(stage_id)
        stage_name = self.stage_names[stage_id].upper()

        # Override for very new leads
        if lead_age < 3 and random.random() < 0.8:
            # 80% chance of new leads being in the first or second stage
            stage_id = self.stage_ids[random.choices([0, 1], weights=[70, 30], k=1)[0]]
            stage_index = self.stage_ids.index(stage_id)
            stage_name = self.stage_names[stage_id].upper()

        # Find WON and LOST stage IDs
        won_stage_id = None
        lost_stage_id = None
        for sid, sname in self.stage_names.items():
            if 'WON' in sname.upper():
                won_stage_id = sid
            elif 'LOST' in sname.upper():
                lost_stage_id = sid

        # Ensure won/lost leads stay in terminal state
        if 'WON' in stage_name and lost_stage_id and random.random() < 0.99:
            if stage_id == lost_stage_id:
                stage_id = won_stage_id
                stage_index = self.stage_ids.index(stage_id)
                stage_name = self.stage_names[stage_id].upper()

        # Assign probability based on stage
        if 'WON' in stage_name:
            probability = 100
        elif 'LOST' in stage_name:
            probability = 0
        elif 'CONTRACT' in stage_name:
            probability = random.randint(80, 95)
        elif 'FOCUS' in stage_name:
            probability = random.randint(60, 80)
        elif 'WARM' in stage_name:
            probability = random.randint(40, 60)
        elif 'PUSH TO WARM' in stage_name:
            probability = random.randint(30, 50)
        elif 'POTENTIAL' in stage_name:
            probability = random.randint(20, 40)
        elif 'COLD' in stage_name:
            probability = random.randint(1, 20)
        elif 'NEW' in stage_name:
            probability = random.randint(1, 10)
        else:
            probability = random.randint(10, 50)

        IDR_CONVERSION = 1000
        base_revenue = random.randint(5000, 500000) * IDR_CONVERSION

        # Find the best matching stage factor
        best_match = None
        for key in self.STAGE_TO_REVENUE_FACTOR:
            if key in stage_name:
                best_match = key
                break

        revenue_factor = self.STAGE_TO_REVENUE_FACTOR.get(best_match, 0.7)
        expected_revenue = int(base_revenue * revenue_factor / 1000) * 1000

        return {
            'stage_id': stage_id,
            'stage_index': stage_index,
            'probability': probability,
            'expected_revenue': expected_revenue
        }

    def create_realistic_lead_history(self, lead_id: int, lead_data: Dict,
                                     date_created: datetime, current_stage_id: int) -> bool:
        """Create a realistic history of stage changes and messages for a lead"""
        try:
            assigned_user_id = lead_data.get('user_id', self.uid)
            user_name = self.users.get(assigned_user_id, {}).get('name', "Administrator")

            # Add creation message with historical timestamp
            creation_msg = f"<p>Lead/Opportunity created by {user_name}</p>"
            self.create_lead_message(lead_id, creation_msg, assigned_user_id, date_created)

            # Add customer info message (slightly after creation)
            customer_msg = f"<p>Customer information added by {user_name}<br/>{lead_data.get('partner_name', '')}, {lead_data.get('contact_name', '')}</p>"
            self.create_lead_message(
                lead_id,
                customer_msg,
                assigned_user_id,
                date_created + timedelta(minutes=random.randint(1, 5))
            )

            # Determine how many stages this lead has gone through
            current_stage_index = self.stage_ids.index(current_stage_id)

            # Add historical stage changes if not in the first stage
            if current_stage_index > 0:
                self._create_stage_change_history(lead_id, lead_data, date_created, current_stage_index)

            return True

        except Exception as e:
            logger.error(f"Error creating lead history for lead {lead_id}: {e}")
            return False

    def _create_stage_change_history(self, lead_id: int, lead_data: Dict, date_created: datetime,
                                    current_stage_index: int) -> None:
        """Create stage change history for a lead"""
        # Generate timestamps for stage transitions
        stage_dates = []
        current_date = date_created + timedelta(hours=random.randint(2, 8))
        assigned_user_id = lead_data.get('user_id', self.uid)

        # Generate sequential stage transitions with reasonable time gaps
        for i in range(current_stage_index):
            from_stage_id = self.stage_ids[i]
            to_stage_id = self.stage_ids[i+1]
            from_stage_name = self.stage_names[from_stage_id].upper()
            to_stage_name = self.stage_names[to_stage_id].upper()

            # Skip invalid transitions
            if 'WON' in from_stage_name or 'LOST' in from_stage_name:
                continue

            # Add appropriate time between stages based on stage type
            if 'NEW' in from_stage_name:
                days_to_add = random.randint(1, 3)
            elif 'COLD' in from_stage_name:
                days_to_add = random.randint(2, 10)
            elif 'POTENTIAL' in from_stage_name:
                days_to_add = random.randint(2, 8)
            elif 'PUSH TO WARM' in from_stage_name:
                days_to_add = random.randint(1, 7)
            elif 'WARM' in from_stage_name:
                days_to_add = random.randint(3, 10)
            elif 'FOCUS' in from_stage_name:
                days_to_add = random.randint(3, 15)
            elif 'CONTRACT' in from_stage_name:
                if 'WON' in to_stage_name:
                    days_to_add = random.randint(5, 20)
                elif 'LOST' in to_stage_name:
                    days_to_add = random.randint(5, 30)
                else:
                    days_to_add = random.randint(3, 15)
            else:
                days_to_add = random.randint(1, 7)

            # Ensure each date is strictly after the previous one
            current_date = max(current_date + timedelta(days=days_to_add),
                             stage_dates[-1] + timedelta(days=1) if stage_dates else current_date)

            # Don't exceed current date
            if current_date > self.now:
                current_date = self.now - timedelta(hours=random.randint(1, 48))

            # Add the date in strictly ascending order
            stage_dates.append(current_date)

        # Record stage transitions
        for i, stage_date in enumerate(stage_dates):
            from_stage_id = self.stage_ids[i]
            to_stage_id = self.stage_ids[i+1]
            from_stage_name = self.stage_names[from_stage_id].upper()
            to_stage_name = self.stage_names[to_stage_id].upper()

            if 'WON' in from_stage_name or 'LOST' in from_stage_name:
                continue

            # Add manager review for important stages
            if 'FOCUS' in to_stage_name or 'CONTRACT' in to_stage_name:
                manager_users = [uid for uid, user in self.users.items()
                               if 'Manager' in user.get('name', '') or 'Director' in user.get('name', '')]
                if manager_users:
                    manager_id = random.choice(manager_users)
                    manager_message = f"Reviewed the opportunity and approved the stage change to '{to_stage_name}'"
                    self.create_lead_message(
                        lead_id,
                        manager_message,
                        manager_id,
                        stage_date + timedelta(hours=random.randint(1, 4))  # After the stage change
                    )

            # Add stage change logs
            self.add_stage_change_log(
                lead_id,
                self.stage_names[from_stage_id],
                self.stage_names[to_stage_id],
                assigned_user_id,
                stage_date
            )

            self.add_custom_stage_change_message(
                lead_id,
                from_stage_id,
                to_stage_id,
                assigned_user_id,
                stage_date + timedelta(seconds=30)
            )

            # Update the lead with the stage change - except for the final transition
            if i == len(stage_dates) - 1:  # Skip the last one as the lead is already at this stage
                continue

            # Write the stage change with tracking disabled
            with OdooUtils.odoo_context() as context:
                self.execute_kw('crm.lead', 'write', [
                    lead_id,
                    {
                        'stage_id': to_stage_id,
                        'user_id': assigned_user_id,
                    }
                ], {'context': context})

    def create_lead_activities(self, lead_id: int, lead_data: Dict, date_created: datetime,
                              partner_id: Optional[int] = None) -> bool:
        """Create activities and meetings for a lead based on its stage"""
        try:
            stage_id = lead_data.get('stage_id')
            if not stage_id or stage_id not in self.stage_names:
                return False

            stage_name = self.stage_names[stage_id].upper()
            user_id = lead_data.get('user_id', self.uid)

            # Skip activity creation for WON/LOST deals
            if 'WON' in stage_name or 'LOST' in stage_name:
                return True

            # Define activity sequence based on stage
            activity_sequence = self._get_activity_sequence_for_stage(stage_name)

            # For variety, don't create all activities for every lead
            if len(activity_sequence) > 2:
                # Keep at least 2 activities for longer sequences
                number_to_keep = random.randint(2, len(activity_sequence))
                random.shuffle(activity_sequence)
                activity_sequence = activity_sequence[:number_to_keep]
                # Sort them back by days_offset
                activity_sequence.sort(key=lambda x: x['days_offset'])

            # Create the activities with proper timing
            base_date = date_created
            for activity in activity_sequence:
                # Calculate realistic datetime
                activity_date = base_date + timedelta(days=activity['days_offset'])
                business_datetime = self.generate_business_datetime(
                    activity_date,
                    activity_date + timedelta(days=1)
                )

                # Skip if too far in the future
                if business_datetime > self.now + timedelta(days=30):
                    continue

                self._create_single_activity(lead_id, activity, business_datetime, user_id, partner_id)

            return True

        except Exception as e:
            logger.error(f"Error creating activities for lead {lead_id}: {e}")
            return False

    def _get_activity_sequence_for_stage(self, stage_name: str) -> List[Dict]:
        """Get appropriate activity sequence for a given stage"""
        if 'NEW' in stage_name or 'COLD' in stage_name:
            # New/Cold leads: Initial outreach
            return [
                {'type': 'email', 'name': 'Initial Contact Email', 'days_offset': random.randint(1, 3), 'duration': 0.5},
                {'type': 'call', 'name': 'Follow-up Call', 'days_offset': random.randint(4, 7), 'duration': 0.5}
            ]
        elif 'POTENTIAL' in stage_name or 'PUSH TO WARM' in stage_name:
            return [
                {'type': 'email', 'name': 'Qualification Email', 'days_offset': random.randint(1, 2), 'duration': 0.5},
                {'type': 'call', 'name': 'Discovery Call', 'days_offset': random.randint(3, 5), 'duration': 1},
                {'type': 'meeting', 'name': 'Initial Meeting', 'days_offset': random.randint(7, 14), 'duration': 1}
            ]
        elif 'WARM' in stage_name:
            # Warm leads: Demo and technical discussions
            return [
                {'type': 'call', 'name': 'Needs Assessment Call', 'days_offset': random.randint(1, 3), 'duration': 1},
                {'type': 'meeting', 'name': 'Product Demo', 'days_offset': random.randint(5, 10), 'duration': 1.5},
                {'type': 'meeting', 'name': 'Technical Discussion', 'days_offset': random.randint(12, 18), 'duration': 2},
                {'type': 'email', 'name': 'Follow-up Materials', 'days_offset': random.randint(13, 20), 'duration': 0.5}
            ]
        elif 'FOCUS' in stage_name:
            # Focus leads: Multiple stakeholder meetings
            return [
                {'type': 'call', 'name': 'Stakeholder Introduction', 'days_offset': random.randint(1, 3), 'duration': 1},
                {'type': 'meeting', 'name': 'Decision Maker Meeting', 'days_offset': random.randint(5, 10), 'duration': 1.5},
                {'type': 'meeting', 'name': 'Technical Deep Dive', 'days_offset': random.randint(7, 14), 'duration': 2},
                {'type': 'meeting', 'name': 'Solution Presentation', 'days_offset': random.randint(15, 21), 'duration': 2},
                {'type': 'email', 'name': 'Proposal Submission', 'days_offset': random.randint(16, 23), 'duration': 1}
            ]
        elif 'CONTRACT' in stage_name:
            # Contract stage: Negotiations
            return [
                {'type': 'email', 'name': 'Contract Draft Sent', 'days_offset': random.randint(1, 2), 'duration': 1},
                {'type': 'call', 'name': 'Contract Review Call', 'days_offset': random.randint(3, 5), 'duration': 1},
                {'type': 'meeting', 'name': 'Negotiation Meeting', 'days_offset': random.randint(7, 10), 'duration': 2},
                {'type': 'meeting', 'name': 'Final Terms Discussion', 'days_offset': random.randint(12, 15), 'duration': 1.5}
            ]
        else:
            return []

    def _create_single_activity(self, lead_id: int, activity: Dict, business_datetime: datetime,
                                user_id: int, partner_id: Optional[int] = None) -> None:
        """Create a single activity record with proper handling for meetings"""
        try:
            activity_type_id = None

            # For meeting activities, create calendar events
            if activity['type'] == 'meeting':
                # Find meeting activity type
                meeting_activity_types = [a for a in self.activity_types if 'meeting' in a['name'].lower()]
                if meeting_activity_types:
                    activity_type_id = random.choice(meeting_activity_types)['id']
            elif activity['type'] in ['call', 'email']:
                # For calls and emails, find appropriate activity type
                call_email_types = [a for a in self.activity_types if activity['type'] in a['name'].lower()]
                if call_email_types:
                    activity_type_id = random.choice(call_email_types)['id']

            if not activity_type_id:
                return

            # Create activity record
            activity_values = {
                'res_id': lead_id,
                'res_model_id': self.execute_kw('ir.model', 'search', [[['model', '=', 'crm.lead']]])[0],
                'activity_type_id': activity_type_id,
                'summary': activity['name'],
                'note': self.fake.paragraph(nb_sentences=2),
                'date_deadline': business_datetime.strftime('%Y-%m-%d'),
                'user_id': user_id,
            }

            # Create the activity with tracking disabled
            with OdooUtils.odoo_context() as context:
                activity_id = self.execute_kw('mail.activity', 'create', [activity_values], {'context': context})

            # Mark as done if in the past
            if business_datetime < self.now:
                self._mark_activity_as_done(activity_id, lead_id, activity, activity_values,
                                          business_datetime, user_id, partner_id)
            elif business_datetime > self.now and business_datetime < self.now + timedelta(days=14):
                # Create upcoming calendar event for near-future meetings
                if activity['type'] == 'meeting':
                    self.create_calendar_event(
                        lead_id,
                        activity['name'],
                        business_datetime,
                        activity['duration'],
                        user_id,
                        partner_id
                    )

        except Exception as e:
            logger.error(f"Error creating activity: {e}")

    def _mark_activity_as_done(self, activity_id: int, lead_id: int, activity: Dict,
                              activity_values: Dict, business_datetime: datetime,
                              user_id: int, partner_id: Optional[int] = None) -> None:
        """Mark an activity as done with proper history recording"""
        try:
            # Use action_done
            self.execute_kw('mail.activity', 'action_done', [activity_id])

            # Add a message with historical timestamp
            user_name = self.users.get(user_id, {}).get('name', "Administrator")
            activity_done_msg = f"<p>{activity['name']} done (originally assigned to {user_name})</p><p>Original note:<br/>{activity_values['note']}</p>"

            # Create historical message about completed activity
            self.create_lead_message(
                lead_id,
                activity_done_msg,
                user_id,
                business_datetime
            )

            # Create a calendar event for meetings
            if activity['type'] == 'meeting':
                self.create_calendar_event(
                    lead_id,
                    activity['name'],
                    business_datetime,
                    activity['duration'],
                    user_id,
                    partner_id
                )

        except Exception as e:
            logger.error(f"Error marking activity as done: {e}")
            # If action_done fails, try unlink
            try:
                self.execute_kw('mail.activity', 'unlink', [activity_id])
            except:
                pass

    def _select_tags_for_lead(self, lead_source: str) -> List[int]:
        """Select appropriate tags for a lead"""
        selected_tags = []

        # Always select an industry tag
        if 'Industry' in self.tag_ids and self.tag_ids['Industry']:
            industry_tag = random.choice(self.tag_ids['Industry'])
            selected_tags.append(industry_tag)

        # Always select a source tag matching the lead source
        if 'Source' in self.tag_ids and self.tag_ids['Source']:
            matching_source_tags = []
            for tag_id in self.tag_ids['Source']:
                tag_name = self.execute_kw('crm.tag', 'read', [tag_id], {'fields': ['name']})[0]['name']
                if lead_source in tag_name:
                    matching_source_tags.append(tag_id)

            if matching_source_tags:
                selected_tags.append(matching_source_tags[0])
            elif self.tag_ids['Source']:
                selected_tags.append(random.choice(self.tag_ids['Source']))

        # Possibly select product interest (70% chance)
        if 'Product Interest' in self.tag_ids and self.tag_ids['Product Interest'] and random.random() < 0.7:
            product_tag = random.choice(self.tag_ids['Product Interest'])
            selected_tags.append(product_tag)

        return selected_tags

    def _get_priority_for_stage(self, stage_name: str) -> int:
        """Determine appropriate priority based on stage"""
        if 'FOCUS' in stage_name or 'CONTRACT' in stage_name:
            # More likely to be high priority in later stages
            priority_weights = [20, 30, 50]  # More likely to be high priority
            return random.choices([0, 1, 2], weights=priority_weights, k=1)[0]
        else:
            # Normal distribution for other stages
            priority_weights = [70, 20, 10]  # 0=Normal, 1=Medium, 2=High
            return random.choices([0, 1, 2], weights=priority_weights, k=1)[0]

    def _get_country_id(self, company: Dict) -> Optional[int]:
        """Get country ID from company data"""
        country_id = False
        if 'country' in company:
            country_search = self.execute_kw('res.country', 'search', [[['name', 'ilike', company['country']]]])
            if country_search:
                country_id = country_search[0]
        return country_id

    def _create_partner_for_lead(self, lead_id: int, lead_data: Dict) -> Optional[int]:
        """Create partner record for a lead"""
        try:
            # Create partner with tracking disabled
            with OdooUtils.odoo_context() as context:
                partner_data = {
                    'name': lead_data['contact_name'],
                    'email': lead_data['email_from'],
                    'phone': lead_data.get('phone', ''),
                    'company_type': 'person',
                    'company_name': lead_data['partner_name'],
                    'function': lead_data.get('function', ''),
                    'country_id': lead_data.get('country_id', False)
                }

                partner_id = self.execute_kw('res.partner', 'create', [partner_data], {'context': context})

                # Link partner to lead
                self.execute_kw('crm.lead', 'write', [lead_id, {'partner_id': partner_id}], {'context': context})

                return partner_id

        except Exception as e:
            logger.warning(f"Could not create partner for lead {lead_id}: {e}")
            return None

    def _select_user(self, company: Dict) -> int:
        """Select a random user based on company's country"""
        if not self.users:
            logger.warning("No users found in the system")
            return self.uid

        # Determine team name based on country
        country = company.get('country', '').lower()
        if 'indonesia' in country or 'id' in country:
            team_name = 'Sales Indonesia'
        elif 'singapore' in country or 'sg' in country:
            team_name = 'Sales Singapore'
        else:
            team_name = random.choice(['Sales Indonesia', 'Sales Singapore'])

        # Get users for the team directly from Odoo
        team_users = self.execute_kw('res.users', 'search_read',
                                    [[('sale_team_id.name', '=', team_name)]],
                                    {'fields': ['id', 'name']})

        if team_users:
            selected_user = random.choice(team_users)
            logger.info(f"Selected user {selected_user['name']} from team {team_name}")
            return selected_user['id']

        logger.warning(f"No users found for team {team_name}, falling back to admin user")
        return self.uid

    def _prepare_lead_data(self, company: Dict, user_id: int,
                        probability_data: Dict, lead_source: str,
                        selected_tags: List[int],
                        date_created: datetime) -> Dict:
        """Prepare lead data dictionary"""
        stage_name = self.stage_names[probability_data['stage_id']].upper()
        lead_type = 'lead' if 'NEW' in stage_name or 'COLD' in stage_name else 'opportunity'

        # Add priority (star rating)
        priority = self._get_priority_for_stage(stage_name)

        # Prepare country ID
        country_id = self._get_country_id(company)

        # Create contact information
        contact_name = self.fake.name()
        email_domain = company['website'].replace('www.', '') if 'website' in company else self.fake.domain_name()

        # Determine team based on country
        country = company.get('country', '').lower()
        if 'indonesia' in country or 'id' in country:
            team_search = self.execute_kw('crm.team', 'search_read',
                                        [[['name', '=', 'Sales Indonesia']]],
                                        {'fields': ['id']})
            team_id = team_search[0]['id'] if team_search else False
        elif 'singapore' in country or 'sg' in country:
            team_search = self.execute_kw('crm.team', 'search_read',
                                        [[['name', '=', 'Sales Singapore']]],
                                        {'fields': ['id']})
            team_id = team_search[0]['id'] if team_search else False
        else:
            # Randomly assign to either team if country is not clearly identifiable
            team_name = random.choice(['Sales Indonesia', 'Sales Singapore'])
            team_search = self.execute_kw('crm.team', 'search_read',
                                        [[['name', '=', team_name]]],
                                        {'fields': ['id']})
            team_id = team_search[0]['id'] if team_search else False

        # Add debugging log
        logger.info(f"Assigning lead for {company.get('name')} ({company.get('country')}) to team ID {team_id}")

        lead_data = {
            'name': f"{company.get('name', 'Unknown')} - {self.fake.catch_phrase()} Project",
            'partner_name': company.get('name', self.fake.company()),
            'contact_name': contact_name,
            'function': self.fake.job(),
            'email_from': f"{contact_name.split()[0].lower()}.{contact_name.split()[-1].lower()}@{email_domain}",
            'phone': self.fake.phone_number(),
            'user_id': user_id,
            'team_id': team_id,
            'stage_id': probability_data['stage_id'],
            'type': lead_type,
            'probability': probability_data['probability'],
            'expected_revenue': probability_data['expected_revenue'],
            'date_deadline': (date_created + timedelta(days=30)).strftime('%Y-%m-%d'),
            'description': self.fake.paragraph(nb_sentences=5),
            'priority': str(priority),
            'tag_ids': [(6, 0, selected_tags)] if selected_tags else False,
            'referred': lead_source == 'Referral',
            'country_id': country_id,
        }

        return lead_data

    def generate_leads(self, count: int = 100) -> bool:
        """Generate realistic dummy leads/opportunities"""
        try:
            # Setup required data structures
            logger.info("Setting up initial data structures...")

            # First set up teams
            team_ids = self.setup_sales_teams()
            if not team_ids:
                logger.error("Failed to set up sales teams")
                return False

            # Then set up other required data
            self.setup_crm_tags()
            self.setup_user_roles()
            self.load_company_data()
            self.get_crm_stages()
            self.get_activity_types()

            if not self.stages:
                logger.error("No CRM stages found. Cannot generate leads.")
                return False

            # Check if we have teams and users properly set up
            if not self.users:
                logger.error("No users found. Cannot generate leads.")
                return False

            # Get lead sources with weighted probabilities
            source_options = list(self.LEAD_SOURCES.keys())
            source_weights = list(self.LEAD_SOURCES.values())

            logger.info(f"Generating {count} leads/opportunities...")
            created_count = 0
            all_created_leads = []

            for i in range(count):
                # Choose a company and assign user
                company = random.choice(self.companies)
                user_id = self._select_user(company)
                date_created = self._generate_creation_date(i, count)

                # Get probability and related data based on creation date
                probability_data = self.get_probability_data(date_created)

                # Determine lead source with weighted random selection
                lead_source = random.choices(source_options, weights=source_weights, k=1)[0]

                # Select tags
                selected_tags = self._select_tags_for_lead(lead_source)

                # Prepare lead data
                lead_data = self._prepare_lead_data(
                    company, user_id, probability_data,
                    lead_source, selected_tags, date_created
                )

                # Filter out any False values that might cause XML-RPC errors
                lead_data = {k: v for k, v in lead_data.items() if v is not None and v is not False}

                try:
                    # Create the lead with tracking disabled
                    with OdooUtils.odoo_context() as context:
                        lead_id = self.execute_kw('crm.lead', 'create', [lead_data], {'context': context})

                    all_created_leads.append(lead_id)

                    # Create lead history with proper timestamps
                    self.create_realistic_lead_history(lead_id, lead_data, date_created, probability_data['stage_id'])

                    # Create partner record if needed
                    partner_id = self._create_partner_for_lead(lead_id, lead_data)

                    # Create activities and meetings
                    self.create_lead_activities(lead_id, lead_data, date_created, partner_id)

                    created_count += 1
                    if created_count % 10 == 0:
                        logger.info(f"Created {created_count} leads so far...")

                except Exception as e:
                    logger.error(f"Error creating lead {i+1}: {e}")

            logger.info(f"Successfully created {created_count} realistic leads/opportunities")
            return True

        except Exception as e:
            logger.error(f"Error generating dummy data: {e}")
            return False

    def _generate_creation_date(self, index: int, total_count: int) -> datetime:
        """Generate appropriate creation date with weighting toward recency"""
        if index < total_count * 0.1:  # 10% very old leads
            return self.fake.date_time_between(start_date='-2y', end_date='-1y')
        elif index < total_count * 0.3:  # 20% older leads
            return self.fake.date_time_between(start_date='-1y', end_date='-6m')
        elif index < total_count * 0.7:  # 40% medium age
            return self.fake.date_time_between(start_date='-6m', end_date='-1m')
        else:  # 30% recent leads
            return self.fake.date_time_between(start_date='-1m', end_date='now')


def main():
    parser = argparse.ArgumentParser(description='Generate realistic CRM data in Odoo')
    parser.add_argument('--url', default='http://localhost:8069', help='Odoo URL')
    parser.add_argument('--db', default='crm_project', help='Database name')
    parser.add_argument('--username', default='admin', help='Username')
    parser.add_argument('--password', default='admin', help='Password')
    parser.add_argument('--count', type=int, default=100, help='Number of leads to generate')

    args = parser.parse_args()

    logger.info(f"Connecting to Odoo at {args.url}")
    uid, models = OdooUtils.connect_to_odoo(args.url, args.db, args.username, args.password)

    if not uid or not models:
        logger.error("Failed to connect to Odoo")
        return

    logger.info("Connected to Odoo successfully")

    # Generate dummy leads
    generator = CrmDataGenerator(uid, models, args.db, args.password)
    generator.generate_leads(args.count)

if __name__ == "__main__":
    main()