import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from app.db.database_postgre import get_db
from app.configs.config import settings
from app.utils.auth import role_checker
from app.utils.logger import LOG_FILE_PATH

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/")
def read_root():
    return {"message": "DPP Management Platform is running!"}

@router.get("/ping-db")
def ping_db(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1"))
        return {"status": "connected", "result": [tuple(row) for row in result]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/logs")
def get_system_logs(current_user=Depends(role_checker("admin"))):
    """
    Returns the last 50 log lines from the backend log file.
    """
    if not os.path.exists(LOG_FILE_PATH):
        return {"logs": ["No logs found."]}

    with open(LOG_FILE_PATH, "r") as file:
        lines = file.readlines()[-50:]

    return {"logs": [line.strip() for line in lines]}


@router.get("/config")
def get_system_config(current_user=Depends(role_checker("admin"))):
    """
    Returns safe system configuration details (excluding secrets and passwords).
    """
    return {
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "host": settings.app_host,
        "port": settings.app_port,
        "database": {
            "host": settings.db_host,
            "port": settings.db_port,
            "name": settings.db_name,
            "user": settings.db_user,
        },
        "logging": {
            "level": settings.log_level,
        },
        "jwt": {
            "algorithm": settings.algorithm,
            "token_expiry_minutes": settings.access_token_expire_minutes,
        },
        "last_checked": datetime.utcnow().isoformat(),
    }