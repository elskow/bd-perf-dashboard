from fastapi import status
from datetime import datetime
from odoo_client import connect_to_odoo
from app import app
from pydantic import BaseModel
from typing import Optional

class HealthCheckResponse(BaseModel):
    """Response model for the health check endpoint"""
    status: str
    odoo_connected: bool
    timestamp: str
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "odoo_connected": True,
                "timestamp": "2025-05-10T12:19:09.270957",
                "error": None
            }
        }

@app.get(
    "/api/health",
    tags=["Health"],
    response_model=HealthCheckResponse,
    responses={
        200: {
            "description": "System is healthy and connected to Odoo",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": {
                            "value": {
                                "status": "healthy",
                                "odoo_connected": True,
                                "timestamp": "2025-05-10T12:19:09.270957",
                                "error": None
                            }
                        },
                        "unhealthy": {
                            "value": {
                                "status": "unhealthy",
                                "odoo_connected": False,
                                "error": "Could not connect to Odoo",
                                "timestamp": "2025-05-10T12:19:09.270957"
                            }
                        }
                    }
                }
            }
        }
    },
    summary="Check API and Odoo Connection Status",
    description="Returns the health status of the API and its connection to the Odoo server"
)
async def health_check():
    """
    Check if the API is running and can connect to Odoo.
    
    Returns:
        HealthCheckResponse: Object containing health status, Odoo connection status, and timestamp
    """
    uid, _ = connect_to_odoo()
    if uid:
        return HealthCheckResponse(
            status="healthy",
            odoo_connected=True,
            timestamp=datetime.now().isoformat(),
            error=None
        )
    else:
        return HealthCheckResponse(
            status="unhealthy",
            odoo_connected=False,
            error="Could not connect to Odoo",
            timestamp=datetime.now().isoformat()
        )