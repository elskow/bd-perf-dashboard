from fastapi import Depends, HTTPException, status, Query
from datetime import datetime, timedelta
from dependencies import get_api_key
from odoo_client import execute_kw_async
from models import (
    DashboardResponse, LeadInfo, MeetingStats, MeetingDetail,
    AnalyticsData, IndustryDistribution, StageDistribution,
    ConversionMetrics, ActivityTimeline, KPIMetrics
)
from config import logger
from cache import cached
from app import app


def format_date(date_str):
    """Format date string to 'DD MONTH' format or return None if invalid"""
    if not date_str or date_str == False:
        return None
    try:
        if isinstance(date_str, str):
            if ' ' in date_str:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            else:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            return None
        return date_obj.strftime('%d %b').upper()
    except (ValueError, TypeError):
        try:
            if 'T' in str(date_str):
                date_obj = datetime.fromisoformat(str(date_str).replace('T', ' ').split('.')[0])
                return date_obj.strftime('%d %b').upper()
        except:
            pass
        return None

@app.get(
    "/api/dashboard",
    response_model=DashboardResponse,
    tags=["Dashboard"],
    summary="Get Salesperson Dashboard Data",
    description="""
    Retrieves comprehensive dashboard data for a specific salesperson including:
    - Lead information with industry and meeting dates
    - Meeting statistics for the last 30 days
    - Upcoming meetings schedule

    The data is cached for 5 minutes to improve performance.
    """,
    responses={
        200: {
            "description": "Successfully retrieved dashboard data",
            "content": {
                "application/json": {
                    "example": {
                        "salesperson_name": "John Doe",
                        "leads": [
                            {
                                "name": "Potential Client A",
                                "industry": "Technology",
                                "stage": "WARM",
                                "first_meeting_date": "15 MARCH",
                                "warm_focus_date": "20 MARCH"
                            }
                        ],
                        "meeting_stats": {
                            "first_meetings": 5,
                            "second_meetings": 3,
                            "third_meetings": 2,
                            "more_meetings": 1,
                            "total_meetings": 11
                        },
                        "upcoming_meetings": [
                            {
                                "name": "Follow-up Meeting",
                                "date": "25 MARCH"
                            }
                        ]
                    }
                }
            }
        },
        401: {
            "description": "Invalid or missing API key",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid API key"}
                }
            }
        },
        404: {
            "description": "Salesperson not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Salesperson not found"}
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "An error occurred while retrieving dashboard data"}
                }
            }
        }
    }
)
@cached(ttl=300, key_prefix='dashboard')
async def get_dashboard_data(
    salesperson_id: int = Query(
        ...,
        description="ID of the salesperson to get dashboard data for",
        example=1,
        gt=0,
        title="Salesperson ID"
    )
) -> DashboardResponse:
    """
    Get weekly report data for a specific salesperson.

    This endpoint provides a comprehensive dashboard including:
    - List of leads with their current stages and important dates
    - Meeting statistics (1st, 2nd, 3rd, and more meetings)
    - Upcoming meetings schedule

    The data is cached for 5 minutes to improve performance and reduce load on the Odoo server.

    Args:
        salesperson_id (int): The ID of the salesperson to get data for

    Returns:
        DashboardResponse: Complete dashboard data including leads, meeting stats, and upcoming meetings

    Raises:
        HTTPException: If authentication fails, salesperson not found, or there's an error retrieving data
    """
    try:
        user_data = await execute_kw_async('res.users', 'read', [[salesperson_id]], {'fields': ['name']})
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Salesperson not found"
            )

        salesperson_name = user_data[0]['name']

        team_member_data = await execute_kw_async(
            'crm.team.member',
            'search_read',
            [[('user_id', '=', salesperson_id)]],
            {'fields': ['crm_team_id']}
        )

        team_name = None
        team_country = None
        if team_member_data:
            team_id = team_member_data[0]['crm_team_id'][0]
            team_data = await execute_kw_async(
                'crm.team',
                'read',
                [[team_id]],
                {'fields': ['name']}
            )
            if team_data:
                team_name = team_data[0]['name']
                if 'Indonesia' in team_name:
                    team_country = 'Indonesia'
                elif 'Singapore' in team_name:
                    team_country = 'Singapore'

        logger.debug(f"Team info for salesperson {salesperson_id}: team_name='{team_name}', team_country='{team_country}'")

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
                    'date_open',    # Date when lead was qualified
                    'date_closed',  # Date when lead was closed
                    'expected_revenue',  # Deal value
                    'probability'  # Win probability
                ]
            }
        )

        lead_ids = [lead['id'] for lead in leads_data]
        meetings = await execute_kw_async(
            'calendar.event',
            'search_read',
            [[('opportunity_id', 'in', lead_ids)]],
            {
                'fields': ['opportunity_id', 'start', 'name'],
                'order': 'start asc'
            }
        )

        logger.debug(f"Found {len(meetings) if meetings else 0} meetings for {len(lead_ids)} leads")
        if meetings:
            logger.debug(f"Sample meeting: {meetings[0] if meetings else 'None'}")

        lead_first_meetings = {}
        lead_meetings = {}
        if meetings:
            for meeting in meetings:
                if meeting.get('opportunity_id'):
                    lead_id = meeting['opportunity_id'][0]
                    if lead_id not in lead_first_meetings:
                        first_meeting_date = format_date(meeting.get('start'))
                        if first_meeting_date:
                            lead_first_meetings[lead_id] = first_meeting_date
                    if lead_id not in lead_meetings:
                        lead_meetings[lead_id] = []
                    lead_meetings[lead_id].append(meeting)

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

        warm_focus_dates = {}
        if messages:
            for msg in messages:
                if msg.get('body') and any(stage in msg['body'].upper() for stage in ['WARM', 'FOCUS']):
                    lead_id = msg['res_id']
                    if lead_id not in warm_focus_dates:
                        warm_focus_dates[lead_id] = format_date(msg.get('date'))

        logger.debug(f"Found {len(warm_focus_dates)} warm/focus dates from messages")

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

        if company_names:
            additional_partners = await execute_kw_async(
                'res.partner',
                'search_read',
                [[('name', 'in', list(company_names)), ('is_company', '=', True)]],
                {'fields': ['id', 'industry_id', 'name']}
            )
            for partner in additional_partners:
                partners_data[partner['id']] = partner

        leads = []
        industry_counts = {}
        stage_counts = {}
        stage_mapping = {
            'NEW': ['NEW', 'DRAFT', 'INITIAL'],
            'QUALIFIED': ['QUALIFIED', 'QUALIFICATION'],
            'PROPOSITION': ['PROPOSITION', 'PROPOSAL', 'QUOTE'],
            'NEGOTIATION': ['NEGOTIATION', 'NEGOTIATE'],
            'WON': ['WON', 'CLOSED WON', 'SUCCESS'],
            'LOST': ['LOST', 'CLOSED LOST', 'FAILED']
        }

        for lead in leads_data:
            industry = None
            if lead.get('partner_id'):
                partner = partners_data.get(lead['partner_id'][0], {})
                if partner.get('industry_id'):
                    industry = partner['industry_id'][1]
            elif lead.get('partner_name'):
                for partner in partners_data.values():
                    if partner.get('name') == lead['partner_name'] and partner.get('industry_id'):
                        industry = partner['industry_id'][1]
                        break

            if not industry and lead.get('partner_name'):
                company_search = await execute_kw_async(
                    'res.partner',
                    'search_read',
                    [[('name', '=', lead['partner_name']), ('is_company', '=', True)]],
                    {'fields': ['industry_id']}
                )
                if company_search and company_search[0].get('industry_id'):
                    industry = company_search[0]['industry_id'][1]

            if not industry or industry.strip() == "":
                industry = "Unknown"

            industry = industry.strip()
            industry_counts[industry] = industry_counts.get(industry, 0) + 1

            first_meeting_date = lead_first_meetings.get(lead['id'])
            if not first_meeting_date:
                for date_field in ['create_date', 'date_open']:
                    if lead.get(date_field):
                        first_meeting_date = format_date(lead[date_field])
                        if first_meeting_date:
                            break

            raw_stage = lead['stage_id'][1].upper() if lead.get('stage_id') else 'NEW'

            stage_name = raw_stage  # Use raw stage as default
            for standard_stage, variations in stage_mapping.items():
                if any(variation in raw_stage for variation in variations):
                    stage_name = standard_stage
                    break

            logger.debug(f"Lead {lead['name']}: raw_stage='{raw_stage}' -> mapped_stage='{stage_name}'")
            stage_counts[stage_name] = stage_counts.get(stage_name, 0) + 1

            warm_focus_date = None
            if any(stage in stage_name for stage in ['WARM', 'FOCUS', 'CONTRACT', 'WON']):
                warm_focus_date = warm_focus_dates.get(lead['id'])
                if not warm_focus_date:
                    for date_field in ['date_conversion', 'date_open', 'write_date']:
                        if lead.get(date_field):
                            warm_focus_date = format_date(lead[date_field])
                            if warm_focus_date:
                                break

            lead_meeting_count = len(lead_meetings.get(lead['id'], []))

            logger.debug(f"Lead {lead['name']}: first_meeting_date={first_meeting_date}, warm_focus_date={warm_focus_date}")

            leads.append(LeadInfo(
                name=lead['name'],
                industry=industry,
                stage=stage_name,
                first_meeting_date=first_meeting_date,
                warm_focus_date=warm_focus_date,
                expected_revenue=lead.get('expected_revenue', 0.0),
                probability=lead.get('probability', 0.0),
                days_in_stage=None,
                meeting_count=lead_meeting_count,
                last_activity=format_date(lead.get('write_date'))
            ))

        meetings_data = await execute_kw_async(
            'calendar.event',
            'search_read',
            [[
                ('user_id', '=', salesperson_id),
                ('opportunity_id', 'in', lead_ids)  # Only get meetings linked to leads
            ]],
            {
                'fields': [
                    'name',
                    'start',
                    'stop',
                    'opportunity_id'
                ],
                'order': 'start asc'  # Order by date to ensure proper counting
            }
        )

        meeting_counts = {
            'first': 0,  # Count of leads that have had their first meeting
            'second': 0,  # Count of leads that have had their second meeting
            'third': 0,   # Count of leads that have had their third meeting
            'more': 0     # Count of leads that have had more than 3 meetings
        }

        lead_meetings_stats = {}
        for meeting in meetings_data:
            if meeting.get('opportunity_id'):
                lead_id = meeting['opportunity_id'][0]
                if lead_id not in lead_meetings_stats:
                    lead_meetings_stats[lead_id] = []
                lead_meetings_stats[lead_id].append(meeting)

        for lead_id, meetings in lead_meetings_stats.items():
            meeting_count = len(meetings)
            if meeting_count >= 1:
                meeting_counts['first'] += 1
            if meeting_count >= 2:
                meeting_counts['second'] += 1
            if meeting_count >= 3:
                meeting_counts['third'] += 1
            if meeting_count >= 4:
                meeting_counts['more'] += 1

        today = datetime.now()
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
                name=meeting.get('name', 'Unnamed Meeting'),
                date=format_date(meeting.get('start')) or 'TBD',
                type="Meeting"
            )
            for meeting in (future_meetings or [])
        ]

        total_leads = len(leads_data)

        if not industry_counts:
            industry_counts = {"Unknown": total_leads} if total_leads > 0 else {"No Data": 1}

        industry_distribution = [
            IndustryDistribution(
                industry=industry if industry and industry != "None" else "Unknown",
                count=count,
                percentage=round(((count / total_leads) * 100), 1) if total_leads > 0 else 0.0
            )
            for industry, count in industry_counts.items()
            if count > 0  # Only include industries with actual counts
        ]

        stage_distribution = [
            StageDistribution(
                stage=stage,
                count=count,
                total_value=round(sum(lead.expected_revenue or 0 for lead in leads if lead.stage == stage), 2),
                avg_days=round((sum(lead.days_in_stage or 0 for lead in leads if lead.stage == stage) / count), 1) if count > 0 else 0.0
            )
            for stage, count in stage_counts.items()
        ]

        conversion_funnel = []

        if stage_counts:
            stage_order_priority = {
                'NEW': 1, 'QUALIFIED': 2, 'PROPOSITION': 3,
                'NEGOTIATION': 4, 'WON': 5, 'LOST': 6
            }

            sorted_stages = sorted(
                stage_counts.items(),
                key=lambda x: (stage_order_priority.get(x[0], 99), -x[1])
            )

            max_count = max(stage_counts.values()) if stage_counts else 0
            logger.debug(f"Max stage count for funnel: {max_count}")

            for stage, count in sorted_stages[:10]:  # Limit to prevent too many items
                if count > 0:  # Only include stages with actual data
                    conv_rate = round((count / max_count * 100), 1) if max_count > 0 else 0.0
                    logger.debug(f"Stage {stage}: count={count}, conversion_rate={conv_rate}")
                    conversion_funnel.append(ConversionMetrics(
                        stage=stage,
                        count=count,
                        conversion_rate=round(conv_rate, 1)
                    ))

        activity_timeline = []
        for i in range(6, -1, -1):  # Reverse order to show oldest to newest
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            day_meetings = len([m for m in (meetings_data or []) if m.get('start', '').startswith(date)])

            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d %b')
            except:
                formatted_date = date.split('-')[2] + ' ' + date.split('-')[1]

            activity_timeline.append(ActivityTimeline(
                date=formatted_date,
                meetings=day_meetings,
                calls=0,  # Would need separate call tracking
                emails=0  # Would need separate email tracking
            ))

        logger.debug(f"Stage counts for salesperson {salesperson_id}: {stage_counts}")
        logger.debug(f"Total leads: {total_leads}")

        qualified_leads = stage_counts.get('QUALIFIED', 0)
        won_leads = stage_counts.get('WON', 0)
        total_revenue = sum(lead.expected_revenue or 0 for lead in leads)

        active_leads_count = len([lead for lead in leads if lead.stage not in ['WON', 'LOST']])

        kpi_metrics = KPIMetrics(
            total_leads=total_leads,
            qualified_leads=qualified_leads,
            conversion_rate=round((won_leads / total_leads * 100), 1) if total_leads > 0 else 0.0,
            avg_deal_size=round((total_revenue / total_leads), 2) if total_leads > 0 else 0.0,
            pipeline_value=round(total_revenue, 2),
            active_leads=active_leads_count,
            monthly_growth=0.0  # Would need historical data
        )

        analytics = AnalyticsData(
            industry_distribution=industry_distribution,
            stage_distribution=stage_distribution,
            conversion_funnel=conversion_funnel,
            activity_timeline=activity_timeline,
            kpi_metrics=kpi_metrics
        )

        logger.debug(f"Returning dashboard data for {salesperson_name} from {team_country} team")

        return DashboardResponse(
            salesperson_name=salesperson_name,
            team_name=team_name,
            team_country=team_country,
            leads=leads,
            meeting_stats=MeetingStats(
                first_meetings=meeting_counts['first'],
                second_meetings=meeting_counts['second'],
                third_meetings=meeting_counts['third'],
                more_meetings=meeting_counts['more'],
                total_meetings=len(meetings_data or [])
            ),
            upcoming_meetings=upcoming,
            analytics=analytics
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving dashboard data"
        )
