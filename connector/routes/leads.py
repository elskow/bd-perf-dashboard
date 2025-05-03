from fastapi import Depends, Query, HTTPException, status
from typing import Optional, List
from fastapi.responses import StreamingResponse
import pandas as pd
import io
from dependencies import get_api_key
from odoo_client import execute_kw_async, batch_execute
from models import LeadListResponse
from config import logger
from app import app
from cache import cached

@app.get("/api/leads", response_model=LeadListResponse, tags=["Leads"])
@cached(ttl=60)  # 60 seconds cache
async def get_leads(
    api_key: str = Depends(get_api_key),
    limit: int = Query(100, ge=1, le=1000),
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

        # Execute count and search in parallel
        count_query = ('crm.lead', 'search_count', [domain], {})

        # Define fields to fetch
        fields = [
            'id', 'name', 'partner_name', 'contact_name', 'email_from',
            'phone', 'user_id', 'team_id', 'stage_id', 'type',
            'probability', 'expected_revenue', 'date_deadline',
            'create_date', 'write_date', 'tag_ids', 'priority'
        ]

        search_query = ('crm.lead', 'search_read', [domain], {
            'fields': fields,
            'limit': limit,
            'offset': offset,
            'order': 'create_date desc'
        })

        # Execute queries in parallel
        results = await batch_execute([count_query, search_query])

        total_count = results[0]
        leads = results[1]

        if leads is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                               detail="Failed to retrieve leads from Odoo")

        # Resolve related fields - prepare batch queries for tags
        tag_ids = set()
        for lead in leads:
            if lead.get('tag_ids'):
                tag_ids.update(lead['tag_ids'])

        # If we have tags, fetch them in one batch
        tag_data = {}
        if tag_ids:
            tags = await execute_kw_async('crm.tag', 'read', [list(tag_ids)], {'fields': ['name']})
            if tags:
                tag_data = {tag['id']: tag['name'] for tag in tags}

        # Post-process leads
        for lead in leads:
            # Convert M2O fields (user_id, team_id, stage_id) to nested objects
            for field in ['user_id', 'team_id', 'stage_id']:
                if lead.get(field):
                    lead[field] = {
                        'id': lead[field][0],
                        'name': lead[field][1]
                    }

            # Add resolved tags
            if lead.get('tag_ids'):
                lead['tags'] = [tag_data.get(tag_id, f"Unknown ({tag_id})") for tag_id in lead['tag_ids']]
            else:
                lead['tags'] = []

        # Return response with pagination info
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
    limit: int = Query(1000, ge=1, le=10000),
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

        # Define fields to fetch - more efficient for CSV
        fields = [
            'id', 'name', 'partner_name', 'contact_name', 'email_from',
            'phone', 'user_id', 'team_id', 'stage_id', 'type',
            'probability', 'expected_revenue', 'date_deadline',
            'create_date', 'write_date', 'priority'
        ]

        # Get leads
        leads = await execute_kw_async(
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

        # Process data for CSV more efficiently
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

        # Use pandas for efficient CSV generation
        df = pd.DataFrame(processed_data)

        # Use StringIO buffer with more efficient write operations
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)

        # Configure response with appropriate headers for caching
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=crm_leads.csv",
                "Cache-Control": "max-age=60"  # Allow caching for 60 seconds
            }
        )

    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving leads as CSV: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                           detail=f"An error occurred: {str(e)}")