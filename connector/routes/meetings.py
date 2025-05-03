from fastapi import Depends, Query, HTTPException, status
from typing import Optional
from fastapi.responses import StreamingResponse
import pandas as pd
import io
from dependencies import get_api_key
from odoo_client import execute_kw
from models import MeetingListResponse
from config import logger
from app import app

@app.get("/api/meetings", response_model=MeetingListResponse, tags=["Meetings"])
async def get_meetings(
    api_key: str = Depends(get_api_key),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    user: Optional[str] = None,
    opportunity_id: Optional[int] = None,
):
    """Get calendar meetings related to opportunities"""
    try:
        # Build domain filter
        domain = [('opportunity_id', '!=', False)]  # Only meetings related to opportunities
        if user:
            domain.append(('user_id.name', 'ilike', user))
        if opportunity_id:
            domain.append(('opportunity_id', '=', opportunity_id))

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
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                               detail="Failed to retrieve meetings from Odoo")

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

        # Return response
        return {
            "count": total_count,
            "limit": limit,
            "offset": offset,
            "data": meetings
        }

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error retrieving meetings: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                           detail=f"An error occurred: {str(e)}")


@app.get("/api/meetings/csv", tags=["Meetings"])
async def get_meetings_csv(
    api_key: str = Depends(get_api_key),
    limit: int = Query(1000, ge=1),
    offset: int = Query(0, ge=0),
    user: Optional[str] = None,
):
    """Get calendar meetings as CSV for direct Power BI import"""
    try:
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
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                               detail="Failed to retrieve meetings from Odoo")

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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                               detail="No data found")

        # Convert to DataFrame and then to CSV
        df = pd.DataFrame(processed_data)
        csv_stream = io.StringIO()
        df.to_csv(csv_stream, index=False)
        csv_stream.seek(0)

        # Return CSV response
        return StreamingResponse(
            iter([csv_stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=crm_meetings.csv"}
        )

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error retrieving meetings as CSV: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                           detail=f"An error occurred: {str(e)}")