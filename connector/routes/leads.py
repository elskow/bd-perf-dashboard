from fastapi import Depends, Query, HTTPException, status
from typing import Optional
from fastapi.responses import StreamingResponse
import pandas as pd
import io
from dependencies import get_api_key
from odoo_client import execute_kw
from models import LeadListResponse
from config import logger
from app import app

@app.get("/api/leads", response_model=LeadListResponse, tags=["Leads"])
async def get_leads(
    api_key: str = Depends(get_api_key),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    stage: Optional[str] = None,
    team: Optional[str] = None,
    user: Optional[str] = None,
):
    """Get CRM leads with optional filtering"""
    try:
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
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                               detail="Failed to retrieve leads from Odoo")

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

        # Return response
        return {
            "count": total_count,
            "limit": limit,
            "offset": offset,
            "data": leads
        }

    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving leads: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                           detail=f"An error occurred: {str(e)}")

@app.get("/api/leads/csv", tags=["Leads"])
async def get_leads_csv(
    api_key: str = Depends(get_api_key),
    limit: int = Query(1000, ge=1),
    offset: int = Query(0, ge=0),
    stage: Optional[str] = None,
    team: Optional[str] = None,
    user: Optional[str] = None,
):
    """Get CRM leads as CSV for direct Power BI import"""
    try:
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
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                               detail="Failed to retrieve leads from Odoo")

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
            headers={"Content-Disposition": "attachment; filename=crm_leads.csv"}
        )

    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving leads as CSV: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                           detail=f"An error occurred: {str(e)}")