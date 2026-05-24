from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pathlib import Path
import shutil
import zipfile
import os
import json
from uuid import uuid4
import xmltodict
from datetime import datetime
from loguru import logger
from app.db.database_postgre import get_db
from app.models.dpp import DPP
from app.models.user import User
from app.schemas.dpp import DPPBase
from app.utils.generic_extractor import auto_extract_fields
from app.utils.jwt_handler import get_current_active_user


# --- Logging Configuration to reduce noise ---
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/metrics" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

router = APIRouter(prefix="/dpp/files", tags=["DPP Files"])

UPLOAD_DIR = Path("uploads/aasx")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Define a persistent directory for static files (images, pdfs)
STATIC_DIR = Path("uploads/static")
STATIC_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/static/{dpp_uuid}/{file_path:path}")
async def get_static_file(
    dpp_uuid: str,
    file_path: str,
    current_user: User = Depends(get_current_active_user),
):
    """Serves static files (images, documents) extracted from AASX."""
    file_location = (STATIC_DIR / dpp_uuid / file_path).resolve()
    if not file_location.is_relative_to(STATIC_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid file path")
    if not file_location.exists() or not file_location.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_location)

@router.post("/upload")
async def upload_aasx(
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload and process a .aasx or .zip file containing DPP data.
    The endpoint extracts XML/JSON, validates, and stores unified data in DB.
    """
    safe_filename = Path(file.filename).name
    if not safe_filename.endswith((".aasx", ".zip")):
        raise HTTPException(status_code=400, detail="Only .aasx or .zip files are allowed")

    file_path = UPLOAD_DIR / safe_filename
    unique_suffix = str(uuid4())[:8]
    extract_dir = UPLOAD_DIR / f"{safe_filename.replace('.aasx', '').replace('.zip', '')}_{unique_suffix}"

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # Find a valid AAS XML or JSON file, skipping system-generated ones
        all_files = []
        aas_candidates = []
        for root, _, files in os.walk(extract_dir):
            for f in files:
                full_path = Path(root) / f
                all_files.append(str(full_path.relative_to(extract_dir)))
                if f.endswith((".xml", ".json")) and "Content_Types" not in f and "_rels" not in root:
                    aas_candidates.append(full_path)

        logger.info(f"Files found in archive: {all_files}")

        if not aas_candidates:
            raise HTTPException(status_code=400, detail="No valid .xml or .json AAS file found inside archive")

        aas_file = aas_candidates[0]
        logger.info(f"Selected AAS file for parsing: {aas_file.name}")

        try:
            if aas_file.suffix == ".xml":
                with open(aas_file, "r", encoding="utf-8") as f:
                    data = xmltodict.parse(f.read())
            else:
                with open(aas_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing file: {str(e)}")

        logger.debug(f"Parsed data from {aas_file.name}: {list(data.keys())}")

        extracted_data = auto_extract_fields(data)

        if not extracted_data:
            raise HTTPException(status_code=400, detail="No relevant DPP fields found in uploaded file")

        # Ensure attributes is a dictionary
        if "attributes" not in extracted_data or not isinstance(extracted_data["attributes"], dict):
            extracted_data["attributes"] = {}

        # Move non-core fields into 'attributes' to prevent them from being dropped by Pydantic
        core_fields = {"product_id", "manufacturer", "model_number", "serial_number", "production_date", "submodels", "attributes"}
        keys_to_move = [k for k in extracted_data.keys() if k not in core_fields]
        for k in keys_to_move:
            extracted_data["attributes"][k] = extracted_data.pop(k)

        try:
            validated = DPPBase(**extracted_data)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Schema validation failed: {str(e)}")

        if not validated.product_id or len(validated.product_id.strip()) < 3:
            validated.product_id = f"AUTO-{uuid4().hex[:8]}"
            logger.warning(f"Missing product_id in AASX — generated {validated.product_id}")

        # Generate a safe UUID for the system (DB primary key, folder name)
        # This prevents issues when product_id is a URL or contains special characters
        system_uuid = str(uuid4())

        # Check if DPP with the same Product ID already exists
        # We check both product_identifier (new standard) and dpp_uuid (legacy)
        existing_dpp = await db.execute(select(DPP).where(
            or_(
                DPP.product_identifier == validated.product_id,
                DPP.dpp_uuid == validated.product_id
            )
        ))
        if existing_dpp.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"A DPP with Product ID '{validated.product_id}' already exists."
            )

        # Update file paths in data to point to the static endpoint
        # We need to replace relative paths (e.g. /aasx/logo.png) with API URLs
        normalized_files = {f.replace("\\", "/").strip("/") for f in all_files}
        
        def update_file_paths(data, uuid):
            if isinstance(data, dict):
                for k, v in data.items():
                    data[k] = update_file_paths(v, uuid)
            elif isinstance(data, list):
                for i, v in enumerate(data):
                    data[i] = update_file_paths(v, uuid)
            elif isinstance(data, str):
                # Check if this string looks like one of our extracted files
                clean_val = data.strip().lstrip("/").replace("\\", "/")
                
                # 1. Exact Match
                if clean_val in normalized_files:
                    # Replace with backend static URL
                    return f"/dpp/files/static/{uuid}/{clean_val}"
                
                # 2. Suffix Match (e.g. JSON has "logo.png", ZIP has "aasx/logo.png")
                # Only if it matches exactly one file to avoid ambiguity
                matches = [f for f in normalized_files if f.endswith(clean_val)]
                if len(matches) == 1:
                     return f"/dpp/files/static/{uuid}/{matches[0]}"
            return data

        # Prepare dpp_data from the validated schema
        dpp_data_dict = validated.dict(exclude_none=True)
        # Use system_uuid for file paths so they match the folder we create
        dpp_data_dict = update_file_paths(dpp_data_dict, system_uuid)

        title = f"Imported AAS: {validated.manufacturer or 'Unknown'} {getattr(validated, 'model_number', '')}".strip()

        new_dpp = DPP(
            dpp_uuid=system_uuid,
            title=title,
            owner_id=current_user.id,
            dpp_data=dpp_data_dict,
            product_identifier=validated.product_id,
            is_published=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Move files BEFORE committing: if the move fails, nothing is written to DB
        target_dir = STATIC_DIR / system_uuid
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.move(str(extract_dir), str(target_dir))

        db.add(new_dpp)
        await db.commit()
        await db.refresh(new_dpp)

        logger.info(f"Stored DPP record: {new_dpp.dpp_uuid} ({title})")

        return {
            "message": "AASX file processed and stored successfully",
            "filename": file.filename,
            "parsed_from": aas_file.name,
            "fields_extracted": list(extracted_data.keys()),
            "product_id": validated.product_id, # Return original ID to user
            "dpp_uuid": new_dpp.dpp_uuid,       # Return system UUID
            "manufacturer": validated.manufacturer,
        }
    finally:
        # Cleanup: Delete the uploaded file and the extracted directory
        if file_path.exists():
            file_path.unlink()
        # Only delete extract_dir if it still exists (i.e., wasn't moved to static)
        if extract_dir.exists():
            shutil.rmtree(extract_dir)