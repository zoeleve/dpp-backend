import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime
from app.db.database_postgre import get_db
from app.configs.config import settings
from app.utils.auth import role_checker
from app.configs.roles import Role
from app.utils.logger import LOG_FILE_PATH

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/")
async def read_root(current_user=Depends(role_checker(Role.ADMIN))):
    """
    Returns a basic message confirming the API is running.
    Only Admins can access this.
    """
    return {"message": "DPP Management Platform is running!", "timestamp": datetime.utcnow()}

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(role_checker(Role.ADMIN))
):
    """
    Checks the health of the API and Database connection.
    Only Admins can access this.
    """
    try:
        # Execute a simple query to check DB connection
        result = await db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "detail": str(e)
        }


@router.get("/logs")
async def get_system_logs(current_user=Depends(role_checker(Role.ADMIN))):
    """
    Returns the last 50 log lines from the backend log file.
    Only Admins can access this.
    """
    if not LOG_FILE_PATH or not os.path.exists(LOG_FILE_PATH):
        return {"logs": ["Log file not found or not configured."]}

    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as file:
            lines = file.readlines()[-50:]
        return {"logs": [line.strip() for line in lines]}
    except Exception as e:
        return {"logs": [f"Error reading logs: {str(e)}"]}


@router.get("/config")
async def get_system_config(current_user=Depends(role_checker(Role.ADMIN))):
    """
    Returns safe system configuration details (excluding secrets and passwords).
    Only Admins can access this.
    """
    return {
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "host": settings.APP_HOST,
        "port": settings.APP_PORT,
        "database": {
            "host": settings.POSTGRES_SERVER,
            "port": settings.POSTGRES_PORT,
            "name": settings.POSTGRES_DB,
            "user": settings.POSTGRES_USER,
        },
        "logging": {
            "level": settings.LOG_LEVEL,
        },
        "jwt": {
            "algorithm": settings.ALGORITHM,
            "token_expiry_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        },
        "last_checked": datetime.utcnow().isoformat(),
    }
