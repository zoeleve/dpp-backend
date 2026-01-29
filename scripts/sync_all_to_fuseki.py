import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.dpp import DPP
from app.configs.config import settings
from app.utils.rdf_converter import convert_dpp_to_rdf
from app.utils.sparql_client import update_fuseki_graph, RDF_BASE_URI

# Load env vars
load_dotenv()

# Database Setup
DATABASE_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

# Disable statement cache for Supabase Transaction Pooler compatibility
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,
    connect_args={"statement_cache_size": 0}
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def sync_all():
    print("🔄 Starting Full Sync to Fuseki...")
    print(f"   Target Fuseki: {settings.FUSEKI_DATA_URL}")
    print(f"   Base URI: {RDF_BASE_URI}")
    
    async with AsyncSessionLocal() as session:
        # Fetch all DPPs
        result = await session.execute(select(DPP))
        dpps = result.scalars().all()
        
        print(f"   Found {len(dpps)} DPPs in Database.")
        
        success_count = 0
        fail_count = 0
        
        for dpp in dpps:
            try:
                target_uri = f"{RDF_BASE_URI}/dpp/{dpp.dpp_uuid}"
                print(f"   - Syncing {dpp.dpp_uuid} -> {target_uri}...", end="")

                rdf_data = convert_dpp_to_rdf(dpp)
                await update_fuseki_graph(dpp.dpp_uuid, rdf_data)
                print(" ✅ OK")
                success_count += 1
            except Exception as e:
                print(f" ❌ FAILED: {e}")
                fail_count += 1
        
        print("\n📊 Sync Complete.")
        print(f"   ✅ Success: {success_count}")
        print(f"   ❌ Failed:  {fail_count}")

if __name__ == "__main__":
    asyncio.run(sync_all())
