from fastapi import Depends, HTTPException, status, Query
from datetime import datetime, timedelta
import asyncio
from dependencies import get_api_key
from odoo_client import execute_kw_async, batch_execute, connect_to_odoo
from models import DashboardResponse, LeadInfo, MeetingStats, MeetingDetail
from config import logger
from cache import cached
from app import app

def format_date(date_str):
    """Format date string to 'DD MONTH' format or return None if invalid"""
    if not date_str or date_str == False:
        return None
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return date_obj.strftime('%d %B').upper()
    except (ValueError, TypeError):
        return None

@app.get("/api/dashboard", response_model=DashboardResponse, tags=["Dashboard"])
@cached(ttl=300, key_prefix='dashboard')
async def get_dashboard_data(
    api_key: str = Depends(get_api_key),
    salesperson_id: int = Query(..., description="ID of the salesperson to get dashboard data for")
):
    """Get weekly report data for a specific salesperson"""
    try:
        # Get salesperson's details
        user_data = await execute_kw_async('res.users', 'read', [[salesperson_id]], {'fields': ['name']})
        if not user_data:
            raise HTTPException(status_code=404, detail="Salesperson not found")
        
        salesperson_name = user_data[0]['name']

        # Get leads for this salesperson with more fields
        leads_data = await execute_kw_async(
            'crm.lead',
            'search_read',
            [[('user_id', '=', salesperson_id)]],
            {
                'fields': [
                    'name',
                    'partner_id',  # This contains industry info
                    'partner_name',  # Company name
                    'stage_id',
                    'create_date',  # For first meeting date reference
                    'write_date',   # For stage change reference
                    'date_conversion',  # For warm/focus date
                    'stage_id'      # Current stage
                ]
            }
        )

        # Get all meetings for these leads to find first meetings
        lead_ids = [lead['id'] for lead in leads_data]
        meetings = await execute_kw_async(
            'calendar.event',
            'search_read',
            [[('opportunity_id', 'in', lead_ids)]],
            {
                'fields': ['opportunity_id', 'start'],
                'order': 'start asc'
            }
        )

        # Organize meetings by lead
        lead_first_meetings = {}
        for meeting in meetings:
            lead_id = meeting['opportunity_id'][0]
            if lead_id not in lead_first_meetings:
                lead_first_meetings[lead_id] = format_date(meeting['start'])

        # Get stage changes from message history
        messages = await execute_kw_async(
            'mail.message',
            'search_read',
            [[
                ('model', '=', 'crm.lead'),
                ('res_id', 'in', lead_ids),
                ('body', 'ilike', '%stage changed%')
            ]],
            {'fields': ['res_id', 'body', 'date']}
        )

        # Find warm/focus dates from stage changes
        warm_focus_dates = {}
        for msg in messages:
            if any(stage in msg['body'].upper() for stage in ['WARM', 'FOCUS']):
                lead_id = msg['res_id']
                if lead_id not in warm_focus_dates:
                    warm_focus_dates[lead_id] = format_date(msg['date'])

        # Get partner details for industry information
        partner_ids = []
        company_names = set()
        for lead in leads_data:
            if lead.get('partner_id'):
                partner_ids.append(lead['partner_id'][0])
            elif lead.get('partner_name'):
                company_names.add(lead['partner_name'])

        partners_data = {}
        if partner_ids:
            partners = await execute_kw_async(
                'res.partner',
                'read',
                [partner_ids],
                {'fields': ['id', 'industry_id', 'name']}
            )
            partners_data = {p['id']: p for p in partners}

        # If we have company names without partner_id, search for them
        if company_names:
            additional_partners = await execute_kw_async(
                'res.partner',
                'search_read',
                [[('name', 'in', list(company_names)), ('is_company', '=', True)]],
                {'fields': ['id', 'industry_id', 'name']}
            )
            for partner in additional_partners:
                partners_data[partner['id']] = partner

        # Process leads
        leads = []
        for lead in leads_data:
            industry = None
            # Try to get industry from partner_id first
            if lead.get('partner_id'):
                partner = partners_data.get(lead['partner_id'][0], {})
                if partner.get('industry_id'):
                    industry = partner['industry_id'][1]
            # If no industry found and we have partner_name, try to find matching company
            elif lead.get('partner_name'):
                for partner in partners_data.values():
                    if partner.get('name') == lead['partner_name'] and partner.get('industry_id'):
                        industry = partner['industry_id'][1]
                        break

            # If still no industry, search for the company in res.partner
            if not industry and lead.get('partner_name'):
                company_search = await execute_kw_async(
                    'res.partner',
                    'search_read',
                    [[('name', '=', lead['partner_name']), ('is_company', '=', True)]],
                    {'fields': ['industry_id']}
                )
                if company_search and company_search[0].get('industry_id'):
                    industry = company_search[0]['industry_id'][1]

            # Get first meeting date from actual meetings or fallback to create date
            first_meeting_date = lead_first_meetings.get(lead['id']) or format_date(lead['create_date'])

            # Get warm/focus date based on stage and message history
            stage_name = lead['stage_id'][1].upper() if lead.get('stage_id') else 'NEW'
            warm_focus_date = None
            if any(stage in stage_name for stage in ['WARM', 'FOCUS', 'CONTRACT', 'WON']):
                warm_focus_date = warm_focus_dates.get(lead['id']) or format_date(lead['write_date'])

            leads.append(LeadInfo(
                name=lead['name'],
                industry=industry or "Unknown",  # Never return null for industry
                stage=stage_name,
                first_meeting_date=first_meeting_date,
                warm_focus_date=warm_focus_date
            ))

        # Get meetings statistics (last 30 days)
        today = datetime.now()
        start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')

        meetings_data = await execute_kw_async(
            'calendar.event',
            'search_read',
            [[
                ('user_id', '=', salesperson_id),
                ('start', '>=', start_date),
                ('start', '<=', end_date)
            ]],
            {
                'fields': [
                    'name',
                    'start',
                    'stop',
                    'opportunity_id'
                ]
            }
        )

        # Calculate meeting stats
        meeting_counts = {
            'first': 0,
            'second': 0,
            'third': 0,
            'more': 0
        }

        lead_meeting_counts = {}
        for meeting in meetings_data:
            if meeting.get('opportunity_id'):
                lead_id = meeting['opportunity_id'][0]
                lead_meeting_counts[lead_id] = lead_meeting_counts.get(lead_id, 0) + 1

        for count in lead_meeting_counts.values():
            if count == 1:
                meeting_counts['first'] += 1
            elif count == 2:
                meeting_counts['second'] += 1
            elif count == 3:
                meeting_counts['third'] += 1
            else:
                meeting_counts['more'] += 1

        # Get upcoming meetings
        future_meetings = await execute_kw_async(
            'calendar.event',
            'search_read',
            [[
                ('user_id', '=', salesperson_id),
                ('start', '>=', today.strftime('%Y-%m-%d'))
            ]],
            {
                'fields': ['name', 'start'],
                'limit': 5,
                'order': 'start asc'
            }
        )

        upcoming = [
            MeetingDetail(
                name=meeting['name'],
                date=format_date(meeting['start'])
            )
            for meeting in future_meetings
        ]

        return DashboardResponse(
            salesperson_name=salesperson_name,
            leads=leads,
            meeting_stats=MeetingStats(
                first_meetings=meeting_counts['first'],
                second_meetings=meeting_counts['second'],
                third_meetings=meeting_counts['third'],
                more_meetings=meeting_counts['more'],
                total_meetings=len(meetings_data)
            ),
            upcoming_meetings=upcoming
        )

    except Exception as e:
        logger.error(f"Error in dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )