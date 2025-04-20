#!/usr/bin/env python3
import argparse
import xmlrpc.client
from faker import Faker
from datetime import datetime, timedelta, time as dt_time
import random
import logging
import sys
import time
import csv
import os
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def connect_to_odoo(url, db, username, password, max_retries=5):
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
                    logger.info(f"Retrying in 5 seconds... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(5)
                else:
                    return None, None
        except Exception as e:
            logger.error(f"Connection error: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in 5 seconds... (Attempt {attempt+1}/{max_retries})")
                time.sleep(5)
            else:
                return None, None

    return None, None

def setup_sales_teams(uid, models, db, password):
    """Create realistic sales teams structure"""
    try:
        logger.info("Setting up sales teams...")

        # Define sales teams
        teams = [
            {
                'name': 'Enterprise Sales',
                'description': 'Large enterprises and key accounts',
                'alias_name': 'enterprise',
                'invoiced_target': 1500000,
            },
            {
                'name': 'SMB Sales',
                'description': 'Small and medium businesses',
                'alias_name': 'smb',
                'invoiced_target': 800000,
            },
            {
                'name': 'Inside Sales',
                'description': 'Inbound leads and qualification',
                'alias_name': 'inside',
                'invoiced_target': 500000,
            },
            {
                'name': 'Partner Channel',
                'description': 'Partner-sourced opportunities',
                'alias_name': 'partners',
                'invoiced_target': 1200000,
            }
        ]

        team_ids = {}
        for team in teams:
            # Check if team already exists
            existing_team = models.execute_kw(db, uid, password, 'crm.team', 'search_read',
                [[['name', '=', team['name']]]], {'fields': ['id']})
            if existing_team:
                team_ids[team['name']] = existing_team[0]['id']
                logger.info(f"Team '{team['name']}' already exists with ID {team_ids[team['name']]}")
            else:
                team_id = models.execute_kw(db, uid, password, 'crm.team', 'create', [team])
                team_ids[team['name']] = team_id
                logger.info(f"Created team '{team['name']}' with ID {team_id}")

        return team_ids

    except Exception as e:
        logger.error(f"Error setting up sales teams: {e}")
        return {}

def setup_crm_tags(uid, models, db, password):
    """Set up realistic CRM tags for lead categorization"""
    try:
        logger.info("Setting up CRM tags...")

        # Industry tags
        industries = [
            'Technology', 'Healthcare', 'Finance', 'Manufacturing', 'Retail',
            'Education', 'Hospitality', 'Construction', 'Energy', 'Agriculture',
            'Transportation', 'Media', 'Professional Services', 'Government', 'Non-profit'
        ]

        # Lead source tags
        sources = [
            'Website', 'Event', 'Referral', 'Cold Call', 'Email Campaign',
            'Social Media', 'Webinar', 'Content Download', 'Partner', 'Paid Search',
            'Organic Search', 'Trade Show', 'Direct Mail'
        ]

        # Product interest tags
        interests = [
            'Core Product', 'Enterprise Package', 'Basic Plan', 'Premium Plan',
            'Add-on Services', 'Integration Services', 'Training', 'Consulting',
            'Maintenance Contract', 'Custom Development'
        ]

        tag_categories = {
            'Industry': industries,
            'Source': sources,
            'Product Interest': interests
        }

        tag_ids = defaultdict(list)

        for category, tags in tag_categories.items():
            for tag in tags:
                tag_name = f"{category}: {tag}"

                # Check if tag already exists
                existing_tag = models.execute_kw(db, uid, password, 'crm.tag', 'search_read',
                                            [[['name', '=', tag_name]]], {'fields': ['id']})

                if existing_tag:
                    tag_ids[category].append(existing_tag[0]['id'])
                else:
                    tag_id = models.execute_kw(db, uid, password, 'crm.tag', 'create', [{'name': tag_name}])
                    tag_ids[category].append(tag_id)

        logger.info(f"Created {sum(len(tags) for tags in tag_ids.values())} tags across {len(tag_ids)} categories")
        return tag_ids

    except Exception as e:
        logger.error(f"Error setting up CRM tags: {e}")
        return {}

def setup_user_roles(uid, models, db, password, team_ids):
    """Set up user roles and assign to sales teams"""
    try:
        logger.info("Setting up user roles...")

        # Get existing users
        existing_users = models.execute_kw(db, uid, password, 'res.users', 'search_read',
                                          [[]], {'fields': ['id', 'name', 'login']})

        # If we only have the admin user, create some additional users
        if len(existing_users) <= 1:
            sales_roles = [
                # Format: (name, login, team_name, is_manager)
                ("Alex Director", "sales.director@example.com", None, False),  # Sales Director
                ("Morgan Manager", "enterprise.manager@example.com", "Enterprise Sales", True),
                ("Sam Enterprise", "sam.enterprise@example.com", "Enterprise Sales", False),
                ("Taylor Enterprise", "taylor.enterprise@example.com", "Enterprise Sales", False),
                ("Jordan Manager", "smb.manager@example.com", "SMB Sales", True),
                ("Casey SMB", "casey.smb@example.com", "SMB Sales", False),
                ("Riley SMB", "riley.smb@example.com", "SMB Sales", False),
                ("Quinn Manager", "inside.manager@example.com", "Inside Sales", True),
                ("Harper Inside", "harper.inside@example.com", "Inside Sales", False),
                ("Cameron Inside", "cameron.inside@example.com", "Inside Sales", False),
                ("Tyler Manager", "partner.manager@example.com", "Partner Channel", True),
                ("Pat Partner", "pat.partner@example.com", "Partner Channel", False),
            ]

            user_mapping = {}
            for name, login, team_name, is_manager in sales_roles:
                # Create user
                user_vals = {
                    'name': name,
                    'login': login,
                    'password': 'demo123',  # Set a simple password for all demo users
                    'company_id': 1,        # Default company
                    'email': login,
                }

                # Check if user exists
                existing_user = models.execute_kw(db, uid, password, 'res.users', 'search_read',
                                              [[['login', '=', login]]], {'fields': ['id']})

                if existing_user:
                    user_id = existing_user[0]['id']
                    logger.info(f"User '{name}' already exists with ID {user_id}")
                else:
                    user_id = models.execute_kw(db, uid, password, 'res.users', 'create', [user_vals])
                    logger.info(f"Created user '{name}' with ID {user_id}")

                user_mapping[login] = {
                    'id': user_id,
                    'name': name,
                    'team': team_name,
                    'is_manager': is_manager
                }

            # Assign users to teams
            for login, user_data in user_mapping.items():
                if user_data['team'] and user_data['team'] in team_ids:
                    # Update team members
                    team_values = {'member_ids': [(4, user_data['id'])]}

                    # Set team leader if is_manager
                    if user_data['is_manager']:
                        team_values['user_id'] = user_data['id']

                    models.execute_kw(db, uid, password, 'crm.team', 'write', [
                        team_ids[user_data['team']], team_values
                    ])

                    logger.info(f"Added user '{user_data['name']}' to team '{user_data['team']}'")

            # Get updated user list
            existing_users = models.execute_kw(db, uid, password, 'res.users', 'search_read',
                                             [[]], {'fields': ['id', 'name', 'login']})

        return {user['id']: user for user in existing_users}

    except Exception as e:
        logger.error(f"Error setting up user roles: {e}")
        return {}

def load_company_data():
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
            # Generate companies with Faker as fallback
            fake = Faker()

            # Define industries manually
            industries = [
                'Technology', 'Healthcare', 'Finance', 'Manufacturing', 'Retail',
                'Education', 'Hospitality', 'Construction', 'Energy', 'Agriculture',
                'Transportation', 'Media', 'Professional Services', 'Government', 'Non-profit'
            ]

            for _ in range(100):
                companies.append({
                    'name': fake.company(),
                    'industry': random.choice(industries),
                    'size': random.choice(['1-10', '11-50', '51-200', '201-500', '501-1000', '1000+']),
                    'country': fake.country(),
                    'website': 'www.' + fake.domain_name()
                })
            logger.info("Generated 100 fake companies as sample data")
    except Exception as e:
        logger.error(f"Error loading company data: {e}")
        # Create a minimal set as fallback
        fake = Faker()
        industries = ['Technology', 'Healthcare', 'Finance', 'Manufacturing', 'Retail']
        for _ in range(50):
            companies.append({
                'name': fake.company(),
                'industry': random.choice(industries),
                'size': random.choice(['1-10', '11-50', '51-200', '201-500', '501-1000', '1000+']),
                'country': fake.country(),
                'website': 'www.' + fake.domain_name()
            })

    return companies

def add_stage_change_log(uid, models, db, password, lead_id, old_stage_name, new_stage_name, user_id, date):
    """Add a log note about stage change for analytics with correct historical timestamp"""
    try:
        message = f"Stage changed from '{old_stage_name}' to '{new_stage_name}'"
        message_with_tag = f"{message} #stage_change_log#"

        analytics_data = {
            "type": "stage_change",
            "old_stage": old_stage_name,
            "new_stage": new_stage_name,
            "timestamp": date.strftime('%Y-%m-%d %H:%M:%S'),
            "user_id": user_id
        }

        analytics_message = f"{message_with_tag}\n\n<!-- ANALYTICS_DATA: {str(analytics_data)} -->"

        # Create the log note with historical date
        values = {
            'body': analytics_message,
            'model': 'crm.lead',
            'res_id': lead_id,
            'author_id': user_id,
            'message_type': 'comment',
            'subtype_id': 1,  # mt_note
            'date': date.strftime('%Y-%m-%d %H:%M:%S')  # Set the historical date here
        }

        message_id = models.execute_kw(db, uid, password, 'mail.message', 'create', [values])
        return message_id

    except Exception as e:
        logger.error(f"Error adding stage change log: {e}")
        return False

def get_realistic_timeline(creation_date, now, stages, stage_index):
    """Generate realistic timeline for a lead based on its custom stage progression"""
    stage_names = [stage['name'].upper() for stage in stages]
    current_stage = stage_names[stage_index]

    # Expected days to close based on current stage
    if 'NEW' in current_stage:
        expected_days = random.randint(30, 60)  # New leads take 1-2 months
    elif 'COLD' in current_stage:
        expected_days = random.randint(45, 90)  # Cold leads take longer
    elif 'POTENTIAL' in current_stage:
        expected_days = random.randint(30, 60)  # Potential leads
    elif 'PUSH TO WARM' in current_stage:
        expected_days = random.randint(25, 50)  # Push to warm
    elif 'WARM' in current_stage:
        expected_days = random.randint(20, 45)  # Warm leads
    elif 'FOCUS' in current_stage:
        expected_days = random.randint(15, 30)  # Focus leads
    elif 'CONTRACT' in current_stage:
        expected_days = random.randint(7, 15)  # Send contract - close soon
    elif 'WON' in current_stage or 'LOST' in current_stage:
        expected_days = 0  # Already closed
        # Set a past date for close date
        days_ago = random.randint(1, 15)
        return now - timedelta(days=days_ago)
    else:
        # Default case
        expected_days = random.randint(15, 45)

    # Calculate expected closing date
    closing_date = now + timedelta(days=expected_days)

    return closing_date

def generate_dummy_leads(uid, models, db, password, count=100):
    """Generate realistic dummy leads/opportunities"""
    fake = Faker()
    now = datetime.now()

    try:
        # Set up sales teams
        team_ids = setup_sales_teams(uid, models, db, password)

        # Set up CRM tags
        tag_ids = setup_crm_tags(uid, models, db, password)

        # Get user information
        users = setup_user_roles(uid, models, db, password, team_ids)

        # Get CRM stages
        stages = models.execute_kw(db, uid, password, 'crm.stage', 'search_read', [[]], {'fields': ['id', 'name', 'sequence']})
        if not stages:
            logger.error("No CRM stages found. Ensure CRM module is properly installed.")
            return False

        # Log the available stages
        stage_names = [stage['name'] for stage in stages]
        logger.info(f"Found {len(stages)} stages: {', '.join(stage_names)}")

        # Sort stages by sequence
        stages.sort(key=lambda x: x['sequence'])
        stage_ids = [stage['id'] for stage in stages]
        stage_names = {stage['id']: stage['name'] for stage in stages}

        # Get activity types
        activity_types = models.execute_kw(db, uid, password, 'mail.activity.type', 'search_read', [[]], {'fields': ['id', 'name']})
        logger.info(f"Found {len(activity_types)} activity types")

        # Load realistic company data
        companies = load_company_data()

        # Get the note subtype ID for messages
        note_subtype_id = None
        try:
            note_subtype = models.execute_kw(db, uid, password, 'mail.message.subtype', 'search_read',
                                           [[['name', '=', 'Note']]], {'fields': ['id']})
            if note_subtype:
                note_subtype_id = note_subtype[0]['id']
            else:
                logger.warning("Note subtype not found, using default subtype ID 1")
                note_subtype_id = 1
        except Exception as e:
            logger.warning(f"Error getting note subtype ID: {e}")
            note_subtype_id = 1

        # Lead sources with weighted probabilities
        lead_sources = {
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
        source_weights = list(lead_sources.values())
        source_options = list(lead_sources.keys())

        # Stage weights for realistic distribution
        # Weights determine likelihood of a lead being in each stage
        stage_weights = {}
        for stage in stages:
            name = stage['name'].upper()
            if 'NEW' in name:
                stage_weights[stage['id']] = 25  # 25% new leads
            elif 'COLD' in name:
                stage_weights[stage['id']] = 15  # 15% cold leads
            elif 'POTENTIAL' in name:
                stage_weights[stage['id']] = 15  # 15% potential
            elif 'PUSH TO WARM' in name:
                stage_weights[stage['id']] = 10  # 10% push to warm
            elif 'WARM' in name:
                stage_weights[stage['id']] = 10  # 10% warm
            elif 'FOCUS' in name:
                stage_weights[stage['id']] = 8   # 8% focus
            elif 'CONTRACT' in name:
                stage_weights[stage['id']] = 7   # 7% contract
            elif 'WON' in name:
                stage_weights[stage['id']] = 5   # 5% won
            elif 'LOST' in name:
                stage_weights[stage['id']] = 5   # 5% lost
            else:
                stage_weights[stage['id']] = 10  # Default weight

        def generate_business_datetime(start_date, end_date):
            """Generate a datetime during business hours (9am-5pm) on weekdays only - optimized version"""
            # Get a random date - use faster random method instead of faker
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

            # Set to business hours (9am-5pm)
            business_start = dt_time(9, 0, 0)
            business_end = dt_time(17, 0, 0)

            # Random time during business hours
            random_hour = random.randint(business_start.hour, business_end.hour - 1)
            random_minute = random.choice([0, 15, 30, 45])  # Realistic meeting start times

            return random_date.replace(hour=random_hour, minute=random_minute, second=0)

        def create_lead_message(lead_id, body, author_id, message_date, subtype_id=None):
            """Create a message for a lead with specific historical date"""
            try:
                message_vals = {
                    'body': body,
                    'model': 'crm.lead',
                    'res_id': lead_id,
                    'author_id': author_id,
                    'message_type': 'comment',
                    'subtype_id': subtype_id or note_subtype_id,
                    'date': message_date.strftime('%Y-%m-%d %H:%M:%S')
                }

                message_id = models.execute_kw(db, uid, password, 'mail.message', 'create', [message_vals])
                return message_id
            except Exception as e:
                logger.error(f"Error creating lead message: {e}")
                return False

        def create_calendar_event(lead_id, event_name, start_datetime, duration_hours, user_id, partner_id=None):
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
                    'description': fake.paragraph(nb_sentences=2),
                }

                if partner_id:
                    event_vals['partner_ids'] = [(4, partner_id)]

                complete_context = {
                    'mail_auto_subscribe_no_notify': True,
                    'tracking_disable': True,
                    'mail_create_nosubscribe': True,
                    'mail_create_nolog': True
                }

                # Create the event with context to disable auto-messages
                event_id = models.execute_kw(db, uid, password, 'calendar.event', 'create', [event_vals],
                                            {'context': complete_context})

                # Add a message with the historical timestamp
                if start_datetime < datetime.now():
                    # Get user name for the message
                    user_name = "Administrator"
                    if user_id in users:
                        user_name = users[user_id].get('name', "Administrator")

                    # Calendar message with meeting details
                    message_body = f"<p>Meeting scheduled at '{start_datetime.strftime('%Y-%m-%d %H:%M:%S')}'<br/>Subject: {event_name}<br/>Duration: {duration_hours} hours</p>"

                    # Create message with historical timestamp
                    create_lead_message(
                        lead_id,
                        message_body,
                        user_id,
                        start_datetime - timedelta(days=random.randint(1, 5))  # Schedule a few days before
                    )

                return event_id
            except Exception as e:
                logger.error(f"Error creating calendar event: {e}")
                return False

        def add_custom_stage_change_message(lead_id, old_stage_id, new_stage_id, user_id, date, users_dict):
            """Add a user-friendly stage change message with historical timestamp"""
            try:
                old_stage_name = stage_names.get(old_stage_id, "Unknown")
                new_stage_name = stage_names.get(new_stage_id, "Unknown")

                # Get user name
                user_name = "Administrator"
                if user_id in users_dict:
                    user_name = users_dict[user_id].get('name', "Administrator")

                # Different message format based on stage transition
                if 'WON' in new_stage_name.upper():
                    message_body = f"<p>Opportunity won</p><p>Salesperson: {user_name}</p><p>Stage: {old_stage_name}<br/>{new_stage_name}</p>"
                elif 'LOST' in new_stage_name.upper():
                    message_body = f"<p>Opportunity lost</p><p>Salesperson: {user_name}</p><p>Stage: {old_stage_name}<br/>{new_stage_name}</p>"
                else:
                    message_body = f"<p>Stage changed</p><p>Salesperson: {user_name}</p><p>Stage: {new_stage_name}<br/>{old_stage_name}</p>"

                # Create message with historical timestamp
                message_id = create_lead_message(lead_id, message_body, user_id, date)
                return message_id
            except Exception as e:
                logger.error(f"Error adding custom stage change message: {e}")
                return False

        # Define probability patterns based on lead age and stage
        def get_probability_data(date_created, team_name=None):
            """Calculate probability and other metrics based on lead age and team - with logical stage progression"""
            lead_age = (now - date_created).days

            # Use weighted random selection for stage
            stage_ids_list = list(stage_weights.keys())
            weights = list(stage_weights.values())
            stage_id = random.choices(stage_ids_list, weights=weights, k=1)[0]
            stage_index = stage_ids.index(stage_id)
            stage_name = stage_names[stage_id].upper()

            # Override for very new leads
            if lead_age < 3 and random.random() < 0.8:
                # 80% chance of new leads being in the first or second stage
                stage_id = stage_ids[random.choices([0, 1], weights=[70, 30], k=1)[0]]
                stage_index = stage_ids.index(stage_id)
                stage_name = stage_names[stage_id].upper()

            # Force logical consistency: Prevent WON leads from becoming LOST and vice versa
            # WON and LOST are terminal states
            won_stage_id = None
            lost_stage_id = None

            # Find WON and LOST stage IDs
            for sid, sname in stage_names.items():
                if 'WON' in sname.upper():
                    won_stage_id = sid
                elif 'LOST' in sname.upper():
                    lost_stage_id = sid

            # If this is a WON or LOST lead, ensure it stays in the appropriate terminal state
            if 'WON' in stage_name and lost_stage_id and random.random() < 0.99:
                # 99% of the time, ensure won leads stay won and don't become lost
                if stage_id == lost_stage_id:
                    stage_id = won_stage_id
                    stage_index = stage_ids.index(stage_id)
                    stage_name = stage_names[stage_id].upper()

            # Assign probability based on stage for your custom stages
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
                # Default case
                probability = random.randint(10, 50)

            # Adjust expected revenue based on team
            if team_name == 'Enterprise Sales':
                base_revenue = random.randint(50000, 500000)
            elif team_name == 'SMB Sales':
                base_revenue = random.randint(10000, 75000)
            elif team_name == 'Partner Channel':
                base_revenue = random.randint(25000, 250000)
            else:  # Inside Sales or default
                base_revenue = random.randint(5000, 50000)

            # Adjust revenue based on stage (later stages have more accurate forecasts)
            stage_to_factor = {
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

            # Find the best matching stage factor
            best_match = None
            for key in stage_to_factor:
                if key in stage_name:
                    best_match = key
                    break

            revenue_factor = stage_to_factor.get(best_match, 0.7)
            expected_revenue = int(base_revenue * revenue_factor / 100) * 100  # Round to nearest 100

            return {
                'stage_id': stage_id,
                'stage_index': stage_index,
                'probability': probability,
                'expected_revenue': expected_revenue
            }

        def create_realistic_lead_history_improved(lead_id, lead_data, stage_sequence, users_dict, date_created, current_stage_id):
            """Create a realistic history of stage changes and messages for a lead with proper chronology"""
            try:
                # Add creation message with historical timestamp
                creation_msg = f"<p>Lead/Opportunity created</p>"
                create_lead_message(lead_id, creation_msg, lead_data.get('user_id', uid), date_created)

                # Add customer info message (slightly after creation)
                customer_msg = f"<p>Customer:<br/>{lead_data.get('partner_name', '')}, {lead_data.get('contact_name', '')}</p>"
                create_lead_message(
                    lead_id,
                    customer_msg,
                    lead_data.get('user_id', uid),
                    date_created + timedelta(minutes=random.randint(1, 5))
                )

                # Sort stages by sequence
                sorted_stages = sorted(stage_sequence, key=lambda s: s['sequence'])
                stage_ids = [stage['id'] for stage in sorted_stages]
                stage_names = {stage['id']: stage['name'] for stage in sorted_stages}

                # Find WON and LOST stages - they are terminal states
                won_stage_id = None
                lost_stage_id = None

                for sid, sname in stage_names.items():
                    if 'WON' in sname.upper():
                        won_stage_id = sid
                    elif 'LOST' in sname.upper():
                        lost_stage_id = sid

                # Determine how many stages this lead has gone through
                current_stage_index = stage_ids.index(current_stage_id)

                # Add historical stage changes if not in the first stage
                if current_stage_index > 0:
                    # Generate timestamps for stage transitions
                    now = datetime.now()
                    stage_dates = []

                    # Start with creation date
                    current_date = date_created + timedelta(hours=random.randint(2, 8))  # First change a few hours after creation

                    # Generate sequential stage transitions with reasonable time gaps
                    for i in range(current_stage_index):
                        from_stage_id = stage_ids[i]
                        to_stage_id = stage_ids[i+1]
                        from_stage_name = stage_names[from_stage_id].upper()
                        to_stage_name = stage_names[to_stage_id].upper()

                        # Skip invalid transitions
                        # If coming from WON/LOST, don't create this transition (they're terminal states)
                        if 'WON' in from_stage_name or 'LOST' in from_stage_name:
                            continue

                        # Add appropriate time between stages
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

                        # IMPORTANT: Ensure each date is strictly after the previous one
                        current_date = max(current_date + timedelta(days=days_to_add),
                                          stage_dates[-1] + timedelta(days=1) if stage_dates else current_date)

                        # Don't exceed current date
                        if current_date > now:
                            current_date = now - timedelta(hours=random.randint(1, 48))

                        # Add the date in strictly ascending order
                        stage_dates.append(current_date)

                    # Record stage transitions in the chatter with both technical and user-friendly messages
                    # Process in ascending date order
                    for i, stage_date in enumerate(stage_dates):
                        from_stage_id = stage_ids[i]
                        to_stage_id = stage_ids[i+1]

                        # Skip transitions from terminal states
                        from_stage_name = stage_names[from_stage_id].upper()
                        to_stage_name = stage_names[to_stage_id].upper()

                        if 'WON' in from_stage_name or 'LOST' in from_stage_name:
                            continue

                        # Choose appropriate user based on stage
                        if 'FOCUS' in to_stage_name or 'CONTRACT' in to_stage_name:
                            # More senior reps/managers handle later stages
                            manager_users = [uid for uid, user in users_dict.items()
                                          if 'Manager' in user.get('name', '') or 'Director' in user.get('name', '')]
                            if manager_users:
                                assignee = random.choice(manager_users)
                            else:
                                assignee = random.choice(list(users_dict.keys()))
                        else:
                            assignee = random.choice(list(users_dict.keys()))

                        # Add the technical stage change log (with #stage_change_log# tag)
                        add_stage_change_log(
                            uid, models, db, password,
                            lead_id,
                            stage_names[from_stage_id],
                            stage_names[to_stage_id],
                            assignee,
                            stage_date
                        )

                        # Add user-friendly stage change message with proper timestamp
                        add_custom_stage_change_message(
                            lead_id,
                            from_stage_id,
                            to_stage_id,
                            assignee,
                            stage_date + timedelta(seconds=30),  # Slightly after the technical log
                            users_dict
                        )

                        # Update the lead with the stage change - except for the final transition
                        if i == len(stage_dates) - 1:  # Skip the last one as the lead is already at this stage
                            continue

                        # Write the stage change to create historical data with all notifications disabled
                        complete_context = {
                            'mail_auto_subscribe_no_notify': True,
                            'tracking_disable': True,
                            'mail_create_nosubscribe': True,
                            'mail_create_nolog': True
                        }

                        models.execute_kw(db, uid, password, 'crm.lead', 'write', [
                            lead_id,
                            {
                                'stage_id': to_stage_id,
                                'user_id': assignee
                            }
                        ], {'context': complete_context})

                return True

            except Exception as e:
                logger.error(f"Error creating improved lead history for lead {lead_id}: {e}")
                return False

        def fix_timestamp_ordering():
            """Fix the order of the lead history by updating message timestamps in the database"""
            try:
                logger.info("Fixing message timestamps for consistent history...")

                # Get all leads created
                leads = models.execute_kw(db, uid, password, 'crm.lead', 'search', [[]])

                for lead_id in leads:
                    # Get messages for this lead
                    lead_messages = models.execute_kw(db, uid, password, 'mail.message', 'search_read',
                                                  [[['model', '=', 'crm.lead'], ['res_id', '=', lead_id]]],
                                                  {'fields': ['id', 'date', 'body', 'subject'], 'order': 'date asc'})

                    # Find creation and customer messages
                    creation_msgs = [m for m in lead_messages if 'Lead/Opportunity created' in m.get('body', '')]
                    customer_msgs = [m for m in lead_messages if 'Customer:' in m.get('body', '')]
                    stage_msgs = [m for m in lead_messages if '#stage_change_log#' in m.get('body', '') or 'Stage changed' in m.get('body', '')]

                    # Get lead create date
                    lead_data = models.execute_kw(db, uid, password, 'crm.lead', 'read', [lead_id], {'fields': ['create_date']})

                    if lead_data and lead_data[0].get('create_date'):
                        create_date = lead_data[0]['create_date']
                        base_date = datetime.strptime(create_date.split('.')[0], '%Y-%m-%d %H:%M:%S')

                        # Fix creation message timestamps if needed
                        if creation_msgs:
                            for msg in creation_msgs:
                                # Set creation message exactly at lead creation time
                                models.execute_kw(db, uid, password, 'mail.message', 'write',
                                              [msg['id'], {'date': create_date}])

                        # Fix customer messages timestamps
                        if customer_msgs:
                            for i, msg in enumerate(customer_msgs):
                                # Set customer message timestamp slightly after creation
                                customer_date = base_date + timedelta(minutes=1+i)
                                models.execute_kw(db, uid, password, 'mail.message', 'write',
                                              [msg['id'], {'date': customer_date.strftime('%Y-%m-%d %H:%M:%S')}])

                        # Parse and fix stage change message timestamps to ensure proper sequence
                        if stage_msgs:
                            # Group stage messages by the stage transition they represent
                            stage_transitions = {}
                            for msg in stage_msgs:
                                # Extract stage information from message body
                                if '#stage_change_log#' in msg.get('body', ''):
                                    # Technical log message
                                    # Extract stage names from "Stage changed from 'X' to 'Y' #stage_change_log#"
                                    import re
                                    match = re.search(r"Stage changed from '([^']+)' to '([^']+)'", msg.get('body', ''))
                                    if match:
                                        from_stage, to_stage = match.groups()
                                        key = f"{from_stage} -> {to_stage}"
                                        if key not in stage_transitions:
                                            stage_transitions[key] = []
                                        stage_transitions[key].append(msg)
                                elif 'Stage changed' in msg.get('body', ''):
                                    # User-friendly stage message
                                    import re
                                    # Extract stage names from the message content
                                    match = re.search(r"Stage:([^<]+)<br/>([^<]+)", msg.get('body', ''))
                                    if match:
                                        from_stage, to_stage = match.groups()
                                        from_stage = from_stage.strip()
                                        to_stage = to_stage.strip()
                                        key = f"{from_stage} -> {to_stage}"
                                        if key not in stage_transitions:
                                            stage_transitions[key] = []
                                        stage_transitions[key].append(msg)

                            # Sort the transitions in logical sequence
                            # This would require knowing the stage sequence, but we can use timestamps
                            sorted_transitions = sorted(stage_transitions.items(),
                                                     key=lambda x: min(datetime.strptime(m['date'].split('.')[0], '%Y-%m-%d %H:%M:%S')
                                                                     for m in x[1]) if x[1] else base_date)

                            # Reassign timestamps to ensure proper sequence, starting 1 day after lead creation
                            current_time = base_date + timedelta(days=1)
                            for transition, messages in sorted_transitions:
                                for msg in sorted(messages, key=lambda m: m['id']):
                                    models.execute_kw(db, uid, password, 'mail.message', 'write',
                                                  [msg['id'], {'date': current_time.strftime('%Y-%m-%d %H:%M:%S')}])
                                    current_time += timedelta(minutes=15)  # Space messages by 15 minutes

                logger.info("Message timestamp fixing completed")

            except Exception as e:
                logger.error(f"Error fixing message timestamps: {e}")

        # Generate leads
        logger.info(f"Generating {count} leads/opportunities...")
        created_count = 0
        all_created_leads = []

        for i in range(count):
            # Choose a company and assign team based on company size
            company = random.choice(companies)

            # Assign sales team based on company size
            team_name = None
            if 'size' in company:
                if company['size'] in ['501-1000', '1000+']:
                    team_name = 'Enterprise Sales'
                elif company['size'] in ['51-200', '201-500']:
                    team_name = 'SMB Sales' if random.random() < 0.7 else 'Partner Channel'
                else:  # Small companies
                    team_name = 'Inside Sales' if random.random() < 0.8 else 'SMB Sales'

            # Fallback if team name wasn't assigned or team doesn't exist
            if not team_name or team_name not in team_ids:
                team_name = random.choice(list(team_ids.keys())) if team_ids else None

            team_id = team_ids.get(team_name) if team_name else False

            # Choose salesperson from team
            user_id = None
            if team_id:
                team_read = models.execute_kw(
                    db, uid, password, 'crm.team', 'read',
                    [team_id], {'fields': ['member_ids']}
                )
                if team_read and team_read[0]['member_ids']:
                    user_id = random.choice(team_read[0]['member_ids'])

            # Fallback to any user if no team members
            if not user_id and users:
                user_id = random.choice(list(users.keys()))
            else:
                # Fallback to admin if no users
                user_id = uid

            # Random dates weighted towards recent
            if i < count * 0.1:  # 10% very old leads
                date_created = fake.date_time_between(start_date='-2y', end_date='-1y')
            elif i < count * 0.3:  # 20% older leads
                date_created = fake.date_time_between(start_date='-1y', end_date='-6m')
            elif i < count * 0.7:  # 40% medium age
                date_created = fake.date_time_between(start_date='-6m', end_date='-1m')
            else:  # 30% recent leads
                date_created = fake.date_time_between(start_date='-1m', end_date='now')

            # Get probability and related data based on creation date and team
            probability_data = get_probability_data(date_created, team_name)

            # Generate expected closing date based on stage and creation date
            expected_closing = get_realistic_timeline(
                date_created, now, stages, probability_data['stage_index']
            )

            # Determine lead source with weighted random selection
            lead_source = random.choices(source_options, weights=source_weights, k=1)[0]

            # Select tags
            selected_tags = []

            # Always select an industry tag
            if 'Industry' in tag_ids and tag_ids['Industry']:
                industry_tag = random.choice(tag_ids['Industry'])
                selected_tags.append(industry_tag)

            # Always select a source tag matching the lead source
            if 'Source' in tag_ids and tag_ids['Source']:
                matching_source_tags = []
                for tag_id in tag_ids['Source']:
                    tag_name = models.execute_kw(
                        db, uid, password, 'crm.tag', 'read',
                        [tag_id], {'fields': ['name']}
                    )[0]['name']
                    if lead_source in tag_name:
                        matching_source_tags.append(tag_id)

                if matching_source_tags:
                    selected_tags.append(matching_source_tags[0])
                elif tag_ids['Source']:
                    # Fallback to random source tag
                    selected_tags.append(random.choice(tag_ids['Source']))

            # Possibly select product interest (70% chance)
            if 'Product Interest' in tag_ids and tag_ids['Product Interest'] and random.random() < 0.7:
                product_tag = random.choice(tag_ids['Product Interest'])
                selected_tags.append(product_tag)

            # Create lead/opportunity
            contact_name = fake.name()
            email_domain = company['website'].replace('www.', '') if 'website' in company else fake.domain_name()

            # Determine type based on stage (first stage is lead, others are opportunities)
            stage_name = stage_names[probability_data['stage_id']].upper()
            lead_type = 'lead' if 'NEW' in stage_name or 'COLD' in stage_name else 'opportunity'

            # Add priority (star rating) - weighted toward normal priority
            priority_weights = [70, 20, 10]  # 0=Normal, 1=Medium, 2=High
            priority = random.choices([0, 1, 2], weights=priority_weights, k=1)[0]

            # For stages like FOCUS or CONTRACT, increase likelihood of high priority
            if 'FOCUS' in stage_name or 'CONTRACT' in stage_name:
                priority_weights = [20, 30, 50]  # More likely to be high priority
                priority = random.choices([0, 1, 2], weights=priority_weights, k=1)[0]

            # Prepare country ID (if it exists)
            country_id = False
            if 'country' in company:
                country_search = models.execute_kw(
                    db, uid, password, 'res.country', 'search',
                    [[['name', 'ilike', company['country']]]]
                )
                if country_search:
                    country_id = country_search[0]

            lead_data = {
                'name': f"{company.get('name', 'Unknown')} - {fake.catch_phrase()} Project",
                'partner_name': company.get('name', fake.company()),
                'contact_name': contact_name,
                'function': fake.job(),
                'email_from': f"{contact_name.split()[0].lower()}.{contact_name.split()[-1].lower()}@{email_domain}",
                'phone': fake.phone_number(),
                'user_id': user_id,
                'team_id': team_id,
                'stage_id': probability_data['stage_id'],
                'type': lead_type,
                'probability': probability_data['probability'],
                'expected_revenue': probability_data['expected_revenue'],
                'date_deadline': expected_closing.strftime('%Y-%m-%d'),
                'description': fake.paragraph(nb_sentences=5),
                'priority': str(priority),
                'tag_ids': [(6, 0, selected_tags)] if selected_tags else False,
                'referred': lead_source == 'Referral',
                'country_id': country_id,
            }

            # Filter out any False values that might cause XML-RPC errors
            lead_data = {k: v for k, v in lead_data.items() if v is not None and v is not False}

            try:

 # Create the lead with full tracking disabled to prevent auto-messages
                complete_context = {
                    'mail_auto_subscribe_no_notify': True,
                    'tracking_disable': True,
                    'mail_create_nosubscribe': True,
                    'mail_create_nolog': True,  # Critical for preventing creation logs
                }

                lead_id = models.execute_kw(
                    db, uid, password, 'crm.lead', 'create', [lead_data],
                    {'context': complete_context}
                )

                all_created_leads.append(lead_id)

                # Create improved lead history with proper timestamps BEFORE creating partner
                # to prevent auto-messages from partner linking
                create_realistic_lead_history_improved(lead_id, lead_data, stages, users, date_created, probability_data['stage_id'])

                # Create partner record if needed
                partner_id = False
                try:
                    # Create partner for the contact (with tracking disabled)
                    partner_data = {
                        'name': lead_data['contact_name'],
                        'email': lead_data['email_from'],
                        'phone': lead_data.get('phone', ''),
                        'company_type': 'person',
                        'company_name': lead_data['partner_name'],
                        'function': lead_data.get('function', ''),
                        'country_id': lead_data.get('country_id', False)
                    }

                    partner_id = models.execute_kw(
                        db, uid, password, 'res.partner', 'create', [partner_data],
                        {'context': complete_context}
                    )

                    # Link partner to lead (with tracking disabled)
                    models.execute_kw(
                        db, uid, password, 'crm.lead', 'write',
                        [lead_id, {'partner_id': partner_id}],
                        {'context': complete_context}
                    )

                except Exception as e:
                    logger.warning(f"Could not create partner for lead {lead_id}: {e}")

                # Add activities based on stage
                stage_name = stage_names[probability_data['stage_id']].upper()

                # Skip activity creation for WON/LOST deals
                if 'WON' not in stage_name and 'LOST' not in stage_name:
                    # Define activity sequence based on stage
                    activity_sequence = []

                    if 'NEW' in stage_name or 'COLD' in stage_name:
                        # New/Cold leads: Initial outreach
                        activity_sequence = [
                            {'type': 'email', 'name': 'Initial Contact Email', 'days_offset': random.randint(1, 3), 'duration': 0.5},
                            {'type': 'call', 'name': 'Follow-up Call', 'days_offset': random.randint(4, 7), 'duration': 0.5}
                        ]
                    elif 'POTENTIAL' in stage_name or 'PUSH TO WARM' in stage_name:
                        activity_sequence = [
                            {'type': 'email', 'name': 'Qualification Email', 'days_offset': random.randint(1, 2), 'duration': 0.5},
                            {'type': 'call', 'name': 'Discovery Call', 'days_offset': random.randint(3, 5), 'duration': 1},
                            {'type': 'meeting', 'name': 'Initial Meeting', 'days_offset': random.randint(7, 14), 'duration': 1}
                        ]
                    elif 'WARM' in stage_name:
                        # Warm leads: Demo and technical discussions
                        activity_sequence = [
                            {'type': 'call', 'name': 'Needs Assessment Call', 'days_offset': random.randint(1, 3), 'duration': 1},
                            {'type': 'meeting', 'name': 'Product Demo', 'days_offset': random.randint(5, 10), 'duration': 1.5},
                            {'type': 'meeting', 'name': 'Technical Discussion', 'days_offset': random.randint(12, 18), 'duration': 2},
                            {'type': 'email', 'name': 'Follow-up Materials', 'days_offset': random.randint(13, 20), 'duration': 0.5}
                        ]
                    elif 'FOCUS' in stage_name:
                        # Focus leads: Multiple stakeholder meetings
                        activity_sequence = [
                            {'type': 'call', 'name': 'Stakeholder Introduction', 'days_offset': random.randint(1, 3), 'duration': 1},
                            {'type': 'meeting', 'name': 'Decision Maker Meeting', 'days_offset': random.randint(5, 10), 'duration': 1.5},
                            {'type': 'meeting', 'name': 'Technical Deep Dive', 'days_offset': random.randint(7, 14), 'duration': 2},
                            {'type': 'meeting', 'name': 'Solution Presentation', 'days_offset': random.randint(15, 21), 'duration': 2},
                            {'type': 'email', 'name': 'Proposal Submission', 'days_offset': random.randint(16, 23), 'duration': 1}
                        ]
                    elif 'CONTRACT' in stage_name:
                        # Contract stage: Negotiations
                        activity_sequence = [
                            {'type': 'email', 'name': 'Contract Draft Sent', 'days_offset': random.randint(1, 2), 'duration': 1},
                            {'type': 'call', 'name': 'Contract Review Call', 'days_offset': random.randint(3, 5), 'duration': 1},
                            {'type': 'meeting', 'name': 'Negotiation Meeting', 'days_offset': random.randint(7, 10), 'duration': 2},
                            {'type': 'meeting', 'name': 'Final Terms Discussion', 'days_offset': random.randint(12, 15), 'duration': 1.5}
                        ]

                    # Randomly choose which activities to actually create (for variety)
                    if activity_sequence:
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
                        business_datetime = generate_business_datetime(
                            activity_date,
                            activity_date + timedelta(days=1)
                        )

                        # Skip if too far in the future
                        if business_datetime > now + timedelta(days=30):
                            continue

                        # For meeting activities, create calendar events
                        if activity['type'] == 'meeting':
                            # Find meeting activity type
                            meeting_activity_types = [a for a in activity_types if 'meeting' in a['name'].lower()]
                            if meeting_activity_types:
                                activity_type_id = random.choice(meeting_activity_types)['id']

                                # Create activity record - only use fields that exist in the model
                                activity_values = {
                                    'res_id': lead_id,
                                    'res_model_id': models.execute_kw(db, uid, password, 'ir.model', 'search',
                                                              [[['model', '=', 'crm.lead']]])[0],
                                    'activity_type_id': activity_type_id,
                                    'summary': activity['name'],
                                    'note': fake.paragraph(nb_sentences=2),
                                    'date_deadline': business_datetime.strftime('%Y-%m-%d'),
                                    'user_id': user_id,
                                }

                                # Create the activity with tracking disabled
                                activity_id = models.execute_kw(
                                    db, uid, password, 'mail.activity', 'create', [activity_values],
                                    {'context': complete_context}
                                )

                                # Mark as done if in the past
                                if business_datetime < now:
                                    try:
                                        # Use action_done but with a custom message afterward
                                        models.execute_kw(db, uid, password, 'mail.activity', 'action_done', [activity_id])

                                        # Add a message with historical timestamp manually
                                        user_name = users.get(user_id, {}).get('name', "Administrator")
                                        activity_done_msg = f"<p>{activity['name']} done (originally assigned to {user_name})</p><p>Original note:<br/>{activity_values['note']}</p>"

                                        # Create historical message about completed activity
                                        create_lead_message(
                                            lead_id,
                                            activity_done_msg,
                                            user_id,
                                            business_datetime
                                        )

                                        # Create a calendar event for the meeting with historical date
                                        create_calendar_event(
                                            lead_id,
                                            activity['name'],
                                            business_datetime,
                                            activity['duration'],
                                            user_id,
                                            partner_id
                                        )

                                    except Exception as e:
                                        logger.error(f"Error handling activity completion: {e}")
                                        # If action_done fails, try unlink as fallback
                                        try:
                                            models.execute_kw(db, uid, password, 'mail.activity', 'unlink', [activity_id])
                                        except:
                                            pass
                                elif business_datetime > now and business_datetime < now + timedelta(days=14):
                                    # Create upcoming calendar event for near-future meetings
                                    create_calendar_event(
                                        lead_id,
                                        activity['name'],
                                        business_datetime,
                                        activity['duration'],
                                        user_id,
                                        partner_id
                                    )
                        elif activity['type'] in ['call', 'email']:
                            # For calls and emails just create activities
                            call_email_types = [a for a in activity_types if activity['type'] in a['name'].lower()]
                            if call_email_types:
                                activity_type_id = random.choice(call_email_types)['id']

                                activity_values = {
                                    'res_id': lead_id,
                                    'res_model_id': models.execute_kw(db, uid, password, 'ir.model', 'search',
                                                              [[['model', '=', 'crm.lead']]])[0],
                                    'activity_type_id': activity_type_id,
                                    'summary': activity['name'],
                                    'note': fake.paragraph(nb_sentences=2),
                                    'date_deadline': business_datetime.strftime('%Y-%m-%d'),
                                    'user_id': user_id,
                                }

                                # Create with tracking disabled
                                activity_id = models.execute_kw(
                                    db, uid, password, 'mail.activity', 'create', [activity_values],
                                    {'context': complete_context}
                                )

                                # Mark as done if in the past
                                if business_datetime < now:
                                    try:
                                        # Use action_done
                                        models.execute_kw(db, uid, password, 'mail.activity', 'action_done', [activity_id])

                                        # Add a message with historical timestamp manually
                                        user_name = users.get(user_id, {}).get('name', "Administrator")
                                        activity_done_msg = f"<p>{activity['name']} done (originally assigned to {user_name})</p><p>Original note:<br/>{activity_values['note']}</p>"

                                        # Create historical message about completed activity
                                        create_lead_message(
                                            lead_id,
                                            activity_done_msg,
                                            user_id,
                                            business_datetime
                                        )
                                    except Exception as e:
                                        logger.error(f"Error marking activity as done: {e}")
                                        # If action_done fails, try unlink
                                        try:
                                            models.execute_kw(db, uid, password, 'mail.activity', 'unlink', [activity_id])
                                        except:
                                            pass

                created_count += 1
                if created_count % 10 == 0:
                    logger.info(f"Created {created_count} leads so far...")

            except Exception as e:
                logger.error(f"Error creating lead {i+1}: {e}")

        # Final step: fix any remaining timestamp issues
        if all_created_leads:
            try:
                fix_timestamp_ordering()
            except Exception as e:
                logger.error(f"Error during final timestamp fixing: {e}")

        logger.info(f"Successfully created {created_count} realistic leads/opportunities")
        return True

    except Exception as e:
        logger.error(f"Error generating dummy data: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Generate realistic CRM data in Odoo')
    parser.add_argument('--url', default='http://localhost:8069', help='Odoo URL')
    parser.add_argument('--db', default='crm_project', help='Database name')
    parser.add_argument('--username', default='admin', help='Username')
    parser.add_argument('--password', default='admin', help='Password')
    parser.add_argument('--count', type=int, default=100, help='Number of leads to generate')

    args = parser.parse_args()

    logger.info(f"Connecting to Odoo at {args.url}")
    uid, models = connect_to_odoo(args.url, args.db, args.username, args.password)

    if not uid or not models:
        logger.error("Failed to connect to Odoo")
        return

    logger.info("Connected to Odoo successfully")

    # Generate dummy leads
    generate_dummy_leads(uid, models, args.db, args.password, args.count)

if __name__ == "__main__":
    main()
