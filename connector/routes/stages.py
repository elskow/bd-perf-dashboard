from fastapi import Depends, HTTPException, status
from dependencies import get_api_key
from odoo_client import execute_kw
from models import StageListResponse
from config import logger
from app import app

@app.get("/api/stages", response_model=StageListResponse, tags=["Stages"])
async def get_stages(
    api_key: str = Depends(get_api_key),
):
    """Get CRM stages"""
    try:
        stages = execute_kw(
            'crm.stage', 'search_read',
            [[]],
            {'fields': ['id', 'name', 'sequence'], 'order': 'sequence'}
        )

        if stages is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                               detail="Failed to retrieve stages from Odoo")

        return {"data": stages}

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error retrieving stages: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                           detail=f"An error occurred: {str(e)}")