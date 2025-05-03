from fastapi import APIRouter
from datetime import datetime
from odoo_client import connect_to_odoo
from app import app

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Endpoint to check if the API is running and can connect to Odoo"""
    uid, _ = connect_to_odoo()
    if uid:
        return {
            "status": "healthy",
            "odoo_connected": True,
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "status": "unhealthy",
            "odoo_connected": False,
            "error": "Could not connect to Odoo",
            "timestamp": datetime.now().isoformat()
        }