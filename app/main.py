from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.configs.config import settings
from app.routers import user, system, auth, dpp_json, dpp_file, dpp_sparql, dpp_export
from app.db.database_postgre import Base, engine

app = FastAPI(title=settings.app_name)

# CORS configuration to allow communication with the Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"], # Vite & React default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

# Routers
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(dpp_json.router)
app.include_router(dpp_file.router)
app.include_router(dpp_sparql.router)
app.include_router(dpp_export.router)
app.include_router(system.router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.app_name,
        version="0.1.0",
        description="Digital Product Passport Management Backend",
        routes=app.routes,
    )
    # This part is crucial for removing the old security scheme
    if "components" in openapi_schema and "securitySchemes" in openapi_schema["components"]:
        if "OAuth2PasswordBearer" in openapi_schema["components"]["securitySchemes"]:
            del openapi_schema["components"]["securitySchemes"]["OAuth2PasswordBearer"]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
