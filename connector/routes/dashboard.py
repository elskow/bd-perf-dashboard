from fastapi import Depends, HTTPException, status
from datetime import datetime
from dependencies import get_api_key
from odoo_client import execute_kw
from models import DashboardResponse
from config import logger
from app import app

@app.get("/api/dashboard", response_model=DashboardResponse, tags=["Dashboard"])
async def get_dashboard_data(
    api_key: str = Depends(get_api_key),
):
    """Get aggregated dashboard data"""
    try:
        # Get stage statistics
        stages = execute_kw('crm.stage', 'search_read', [[]], {'fields': ['id', 'name', 'sequence']})

        if stages is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                               detail="Failed to retrieve stages from Odoo")

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
        return {
            "total_leads": execute_kw('crm.lead', 'search_count', [[]]),
            "total_expected_revenue": total_expected_revenue,
            "total_meetings": execute_kw('calendar.event', 'search_count', [[('opportunity_id', '!=', False)]]),
            "stage_stats": stage_stats,
            "team_stats": team_stats,
            "monthly_meetings": monthly_meetings,
        }

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error retrieving dashboard data: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                           detail=f"An error occurred: {str(e)}")