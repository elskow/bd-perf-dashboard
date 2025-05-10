from fastapi import Depends, HTTPException, status
from dependencies import get_api_key
from odoo_client import execute_kw
from models import SalesTeamListResponse
from config import logger
from app import app

@app.get("/api/salesteams", response_model=SalesTeamListResponse, tags=["Sales Teams"])
async def get_sales_teams(
    api_key: str = Depends(get_api_key),
):
    """Get sales teams data"""
    try:
        teams = execute_kw(
            'crm.team', 'search_read',
            [[('name', 'in', ['Sales Indonesia', 'Sales Singapore'])]],
            {'fields': ['id', 'name', 'user_id']}
        )

        if teams is None or not teams:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                               detail="Failed to retrieve sales teams from Odoo")

        processed_teams = []
        for team in teams:
            team_members = execute_kw(
                'crm.team.member', 'search_read',
                [[('crm_team_id', '=', team['id'])]],
                {'fields': ['user_id']}
            )
            
            user_ids = [m['user_id'][0] for m in team_members if m.get('user_id')]
            
            processed_team = {
                'id': team['id'],
                'name': team['name'],
                'user_id': {'id': team['user_id'][0], 'name': team['user_id'][1]} if team.get('user_id') else None,
                'members': []
            }
            
            if user_ids:
                user_data = execute_kw(
                    'res.users', 'read',
                    [user_ids],
                    {'fields': ['id', 'name', 'login', 'image_1920']}
                )
                
                for user in user_data:
                    if 'image_1920' not in user:
                        user['image_1920'] = None
                
                processed_team['members'] = user_data
            
            processed_teams.append(processed_team)

        return {"data": processed_teams}

    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"Error retrieving sales teams: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                           detail=f"An error occurred: {str(e)}")