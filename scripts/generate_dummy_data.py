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

# Set Indonesian locale
for loc in [DEFAULT_LOCALE, FALLBACK_LOCALE]:
    try:
        locale.setlocale(locale.LC_ALL, loc)
        break
    except locale.Error:
        continue
else:
    logger.warning("Could not set Indonesian locale, using default")


class OdooUtils:
    """Utility class for Odoo connection and operations."""

    @staticmethod
    def format_idr(amount: float) -> str:
        """Format amount as IDR currency."""
        try:
            return format_currency(amount, 'IDR', locale='id_ID')
        except:
            return f"Rp {amount:,.0f},-"

    @staticmethod
    def connect_to_odoo(url: str, db: str, username: str, password: str, max_retries: int = MAX_RETRIES) -> Tuple[Optional[int], Optional[xmlrpc.client.ServerProxy]]:
        """Establish connection to Odoo instance with retries."""
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
            except Exception as e:
                logger.error(f"Connection error: {e}")

            if attempt < max_retries - 1:
                logger.info(f"Retrying in {RETRY_DELAY} seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(RETRY_DELAY)

        return None, None

    @staticmethod
    @contextmanager
    def odoo_context(tracking_disabled: bool = True):
        """Context manager to provide standard context for Odoo operations."""
        context = {
            'mail_auto_subscribe_no_notify': tracking_disabled,
            'tracking_disable': tracking_disabled,
            'mail_create_nosubscribe': tracking_disabled,
            'mail_create_nolog': tracking_disabled
        }
        yield context


class CrmDataGenerator:
    """Generator for realistic CRM data in Odoo."""

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

    # Product list
    PRODUCT_LIST = [
        'SIAP + HRM',
        'SIAP',
        'CRM sales',
        'POS sales',
        'ERP Manufacture',
        'ERP Construction',
        'HRM',
        'Talent Management',
        'LMS',
        'HR Recruitment',
        'SIAP + Asset',
        'Mining + Asset',
    ]

    # Tag categories
    TAG_CATEGORIES = {
        'Industry': [
            'Technology', 'Healthcare', 'Finance', 'Manufacturing', 'Retail',
            'Education', 'Hospitality', 'Construction', 'Energy', 'Agriculture',
            'Transportation', 'Media', 'Professional Services', 'Government', 'Non-profit'
        ],
        'Source': [
            'SME', 'SEO', 'Referral', 'Cold Call', 'Email Campaign',
            'Social Media', 'Webinar', 'Content Download', 'Partner', 'Paid Search',
            'Organic Search', 'Trade Show', 'Direct Mail'
        ],
        'Product Interest': PRODUCT_LIST
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
        """Initialize the generator with Odoo connection details."""
        self.uid = uid
        self.models = models
        self.db = db
        self.password = password
        self.fake = Faker()
        self.now = datetime.now()

        # Initialize data structures
        self.tag_ids = {}
        self.users = {}
        self.stages = []
        self.stage_ids = []
        self.stage_names = {}
        self.activity_types = []
        self.companies = []

    def execute_kw(self, model: str, method: str, args: List, kwargs: Dict = None) -> Any:
        """Execute Odoo RPC call with error handling."""
        if kwargs is None:
            kwargs = {}

        try:
            return self.models.execute_kw(self.db, self.uid, self.password, model, method, args, kwargs)
        except Exception as e:
            logger.error(f"Error executing {model}.{method}: {e}")
            raise

    def setup_crm_tags(self) -> Dict[str, List[int]]:
        """Set up CRM tags for lead categorization."""
        try:
            logger.info("Setting up CRM tags...")
            tag_ids = defaultdict(list)

            for category, tags in self.TAG_CATEGORIES.items():
                for tag in tags:
                    tag_name = f"{category}: {tag}"
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
        """Set up user roles with team assignments."""
        try:
            logger.info("Setting up user roles...")
            # Set up teams first
            sales_teams = self.execute_kw('crm.team', 'search_read',
                                        [[('name', 'in', ['Sales Indonesia', 'Sales Singapore'])]],
                                        {'fields': ['id', 'name']})
            team_map = {team['name']: team['id'] for team in sales_teams}

            # Get required groups
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
                    self._create_or_update_user(name, login, title, team_id, team_name, group_ids)

            # Verify team memberships
            self._verify_team_memberships(team_map)

            # Get final user list
            users = self.execute_kw('res.users', 'search_read',
                                [[('share', '=', False)]],
                                {'fields': ['id', 'name', 'login', 'sale_team_id']})

            users_dict = {user['id']: user for user in users}
            self.users = users_dict
            return users_dict
        except Exception as e:
            logger.error(f"Error setting up user roles: {e}")
            return {}

    def _create_or_update_user(self, name, login, title, team_id, team_name, group_ids):
        """Create or update a user with proper team assignment."""
        try:
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
                'groups_id': [(6, 0, group_ids)],
                'share': False,
                'notification_type': 'email',
            }

            if existing_user:
                # Update existing user
                user_id = existing_user[0]['id']
                self.execute_kw('res.users', 'write', [[user_id], user_vals])
                logger.info(f"Updated user '{name}' with team {team_name}")
            else:
                # Create new user
                user_id = self.execute_kw('res.users', 'create', [user_vals])
                logger.info(f"Created user '{name}' with team {team_name}")

            # Add user to team membership
            self._add_user_to_team(user_id, team_id, team_name, name)

        except Exception as e:
            logger.error(f"Error creating/updating user {name}: {e}")

    def _add_user_to_team(self, user_id, team_id, team_name, name):
        """Add a user to a sales team as a member."""
        try:
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
            logger.error(f"Error adding user {name} to team: {e}")

    def _verify_team_memberships(self, team_map):
        """Verify and log team memberships."""
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

    def setup_sales_teams(self) -> Dict[str, int]:
        """Set up sales teams for Indonesia and Singapore."""
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

    def get_crm_stages(self) -> List[Dict]:
        """Get CRM stages from Odoo."""
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
        """Get activity types from Odoo."""
        activity_types = self.execute_kw('mail.activity.type', 'search_read', [[]], {'fields': ['id', 'name']})
        logger.info(f"Found {len(activity_types)} activity types")
        self.activity_types = activity_types
        return activity_types

    def get_note_subtype_id(self) -> int:
        """Get the note subtype ID for messages."""
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
        """Generate a datetime during business hours on weekdays."""
        # Get a random date
        time_delta = end_date - start_date
        days_delta = time_delta.days + 1

        if days_delta <= 0:
            random_date = start_date
        else:
            random_days = random.randint(0, days_delta)
            random_date = start_date + timedelta(days=random_days)

        # Adjust for weekends
        while random_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
            random_date += timedelta(days=1)
            if random_date > end_date:
                random_date = end_date
                # If end_date is a weekend, move to previous Friday
                while random_date.weekday() >= 5:
                    random_date -= timedelta(days=1)

        # Set to business hours
        business_start = dt_time(8, 0, 0)  # 8:00
        business_end = dt_time(17, 0, 0)   # 17:00

        # Random time during business hours
        random_hour = random.randint(business_start.hour, business_end.hour - 1)
        random_minute = random.choice([0, 15, 30, 45])  # Realistic meeting start times

        return random_date.replace(hour=random_hour, minute=random_minute, second=0)

    def _get_user_partner_id(self, user_id: int) -> Optional[int]:
        """Get the partner ID associated with a user."""
        try:
            user_data = self.execute_kw('res.users', 'read', [user_id], {'fields': ['partner_id']})
            if user_data and user_data[0]['partner_id']:
                return user_data[0]['partner_id'][0]
        except Exception as e:
            logger.error(f"Error getting partner ID for user {user_id}: {e}")
        return None

    def create_lead_message(self, lead_id: int, body: str, author_id: int,
                          message_date: datetime, subtype_id: Optional[int] = None) -> Optional[int]:
        """Create a message for a lead with specific historical date."""
        try:
            note_subtype_id = subtype_id or self.get_note_subtype_id()
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

            return self.execute_kw('mail.message', 'create', [message_vals])
        except Exception as e:
            logger.error(f"Error creating lead message: {e}")
            return None

    def add_stage_change_log(self, lead_id: int, old_stage_name: str, new_stage_name: str,
                           user_id: int, date: datetime) -> Optional[int]:
        """Add a log note about stage change with timestamp."""
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
        """Create a calendar event with proper historical dates."""
        try:
            end_datetime = start_datetime + timedelta(hours=duration_hours)

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
                event_id = self.execute_kw('calendar.event', 'create', [event_vals], {'context': context})

                if start_datetime < self.now:
                    # Get user name for the message
                    user_name = self.users.get(user_id, {}).get('name', "Administrator")

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
        """Add a user-friendly stage change message with timestamp."""
        try:
            old_stage_name = self.stage_names.get(old_stage_id, "Unknown")
            new_stage_name = self.stage_names.get(new_stage_id, "Unknown")
            user_name = self.users.get(user_id, {}).get('name', "Administrator")

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
        """Calculate probability and other metrics based on lead age."""
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
        won_stage_id = next((sid for sid, sname in self.stage_names.items()
                             if 'WON' in sname.upper()), None)
        lost_stage_id = next((sid for sid, sname in self.stage_names.items()
                              if 'LOST' in sname.upper()), None)

        # Ensure won/lost leads stay in terminal state
        if 'WON' in stage_name and lost_stage_id and random.random() < 0.99:
            if stage_id == lost_stage_id:
                stage_id = won_stage_id
                stage_index = self.stage_ids.index(stage_id)
                stage_name = self.stage_names[stage_id].upper()

        # Assign probability based on stage
        probability = self._calculate_probability_for_stage(stage_name)
        revenue = self._calculate_revenue_for_stage(stage_name)

        return {
            'stage_id': stage_id,
            'stage_index': stage_index,
            'probability': probability,
            'expected_revenue': revenue
        }

    def _calculate_probability_for_stage(self, stage_name: str) -> int:
        """Calculate probability based on stage name."""
        if 'WON' in stage_name:
            return 100
        elif 'LOST' in stage_name:
            return 0
        elif 'CONTRACT' in stage_name:
            return random.randint(80, 95)
        elif 'FOCUS' in stage_name:
            return random.randint(60, 80)
        elif 'WARM' in stage_name:
            return random.randint(40, 60)
        elif 'PUSH TO WARM' in stage_name:
            return random.randint(30, 50)
        elif 'POTENTIAL' in stage_name:
            return random.randint(20, 40)
        elif 'COLD' in stage_name:
            return random.randint(1, 20)
        elif 'NEW' in stage_name:
            return random.randint(1, 10)
        else:
            return random.randint(10, 50)

    def _calculate_revenue_for_stage(self, stage_name: str) -> int:
        """Calculate expected revenue based on stage name."""
        IDR_CONVERSION = 1000
        base_revenue = random.randint(5000, 500000) * IDR_CONVERSION

        # Find the best matching stage factor
        best_match = next((key for key in self.STAGE_TO_REVENUE_FACTOR
                           if key in stage_name), None)

        revenue_factor = self.STAGE_TO_REVENUE_FACTOR.get(best_match, 0.7)
        return int(base_revenue * revenue_factor / 1000) * 1000

    def create_realistic_lead_history(self, lead_id: int, lead_data: Dict,
                                    date_created: datetime, current_stage_id: int) -> bool:
        """Create a realistic history of stage changes and messages for a lead."""
        try:
            assigned_user_id = lead_data.get('user_id', self.uid)
            user_name = self.users.get(assigned_user_id, {}).get('name', "Administrator")

            # Add creation message
            creation_msg = f"<p>Lead/Opportunity created by {user_name}</p>"
            self.create_lead_message(lead_id, creation_msg, assigned_user_id, date_created)

            # Add customer info message
            customer_msg = f"<p>Customer information added by {user_name}<br/>{lead_data.get('partner_name', '')}, {lead_data.get('contact_name', '')}</p>"
            self.create_lead_message(
                lead_id,
                customer_msg,
                assigned_user_id,
                date_created + timedelta(minutes=random.randint(1, 5))
            )

            # Create stage history if lead has progressed
            current_stage_index = self.stage_ids.index(current_stage_id)
            if current_stage_index > 0:
                self._create_stage_change_history(lead_id, lead_data, date_created, current_stage_index)

            return True
        except Exception as e:
            logger.error(f"Error creating lead history for lead {lead_id}: {e}")
            return False

    def _create_stage_change_history(self, lead_id: int, lead_data: Dict, date_created: datetime,
                                   current_stage_index: int) -> None:
        """Create stage change history for a lead."""
        # Generate timestamps for stage transitions
        stage_dates = []
        current_date = date_created + timedelta(hours=random.randint(2, 8))
        assigned_user_id = lead_data.get('user_id', self.uid)

        # Generate sequential stage transitions with time gaps
        for i in range(current_stage_index):
            from_stage_id = self.stage_ids[i]
            to_stage_id = self.stage_ids[i+1]
            from_stage_name = self.stage_names[from_stage_id].upper()
            to_stage_name = self.stage_names[to_stage_id].upper()

            # Skip invalid transitions
            if 'WON' in from_stage_name or 'LOST' in from_stage_name:
                continue

            # Calculate days to add based on stage
            days_to_add = self._calculate_days_between_stages(from_stage_name, to_stage_name)

            # Ensure each date is strictly after the previous one
            current_date = max(current_date + timedelta(days=days_to_add),
                             stage_dates[-1] + timedelta(days=1) if stage_dates else current_date)

            # Don't exceed current date
            if current_date > self.now:
                current_date = self.now - timedelta(hours=random.randint(1, 48))

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
                self._add_manager_review(lead_id, to_stage_name, stage_date)

            # Log stage change
            self.add_stage_change_log(
                lead_id,
                self.stage_names[from_stage_id],
                self.stage_names[to_stage_id],
                assigned_user_id,
                stage_date
            )

            # Add user-friendly message
            self.add_custom_stage_change_message(
                lead_id,
                from_stage_id,
                to_stage_id,
                assigned_user_id,
                stage_date + timedelta(seconds=30)
            )

            # Apply stage change
            with OdooUtils.odoo_context() as context:
                self.execute_kw('crm.lead', 'write', [
                    lead_id,
                    {
                        'stage_id': to_stage_id,
                        'user_id': assigned_user_id,
                    }
                ], {'context': context})

    def _calculate_days_between_stages(self, from_stage_name: str, to_stage_name: str) -> int:
        """Calculate reasonable days between stage transitions."""
        if 'NEW' in from_stage_name:
            return random.randint(1, 3)
        elif 'COLD' in from_stage_name:
            return random.randint(2, 10)
        elif 'POTENTIAL' in from_stage_name:
            return random.randint(2, 8)
        elif 'PUSH TO WARM' in from_stage_name:
            return random.randint(1, 7)
        elif 'WARM' in from_stage_name:
            return random.randint(3, 10)
        elif 'FOCUS' in from_stage_name:
            return random.randint(3, 15)
        elif 'CONTRACT' in from_stage_name:
            if 'WON' in to_stage_name:
                return random.randint(5, 20)
            elif 'LOST' in to_stage_name:
                return random.randint(5, 30)
            else:
                return random.randint(3, 15)
        else:
            return random.randint(1, 7)

    def _add_manager_review(self, lead_id: int, stage_name: str, stage_date: datetime):
        """Add manager review message for important stage changes."""
        manager_users = [uid for uid, user in self.users.items()
                        if 'Manager' in user.get('name', '') or 'Director' in user.get('name', '')]
        if manager_users:
            manager_id = random.choice(manager_users)
            manager_message = f"Reviewed the opportunity and approved the stage change to '{stage_name}'"
            self.create_lead_message(
                lead_id,
                manager_message,
                manager_id,
                stage_date + timedelta(hours=random.randint(1, 4))
            )

    def create_lead_activities(self, lead_id: int, lead_data: Dict, date_created: datetime,
                             partner_id: Optional[int] = None) -> bool:
        """Create activities and meetings for a lead based on its stage."""
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
        """Get appropriate activity sequence for a given stage."""
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
        """Create a single activity record with proper handling for meetings."""
        try:
            activity_type_id = self._get_activity_type_id(activity['type'])
            if not activity_type_id:
                return

            activity_values = {
                'res_id': lead_id,
                'res_model_id': self.execute_kw('ir.model', 'search', [[['model', '=', 'crm.lead']]])[0],
                'activity_type_id': activity_type_id,
                'summary': activity['name'],
                'note': self.fake.paragraph(nb_sentences=2),
                'date_deadline': business_datetime.strftime('%Y-%m-%d'),
                'user_id': user_id,
            }

            with OdooUtils.odoo_context() as context:
                activity_id = self.execute_kw('mail.activity', 'create', [activity_values], {'context': context})

            if business_datetime < self.now:
                self._mark_activity_as_done(activity_id, lead_id, activity, activity_values,
                                          business_datetime, user_id, partner_id)
            elif business_datetime > self.now and business_datetime < self.now + timedelta(days=14):
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

    def _get_activity_type_id(self, activity_type: str) -> Optional[int]:
        """Get activity type ID based on activity type string."""
        if activity_type == 'meeting':
            meeting_activity_types = [a for a in self.activity_types if 'meeting' in a['name'].lower()]
            if meeting_activity_types:
                return random.choice(meeting_activity_types)['id']
        elif activity_type in ['call', 'email']:
            call_email_types = [a for a in self.activity_types if activity_type in a['name'].lower()]
            if call_email_types:
                return random.choice(call_email_types)['id']
        return None

    def _mark_activity_as_done(self, activity_id: int, lead_id: int, activity: Dict,
                             activity_values: Dict, business_datetime: datetime,
                             user_id: int, partner_id: Optional[int] = None) -> None:
        """Mark an activity as done with proper history recording."""
        try:
            self.execute_kw('mail.activity', 'action_done', [activity_id])

            user_name = self.users.get(user_id, {}).get('name', "Administrator")
            activity_done_msg = f"<p>{activity['name']} done (originally assigned to {user_name})</p><p>Original note:<br/>{activity_values['note']}</p>"

            self.create_lead_message(
                lead_id,
                activity_done_msg,
                user_id,
                business_datetime
            )

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
            try:
                self.execute_kw('mail.activity', 'unlink', [activity_id])
            except:
                pass

    def _select_tags_for_lead(self, lead_source: str, company_data: Dict, product_name: str = None) -> List[int]:
        """Select appropriate tags for a lead based on company data and product."""
        selected_tags = []

        # Industry tag
        if 'Industry' in self.tag_ids and self.tag_ids['Industry']:
            industry_tag = self._get_or_create_industry_tag(company_data)
            if industry_tag:
                selected_tags.append(industry_tag)

        # Source tag
        if 'Source' in self.tag_ids and self.tag_ids['Source']:
            source_tag = self._get_source_tag(lead_source)
            if source_tag:
                selected_tags.append(source_tag)

        # Product interest tag
        if 'Product Interest' in self.tag_ids and self.tag_ids['Product Interest']:
            product_tag = self._get_or_create_product_tag(product_name)
            if product_tag:
                selected_tags.append(product_tag)

        return selected_tags

    def _get_or_create_industry_tag(self, company_data: Dict) -> Optional[int]:
        """Get or create industry tag based on company data."""
        if not company_data.get('industry'):
            return random.choice(self.tag_ids['Industry']) if self.tag_ids['Industry'] else None

        # Look for matching tag
        for tag_id in self.tag_ids['Industry']:
            tag_name = self.execute_kw('crm.tag', 'read', [tag_id], {'fields': ['name']})[0]['name']
            if ': ' in tag_name:
                tag_value = tag_name.split(': ')[1]
                if company_data['industry'] in tag_value or tag_value in company_data['industry']:
                    return tag_id

        # Create new tag if no match
        try:
            tag_name = f"Industry: {company_data['industry']}"
            existing_tag = self.execute_kw('crm.tag', 'search_read',
                                    [[['name', '=', tag_name]]], {'fields': ['id']})
            if existing_tag:
                new_tag_id = existing_tag[0]['id']
            else:
                new_tag_id = self.execute_kw('crm.tag', 'create', [{'name': tag_name}])
                self.tag_ids['Industry'].append(new_tag_id)
            return new_tag_id
        except Exception as e:
            logger.warning(f"Could not create tag for industry {company_data['industry']}: {e}")
            return random.choice(self.tag_ids['Industry']) if self.tag_ids['Industry'] else None

    def _get_source_tag(self, lead_source: str) -> Optional[int]:
        """Get source tag matching the lead source."""
        matching_source_tags = []
        for tag_id in self.tag_ids['Source']:
            tag_name = self.execute_kw('crm.tag', 'read', [tag_id], {'fields': ['name']})[0]['name']
            if lead_source in tag_name:
                matching_source_tags.append(tag_id)

        if matching_source_tags:
            return matching_source_tags[0]
        elif self.tag_ids['Source']:
            return random.choice(self.tag_ids['Source'])
        return None

    def _get_or_create_product_tag(self, product_name: str) -> Optional[int]:
        """Get or create product interest tag."""
        if not product_name:
            return random.choice(self.tag_ids['Product Interest']) if self.tag_ids['Product Interest'] else None

        # Look for matching tag
        for tag_id in self.tag_ids['Product Interest']:
            tag_name = self.execute_kw('crm.tag', 'read', [tag_id], {'fields': ['name']})[0]['name']
            if product_name in tag_name:
                return tag_id

        # Create new tag if no match
        try:
            tag_name = f"Product Interest: {product_name}"
            existing_tag = self.execute_kw('crm.tag', 'search_read',
                                    [[['name', '=', tag_name]]], {'fields': ['id']})
            if existing_tag:
                new_tag_id = existing_tag[0]['id']
            else:
                new_tag_id = self.execute_kw('crm.tag', 'create', [{'name': tag_name}])
                self.tag_ids['Product Interest'].append(new_tag_id)
            return new_tag_id
        except Exception as e:
            logger.warning(f"Could not create tag for product {product_name}: {e}")
            return random.choice(self.tag_ids['Product Interest']) if self.tag_ids['Product Interest'] else None

    def _get_priority_for_stage(self, stage_name: str) -> int:
        """Determine appropriate priority based on stage."""
        if 'FOCUS' in stage_name or 'CONTRACT' in stage_name:
            # More likely to be high priority in later stages
            priority_weights = [20, 30, 50]  # More likely to be high priority
            return random.choices([0, 1, 2], weights=priority_weights, k=1)[0]
        else:
            # Normal distribution for other stages
            priority_weights = [70, 20, 10]  # 0=Normal, 1=Medium, 2=High
            return random.choices([0, 1, 2], weights=priority_weights, k=1)[0]

    def _create_partner_for_lead(self, lead_id: int, lead_data: Dict) -> Optional[int]:
        """Create partner record for a lead."""
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
        """Select appropriate user based on company's country."""
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

        # Get users for the team
        team_users = self.execute_kw('res.users', 'search_read',
                                    [[('sale_team_id.name', '=', team_name)]],
                                    {'fields': ['id', 'name']})

        if team_users:
            selected_user = random.choice(team_users)
            logger.info(f"Selected user {selected_user['name']} from team {team_name}")
            return selected_user['id']

        logger.warning(f"No users found for team {team_name}, falling back to admin user")
        return self.uid

    def load_company_data_from_csv(self, csv_file_path=None):
        """Load company data from a CSV file."""
        companies = []

        if not csv_file_path:
            raise ValueError("No CSV file path provided. A company data CSV file is required.")

        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"CSV file not found at: {csv_file_path}")

        try:
            with open(csv_file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    companies.append({
                        'name': row.get('Company', '').strip('$'),
                        'industry': row.get('Industry', ''),
                        'country': row.get('Country', ''),
                        'city': row.get('City', ''),
                        'valuation': row.get('Valuation ($B)', '').strip('$'),
                        'website': f"www.{row.get('Company', '').lower().replace(' ', '')}.com",
                    })

            if not companies:
                raise ValueError("CSV file is empty or has invalid format.")

            logger.info(f"Loaded {len(companies)} companies from CSV file")
        except Exception as e:
            logger.error(f"Error loading company data: {e}")
            raise

        self.companies = companies
        return companies

    def create_company_record(self, company_data):
        """Create a company record in Odoo."""
        try:
            # Check if company already exists
            existing_company = self.execute_kw('res.partner', 'search_read',
                                            [[['name', '=', company_data['name']],
                                              ['is_company', '=', True]]],
                                            {'fields': ['id']})

            if existing_company:
                return existing_company[0]['id']

            # Get country ID
            country_id = False
            if company_data.get('country'):
                country_search = self.execute_kw('res.country', 'search',
                                            [[['name', 'ilike', company_data['country']]]])
                if country_search:
                    country_id = country_search[0]

            # Find or create industry ID
            industry_id = self._get_or_create_industry(company_data.get('industry'))

            with OdooUtils.odoo_context() as context:
                company_vals = {
                    'name': company_data['name'],
                    'is_company': True,
                    'company_type': 'company',
                    'website': company_data.get('website', ''),
                    'country_id': country_id,
                    'industry_id': industry_id,
                }

                if company_data.get('city'):
                    company_vals['city'] = company_data['city']

                company_id = self.execute_kw('res.partner', 'create', [company_vals], {'context': context})

                logger.info(f"Created company record for {company_data['name']} with industry: {company_data.get('industry', 'None')}")
                return company_id
        except Exception as e:
            logger.error(f"Error creating company record: {e}")
            return False

    def _get_or_create_industry(self, industry_name):
        """Find or create an industry record."""
        if not industry_name:
            return False

        # Try to find the industry in Odoo
        industry_search = self.execute_kw('res.partner.industry', 'search',
                                        [[['name', 'ilike', industry_name]]])
        if industry_search:
            return industry_search[0]

        # Create the industry if it doesn't exist
        try:
            industry_id = self.execute_kw('res.partner.industry', 'create',
                                        [{'name': industry_name}])
            logger.info(f"Created new industry: {industry_name}")
            return industry_id
        except Exception as e:
            logger.warning(f"Could not create industry {industry_name}: {e}")
            return False

    def _prepare_lead_data(self, company_data, company_id, user_id,
                                    probability_data, lead_source, selected_tags,
                                    date_created, product_name=None) -> Dict:
        """Prepare lead data dictionary using company record."""
        stage_name = self.stage_names[probability_data['stage_id']].upper()
        lead_type = 'lead' if 'NEW' in stage_name or 'COLD' in stage_name else 'opportunity'

        priority = self._get_priority_for_stage(stage_name)

        contact_name = self.fake.name()
        contact_first_name = contact_name.split()[0]
        email_domain = company_data.get('website', self.fake.domain_name()).replace('www.', '')

        if not product_name:
            product_name = random.choice(self.PRODUCT_LIST)

        lead_name = f"{contact_first_name} | {product_name} | {company_data.get('name', 'Unknown')}"

        # Get team ID based on country
        team_id = self._get_team_id_for_country(company_data.get('country', ''))

        lead_data = {
            'name': lead_name,
            'partner_name': company_data.get('name', self.fake.company()),
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
            'description': f"Product: {product_name}\n\n{self.fake.paragraph(nb_sentences=5)}",
            'priority': str(priority),
            'tag_ids': [(6, 0, selected_tags)] if selected_tags else False,
            'referred': lead_source == 'Referral',
            'partner_id': company_id,
        }

        return lead_data

    def _get_team_id_for_country(self, country):
        """Get sales team ID based on country."""
        country = country.lower()
        if 'indonesia' in country or 'id' in country:
            team_name = 'Sales Indonesia'
        elif 'singapore' in country or 'sg' in country:
            team_name = 'Sales Singapore'
        else:
            team_name = random.choice(['Sales Indonesia', 'Sales Singapore'])

        team_search = self.execute_kw('crm.team', 'search_read',
                                    [[['name', '=', team_name]]],
                                    {'fields': ['id']})

        team_id = team_search[0]['id'] if team_search else False
        logger.info(f"Assigning lead for country '{country}' to team '{team_name}' (ID: {team_id})")
        return team_id

    def generate_leads(self, count: int = 100, company_csv=None) -> bool:
        """Generate realistic dummy leads/opportunities."""
        try:
            logger.info("Setting up initial data structures...")

            if not company_csv:
                logger.error("No company CSV file provided. This is required to generate leads.")
                return False

            # Initialize required data
            team_ids = self.setup_sales_teams()
            if not team_ids:
                logger.error("Failed to set up sales teams")
                return False

            self.setup_crm_tags()
            self.setup_user_roles()
            self.load_company_data_from_csv(company_csv)
            self.get_crm_stages()
            self.get_activity_types()

            # Validate required data
            if not self.stages:
                logger.error("No CRM stages found. Cannot generate leads.")
                return False

            if not self.users:
                logger.error("No users found. Cannot generate leads.")
                return False

            # Prepare lead source options
            source_options = list(self.LEAD_SOURCES.keys())
            source_weights = list(self.LEAD_SOURCES.values())

            logger.info(f"Generating {count} leads/opportunities...")
            created_count = 0
            all_created_leads = []

            for i in range(count):
                # Select random company and assign user
                company_data = random.choice(self.companies)
                company_id = self.create_company_record(company_data)
                user_id = self._select_user(company_data)

                # Generate creation date and calculate probability data
                date_created = self._generate_creation_date(i, count)
                probability_data = self.get_probability_data(date_created)

                lead_source = random.choices(source_options, weights=source_weights, k=1)[0]
                product_name = random.choice(self.PRODUCT_LIST)
                selected_tags = self._select_tags_for_lead(lead_source, company_data, product_name)

                lead_data = self._prepare_lead_data(
                    company_data, company_id, user_id, probability_data,
                    lead_source, selected_tags, date_created, product_name
                )

                # Filter out None and False values
                lead_data = {k: v for k, v in lead_data.items() if v is not None and v is not False}

                try:
                    # Create lead with tracking disabled
                    with OdooUtils.odoo_context() as context:
                        lead_id = self.execute_kw('crm.lead', 'create', [lead_data], {'context': context})

                    all_created_leads.append(lead_id)

                    # Create realistic history and activities
                    self.create_realistic_lead_history(lead_id, lead_data, date_created, probability_data['stage_id'])
                    partner_id = self._create_partner_for_lead(lead_id, lead_data)
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
        """Generate appropriate creation date with weighting toward recency."""
        if index < total_count * 0.1:  # Oldest 10%
            return self.fake.date_time_between(start_date='-2y', end_date='-1y')
        elif index < total_count * 0.3:  # Next 20%
            return self.fake.date_time_between(start_date='-1y', end_date='-6m')
        elif index < total_count * 0.7:  # Middle 40%
            return self.fake.date_time_between(start_date='-6m', end_date='-1m')
        else:  # Most recent 30%
            return self.fake.date_time_between(start_date='-1m', end_date='now')


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Generate realistic CRM data in Odoo')
    parser.add_argument('--url', default='http://localhost:8069', help='Odoo URL')
    parser.add_argument('--db', default='crm_project', help='Database name')
    parser.add_argument('--username', default='admin', help='Username')
    parser.add_argument('--password', default='admin', help='Password')
    parser.add_argument('--count', type=int, default=100, help='Number of leads to generate')
    parser.add_argument('--csv', help='Path to CSV file with company data')

    args = parser.parse_args()

    logger.info(f"Connecting to Odoo at {args.url}")
    uid, models = OdooUtils.connect_to_odoo(args.url, args.db, args.username, args.password)

    if not uid or not models:
        logger.error("Failed to connect to Odoo")
        return

    logger.info("Connected to Odoo successfully")

    # Generate dummy leads
    generator = CrmDataGenerator(uid, models, args.db, args.password)
    generator.generate_leads(args.count, args.csv)


if __name__ == "__main__":
    main()