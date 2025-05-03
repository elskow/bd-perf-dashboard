from fastapi import Security, HTTPException, Depends, status
from fastapi.security.api_key import APIKeyHeader
from typing import Optional
from config import API_KEY, logger

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Validate API key if configured"""
    if API_KEY == 'your-secure-api-key':
        logger.debug("API key validation skipped (using default key)")
        return "default-key"

    if api_key == API_KEY:
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API Key",
    )