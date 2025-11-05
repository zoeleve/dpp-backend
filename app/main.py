import sqlalchemy
from fastapi import FastAPI,Depends
from sqlalchemy.orm import Session

from app.configs.config import settings
from app.routers import user, system, auth, dpp_json, dpp_file
from app.db.database_postgre import Base, engine

app = FastAPI(title=settings.app_name)

Base.metadata.create_all(bind=engine)

# Routers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(dpp_json.router)
app.include_router(dpp_file.router)
app.include_router(system.router)


