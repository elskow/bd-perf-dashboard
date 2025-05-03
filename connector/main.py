import uvicorn
from app import app
import config
from routes import *  # Import all routes

if __name__ == "__main__":
    # Run the app
    config.logger.info(f"Starting Odoo-PowerBI connector on port 7001")
    uvicorn.run("main:app", host="0.0.0.0", port=7001, reload=False)