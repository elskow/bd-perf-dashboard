from fastapi import Depends, HTTPException, status
from datetime import datetime
import asyncio
from dependencies import get_api_key
from odoo_client import execute_kw_async, batch_execute
from models import DashboardResponse
from config import logger
from cache import cached
from app import app

@app.get("/api/dashboard", response_model=DashboardResponse, tags=["Dashboard"])
@cached(ttl=300, key_prefix='dashboard')
async def get_dashboard_data(
    api_key: str = Depends(get_api_key),
):
    """Get aggregated dashboard data with optimized parallel queries"""
    try:
        # Fetch stages first (needed for subsequent queries)
        stages = await execute_kw_async('crm.stage', 'search_read', [[]],
                                   {'fields': ['id', 'name', 'sequence']})

        if stages is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                               detail="Failed to retrieve stages from Odoo")

        # Prepare parallel queries for stage stats
        stage_queries = []

        # For each stage, prepare count and revenue queries
        for stage in stages:
            stage_id = stage['id']
            # Stage lead count query
            stage_queries.append(
                ('crm.lead', 'search_count', [[('stage_id', '=', stage_id)]], {})
            )
            # Stage revenue query - add the missing groupby parameter
            stage_queries.append(
                ('crm.lead', 'read_group',
                [[('stage_id', '=', stage_id)]],
                {'fields': ['expected_revenue:sum'], 'groupby': []}  # Note the added 'groupby': [] parameter
                )
            )

        # Get teams for team stats
        teams = await execute_kw_async('crm.team', 'search_read', [[]], {'fields': ['id', 'name']})

        if teams is None:
            teams = []

        # Prepare team queries
        team_queries = []
        for team in teams:
            team_id = team['id']
            # Team lead count query
            team_queries.append(
                ('crm.lead', 'search_count', [[('team_id', '=', team_id)]], {})
            )
            # Team revenue query
            team_queries.append(
                ('crm.lead', 'read_group',
                [[('team_id', '=', team_id)]],
                {'fields': ['expected_revenue:sum'], 'groupby': []}  # Added groupby parameter
                )
            )

        # Monthly meeting queries
        current_year = datetime.now().year
        month_queries = []

        for month in range(1, 13):
            month_start = f"{current_year}-{month:02d}-01"
            month_end = f"{current_year}-{month+1:02d}-01" if month < 12 else f"{current_year+1}-01-01"

            month_queries.append(
                ('calendar.event', 'search_count',
                 [[('opportunity_id', '!=', False), ('start', '>=', month_start), ('start', '<', month_end)]], {})
            )

        # Additional overall stats queries
        overall_queries = [
            ('crm.lead', 'search_count', [[]], {}),
            ('calendar.event', 'search_count', [[('opportunity_id', '!=', False)]], {})
        ]

        # Execute all queries in parallel
        stage_results = await batch_execute(stage_queries)
        team_results = await batch_execute(team_queries) if teams else []
        month_results = await batch_execute(month_queries)
        overall_results = await batch_execute(overall_queries)

        # Process stage stats with error handling
        stage_stats = []
        total_expected_revenue = 0

        for i, stage in enumerate(stages):
            count_index = i * 2
            revenue_index = i * 2 + 1

            # Default to 0 if None
            count = stage_results[count_index] if stage_results and count_index < len(stage_results) and stage_results[count_index] is not None else 0

            revenue_result = stage_results[revenue_index] if stage_results and revenue_index < len(stage_results) else None
            stage_revenue = revenue_result[0]['expected_revenue'] if revenue_result and revenue_result[0] and 'expected_revenue' in revenue_result[0] and revenue_result[0]['expected_revenue'] is not None else 0

            total_expected_revenue += stage_revenue

            stage_stats.append({
                'id': stage['id'],
                'name': stage['name'],
                'sequence': stage['sequence'],
                'count': count,
                'expected_revenue': stage_revenue
            })

        # Process team stats with error handling
        team_stats = []
        for i, team in enumerate(teams):
            count_index = i * 2
            revenue_index = i * 2 + 1

            # Default to 0 if None
            count = team_results[count_index] if team_results and count_index < len(team_results) and team_results[count_index] is not None else 0

            revenue_result = team_results[revenue_index] if team_results and revenue_index < len(team_results) else None
            team_revenue = revenue_result[0]['expected_revenue'] if revenue_result and revenue_result[0] and 'expected_revenue' in revenue_result[0] and revenue_result[0]['expected_revenue'] is not None else 0

            team_stats.append({
                'id': team['id'],
                'name': team['name'],
                'count': count,
                'expected_revenue': team_revenue
            })

        # Process monthly meetings with error handling
        monthly_meetings = []
        for month, count in enumerate(month_results, 1):
            monthly_meetings.append({
                'month': month,
                'month_name': datetime(2000, month, 1).strftime('%B'),
                'meeting_count': count if count is not None else 0  # Default to 0 if None
            })

        # Get overall stats with error handling
        total_leads = overall_results[0] if overall_results and len(overall_results) > 0 and overall_results[0] is not None else 0
        total_meetings = overall_results[1] if overall_results and len(overall_results) > 1 and overall_results[1] is not None else 0

        # Return combined dashboard data
        return {
            "total_leads": total_leads,
            "total_expected_revenue": total_expected_revenue,
            "total_meetings": total_meetings,
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