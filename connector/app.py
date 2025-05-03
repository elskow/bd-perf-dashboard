#!/usr/bin/env python3

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, Response
import xmlrpc.client
from functools import wraps
import pandas as pd
from werkzeug.serving import run_simple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Constants
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds

# Environment variables for configuration (can be set in .env file)
ODOO_URL = os.environ.get('ODOO_URL', 'http://localhost:8069')
ODOO_DB = os.environ.get('ODOO_DB', 'crm_project')
ODOO_USERNAME = os.environ.get('ODOO_USERNAME', 'admin')
ODOO_PASSWORD = os.environ.get('ODOO_PASSWORD', 'admin')
API_KEY = os.environ.get('API_KEY', 'your-secure-api-key')  # Add this for API security

# Global connection objects
odoo_uid = None
odoo_models = None


def require_api_key(f):
    """Decorator to require API key for endpoints"""
    @wraps(f)
    def decorated(*args, **kwargs):
        provided_key = request.headers.get('X-API-Key')
        if provided_key != API_KEY:
            return jsonify({"error": "Unauthorized access. Invalid API key."}), 401
        return f(*args, **kwargs)
    return decorated


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
                import time
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


@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint to check if the API is running and can connect to Odoo"""
    uid, _ = connect_to_odoo()
    if uid:
        return jsonify({
            "status": "healthy",
            "odoo_connected": True,
            "timestamp": datetime.now().isoformat()
        })
    else:
        return jsonify({
            "status": "unhealthy",
            "odoo_connected": False,
            "error": "Could not connect to Odoo",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/leads', methods=['GET'])
@require_api_key
def get_leads():
    """Get CRM leads with optional filtering"""
    try:
        # Process query parameters
        limit = request.args.get('limit', default=100, type=int)
        offset = request.args.get('offset', default=0, type=int)
        stage = request.args.get('stage', default=None)
        team = request.args.get('team', default=None)
        user = request.args.get('user', default=None)

        # Build domain filter
        domain = []
        if stage:
            domain.append(('stage_id.name', 'ilike', stage))
        if team:
            domain.append(('team_id.name', 'ilike', team))
        if user:
            domain.append(('user_id.name', 'ilike', user))

        # Get leads count for pagination
        total_count = execute_kw('crm.lead', 'search_count', [domain])

        # Define fields to fetch
        fields = [
            'id', 'name', 'partner_name', 'contact_name', 'email_from',
            'phone', 'user_id', 'team_id', 'stage_id', 'type',
            'probability', 'expected_revenue', 'date_deadline',
            'create_date', 'write_date', 'tag_ids', 'priority'
        ]

        # Get leads
        leads = execute_kw(
            'crm.lead', 'search_read',
            [domain],
            {
                'fields': fields,
                'limit': limit,
                'offset': offset,
                'order': 'create_date desc'
            }
        )

        if leads is None:
            return jsonify({"error": "Failed to retrieve leads from Odoo"}), 500

        # Resolve related fields
        for lead in leads:
            if lead.get('user_id'):
                lead['user_id'] = {
                    'id': lead['user_id'][0],
                    'name': lead['user_id'][1]
                }
            if lead.get('team_id'):
                lead['team_id'] = {
                    'id': lead['team_id'][0],
                    'name': lead['team_id'][1]
                }
            if lead.get('stage_id'):
                lead['stage_id'] = {
                    'id': lead['stage_id'][0],
                    'name': lead['stage_id'][1]
                }

            # Resolve tags
            if lead.get('tag_ids'):
                tag_data = execute_kw('crm.tag', 'read', [lead['tag_ids']], {'fields': ['name']})
                lead['tags'] = [tag['name'] for tag in tag_data] if tag_data else []

        # Add pagination info
        result = {
            "count": total_count,
            "limit": limit,
            "offset": offset,
            "data": leads
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error retrieving leads: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/api/leads/csv', methods=['GET'])
@require_api_key
def get_leads_csv():
    """Get CRM leads as CSV for direct Power BI import"""
    try:
        # Process query parameters - similar to get_leads
        limit = request.args.get('limit', default=1000, type=int)
        offset = request.args.get('offset', default=0, type=int)
        stage = request.args.get('stage', default=None)
        team = request.args.get('team', default=None)
        user = request.args.get('user', default=None)

        # Build domain filter
        domain = []
        if stage:
            domain.append(('stage_id.name', 'ilike', stage))
        if team:
            domain.append(('team_id.name', 'ilike', team))
        if user:
            domain.append(('user_id.name', 'ilike', user))

        # Define fields to fetch
        fields = [
            'id', 'name', 'partner_name', 'contact_name', 'email_from',
            'phone', 'user_id', 'team_id', 'stage_id', 'type',
            'probability', 'expected_revenue', 'date_deadline',
            'create_date', 'write_date', 'priority'
        ]

        # Get leads
        leads = execute_kw(
            'crm.lead', 'search_read',
            [domain],
            {
                'fields': fields,
                'limit': limit,
                'offset': offset,
                'order': 'create_date desc'
            }
        )

        if leads is None:
            return jsonify({"error": "Failed to retrieve leads from Odoo"}), 500

        # Process data for CSV
        processed_data = []
        for lead in leads:
            lead_data = {
                'id': lead['id'],
                'name': lead['name'],
                'partner_name': lead['partner_name'],
                'contact_name': lead['contact_name'],
                'email': lead['email_from'],
                'phone': lead['phone'],
                'user_name': lead['user_id'][1] if lead.get('user_id') else None,
                'team_name': lead['team_id'][1] if lead.get('team_id') else None,
                'stage_name': lead['stage_id'][1] if lead.get('stage_id') else None,
                'type': lead['type'],
                'probability': lead['probability'],
                'expected_revenue': lead['expected_revenue'],
                'date_deadline': lead['date_deadline'],
                'create_date': lead['create_date'],
                'write_date': lead['write_date'],
                'priority': lead['priority']
            }
            processed_data.append(lead_data)

        if not processed_data:
            return jsonify({"error": "No data found"}), 404

        # Convert to DataFrame and then to CSV
        df = pd.DataFrame(processed_data)
        csv_data = df.to_csv(index=False)

        # Create response with CSV data
        response = Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=crm_leads.csv"}
        )
        return response

    except Exception as e:
        logger.error(f"Error retrieving leads as CSV: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/api/meetings', methods=['GET'])
@require_api_key
def get_meetings():
    """Get calendar meetings related to opportunities"""
    try:
        # Process query parameters
        limit = request.args.get('limit', default=100, type=int)
        offset = request.args.get('offset', default=0, type=int)
        user = request.args.get('user', default=None)
        opportunity_id = request.args.get('opportunity_id', default=None)

        # Build domain filter
        domain = [('opportunity_id', '!=', False)]  # Only meetings related to opportunities
        if user:
            domain.append(('user_id.name', 'ilike', user))
        if opportunity_id:
            domain.append(('opportunity_id', '=', int(opportunity_id)))

        # Get total count for pagination
        total_count = execute_kw('calendar.event', 'search_count', [domain])

        # Define fields to fetch
        fields = [
            'id', 'name', 'start', 'stop', 'duration', 'user_id',
            'opportunity_id', 'location', 'description'
        ]

        # Get meetings
        meetings = execute_kw(
            'calendar.event', 'search_read',
            [domain],
            {
                'fields': fields,
                'limit': limit,
                'offset': offset,
                'order': 'start desc'
            }
        )

        if meetings is None:
            return jsonify({"error": "Failed to retrieve meetings from Odoo"}), 500

        # Resolve related fields
        for meeting in meetings:
            if meeting.get('user_id'):
                meeting['user_id'] = {
                    'id': meeting['user_id'][0],
                    'name': meeting['user_id'][1]
                }
            if meeting.get('opportunity_id'):
                # Get opportunity details
                opp_id = meeting['opportunity_id'][0]
                opp_data = execute_kw('crm.lead', 'read', [[opp_id]], {'fields': ['name', 'partner_name', 'stage_id']})
                if opp_data:
                    meeting['opportunity_id'] = {
                        'id': opp_id,
                        'name': opp_data[0]['name'],
                        'partner_name': opp_data[0]['partner_name'],
                        'stage_id': opp_data[0]['stage_id'][1] if opp_data[0].get('stage_id') else None
                    }

        # Add pagination info
        result = {
            "count": total_count,
            "limit": limit,
            "offset": offset,
            "data": meetings
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error retrieving meetings: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/api/meetings/csv', methods=['GET'])
@require_api_key
def get_meetings_csv():
    """Get calendar meetings as CSV for direct Power BI import"""
    try:
        # Process query parameters
        limit = request.args.get('limit', default=1000, type=int)
        offset = request.args.get('offset', default=0, type=int)
        user = request.args.get('user', default=None)

        # Build domain filter
        domain = [('opportunity_id', '!=', False)]  # Only meetings related to opportunities
        if user:
            domain.append(('user_id.name', 'ilike', user))

        # Define fields to fetch
        fields = [
            'id', 'name', 'start', 'stop', 'duration', 'user_id',
            'opportunity_id', 'location', 'description'
        ]

        # Get meetings
        meetings = execute_kw(
            'calendar.event', 'search_read',
            [domain],
            {
                'fields': fields,
                'limit': limit,
                'offset': offset,
                'order': 'start desc'
            }
        )

        if meetings is None:
            return jsonify({"error": "Failed to retrieve meetings from Odoo"}), 500

        # Process data for CSV
        processed_data = []
        for meeting in meetings:
            # Get opportunity details
            opp_id = meeting['opportunity_id'][0]
            opp_data = execute_kw('crm.lead', 'read', [[opp_id]],
                                {'fields': ['name', 'partner_name', 'stage_id', 'team_id', 'expected_revenue']})

            meeting_data = {
                'id': meeting['id'],
                'name': meeting['name'],
                'start_datetime': meeting['start'],
                'end_datetime': meeting['stop'],
                'duration': meeting['duration'],
                'user_name': meeting['user_id'][1] if meeting.get('user_id') else None,
                'opportunity_id': opp_id,
                'opportunity_name': opp_data[0]['name'] if opp_data else None,
                'partner_name': opp_data[0]['partner_name'] if opp_data else None,
                'stage_name': opp_data[0]['stage_id'][1] if opp_data and opp_data[0].get('stage_id') else None,
                'team_name': opp_data[0]['team_id'][1] if opp_data and opp_data[0].get('team_id') else None,
                'expected_revenue': opp_data[0]['expected_revenue'] if opp_data else None,
                'location': meeting.get('location', ''),
            }
            processed_data.append(meeting_data)

        if not processed_data:
            return jsonify({"error": "No data found"}), 404

        # Convert to DataFrame and then to CSV
        df = pd.DataFrame(processed_data)
        csv_data = df.to_csv(index=False)

        # Create response with CSV data
        response = Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=crm_meetings.csv"}
        )
        return response

    except Exception as e:
        logger.error(f"Error retrieving meetings as CSV: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/api/salesteams', methods=['GET'])
@require_api_key
def get_sales_teams():
    """Get sales teams data"""
    try:
        teams = execute_kw(
            'crm.team', 'search_read',
            [[]],
            {'fields': ['id', 'name', 'user_id', 'member_ids']}
        )

        if teams is None:
            return jsonify({"error": "Failed to retrieve sales teams from Odoo"}), 500

        # Resolve members for each team
        for team in teams:
            if team.get('member_ids'):
                member_data = execute_kw(
                    'crm.team.member', 'read',
                    [team['member_ids']],
                    {'fields': ['user_id']}
                )

                user_ids = [m['user_id'][0] for m in member_data if m.get('user_id')]
                if user_ids:
                    user_data = execute_kw(
                        'res.users', 'read',
                        [user_ids],
                        {'fields': ['name', 'login']}
                    )
                    team['members'] = user_data
                else:
                    team['members'] = []

        return jsonify({"data": teams})

    except Exception as e:
        logger.error(f"Error retrieving sales teams: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/api/stages', methods=['GET'])
@require_api_key
def get_stages():
    """Get CRM stages"""
    try:
        stages = execute_kw(
            'crm.stage', 'search_read',
            [[]],
            {'fields': ['id', 'name', 'sequence'], 'order': 'sequence'}
        )

        if stages is None:
            return jsonify({"error": "Failed to retrieve stages from Odoo"}), 500

        return jsonify({"data": stages})

    except Exception as e:
        logger.error(f"Error retrieving stages: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


@app.route('/api/dashboard', methods=['GET'])
@require_api_key
def get_dashboard_data():
    """Get aggregated dashboard data"""
    try:
        # Get stage statistics
        stages = execute_kw('crm.stage', 'search_read', [[]], {'fields': ['id', 'name', 'sequence']})

        # Get data for each stage
        stage_stats = []
        total_expected_revenue = 0
        for stage in stages:
            count = execute_kw('crm.lead', 'search_count', [[('stage_id', '=', stage['id'])]])

            # Calculate revenue for this stage
            revenue = execute_kw(
                'crm.lead', 'read_group',
                [[('stage_id', '=', stage['id'])]],
                ['expected_revenue:sum']
            )

            stage_revenue = revenue[0]['expected_revenue'] if revenue and revenue[0]['expected_revenue'] else 0
            total_expected_revenue += stage_revenue

            stage_stats.append({
                'id': stage['id'],
                'name': stage['name'],
                'sequence': stage['sequence'],
                'count': count,
                'expected_revenue': stage_revenue
            })

        # Get team statistics
        teams = execute_kw('crm.team', 'search_read', [[]], {'fields': ['id', 'name']})

        team_stats = []
        for team in teams:
            count = execute_kw('crm.lead', 'search_count', [[('team_id', '=', team['id'])]])

            # Calculate revenue for this team
            revenue = execute_kw(
                'crm.lead', 'read_group',
                [[('team_id', '=', team['id'])]],
                ['expected_revenue:sum']
            )

            team_revenue = revenue[0]['expected_revenue'] if revenue and revenue[0]['expected_revenue'] else 0

            team_stats.append({
                'id': team['id'],
                'name': team['name'],
                'count': count,
                'expected_revenue': team_revenue
            })

        # Get meeting statistics by month for current year
        current_year = datetime.now().year
        sql_query = f"""
            SELECT EXTRACT(MONTH FROM start) AS month,
                   COUNT(*) AS meeting_count
            FROM calendar_event
            WHERE opportunity_id IS NOT NULL
              AND EXTRACT(YEAR FROM start) = {current_year}
            GROUP BY EXTRACT(MONTH FROM start)
            ORDER BY month
        """

        # This requires direct db access, alternatively we can use search_read with filters
        # Since we can't run SQL directly through XML-RPC, using a different approach

        monthly_meetings = []
        for month in range(1, 13):
            month_start = f"{current_year}-{month:02d}-01"
            if month < 12:
                month_end = f"{current_year}-{month+1:02d}-01"
            else:
                month_end = f"{current_year+1}-01-01"

            count = execute_kw(
                'calendar.event', 'search_count',
                [[
                    ('opportunity_id', '!=', False),
                    ('start', '>=', month_start),
                    ('start', '<', month_end)
                ]]
            )

            monthly_meetings.append({
                'month': month,
                'month_name': datetime(2000, month, 1).strftime('%B'),
                'meeting_count': count
            })

        # Return combined dashboard data
        return jsonify({
            "total_leads": execute_kw('crm.lead', 'search_count', [[]]),
            "total_expected_revenue": total_expected_revenue,
            "total_meetings": execute_kw('calendar.event', 'search_count', [[('opportunity_id', '!=', False)]]),
            "stage_stats": stage_stats,
            "team_stats": team_stats,
            "monthly_meetings": monthly_meetings,
        })

    except Exception as e:
        logger.error(f"Error retrieving dashboard data: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500


if __name__ == '__main__':
    # Run the app
    logger.info(f"Starting Odoo-PowerBI connector on port 5000")
    run_simple('0.0.0.0', 5000, app)