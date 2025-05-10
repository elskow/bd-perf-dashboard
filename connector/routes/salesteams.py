from fastapi import Depends, HTTPException, status
from dependencies import get_api_key
from odoo_client import execute_kw
from models import SalesTeamListResponse
from config import logger
from app import app
from typing import List

@app.get(
    "/api/salesteams",
    response_model=SalesTeamListResponse,
    tags=["Sales Teams"],
    summary="Get Sales Teams Information",
    description="Retrieves information about sales teams including team members and their details",
    responses={
        200: {
            "description": "Successfully retrieved sales teams data",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": 5,
                                "name": "Sales Singapore",
                                "user_id": None,
                                "members": [
                                    {
                                        "id": 16,
                                        "name": "Dion Irawan",
                                        "login": "dion.irawan@hashmicro.com",
                                        "image_1920": "PD94bWwgdmVyc2lvbj0nMS4wJyBlbmNvZGluZz0nVVRGLTgnID8+"  # Truncated for brevity
                                    },
                                    {
                                        "id": 17,
                                        "name": "Elisabeth Pudjo",
                                        "login": "elisabeth.pudjo@hashmicro.com",
                                        "image_1920": "PD94bWwgdmVyc2lvbj0nMS4wJyBlbmNvZGluZz0nVVRGLTgnID8+"  # Truncated for brevity
                                    }
                                ]
                            },
                            {
                                "id": 4,
                                "name": "Sales Indonesia",
                                "user_id": None,
                                "members": [
                                    {
                                        "id": 6,
                                        "name": "David Mulya",
                                        "login": "david.mulya@hashmicro.com",
                                        "image_1920": "PD94bWwgdmVyc2lvbj0nMS4wJyBlbmNvZGluZz0nVVRGLTgnID8+"  # Truncated for brevity
                                    },
                                    {
                                        "id": 7,
                                        "name": "Dony Hendrawan",
                                        "login": "dony.hendrawan@hashmicro.com",
                                        "image_1920": "PD94bWwgdmVyc2lvbj0nMS4wJyBlbmNvZGluZz0nVVRGLTgnID8+"  # Truncated for brevity
                                    }
                                ]
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
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to retrieve sales teams from Odoo"}
                }
            }
        }
    }
)
async def get_sales_teams(
    api_key: str = Depends(get_api_key),
) -> SalesTeamListResponse:
    """
    Retrieve sales teams data from Odoo.
    
    This endpoint fetches:
    - Team basic information (ID, name)
    - Team leader information
    - Team members with their details (name, login, profile image)
    
    The data is filtered to only include 'Sales Indonesia' and 'Sales Singapore' teams.
    
    Args:
        api_key (str): API key for authentication
        
    Returns:
        SalesTeamListResponse: List of sales teams with their members
        
    Raises:
        HTTPException: If authentication fails or there's an error retrieving data
    """
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