from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import zipfile
import os
import json
import xmltodict
from datetime import datetime
from loguru import logger
from app.db.database_postgre import get_db
from app.models.dpp import DPP
from app.schemas.dpp import DPPBase
from app.utils.generic_extractor import auto_extract_fields


router = APIRouter(prefix="/dpp/files", tags=["DPP Files"])

UPLOAD_DIR = Path("uploads/aasx")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_aasx(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload and process a .aasx or .zip file containing DPP data.
    The endpoint extracts XML/JSON, validates, and stores unified data in DB.
    """
    # ✅ 1. Check file extension
    if not file.filename.endswith((".aasx", ".zip")):
        raise HTTPException(status_code=400, detail="Only .aasx or .zip files are allowed")

    # ✅ 2. Save the uploaded file
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ✅ 3. Extract archive
    extract_dir = UPLOAD_DIR / file.filename.replace(".aasx", "").replace(".zip", "")
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    # ✅ 4. Find a valid AAS XML or JSON file (skip system ones)
    aas_file = None
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.endswith((".xml", ".json")) and "Content_Types" not in f and "_rels" not in root:
                aas_file = Path(root) / f
                break
        if aas_file:
            break

    if not aas_file:
        raise HTTPException(status_code=400, detail="No valid .xml or .json AAS file found inside archive")

    # ✅ 5. Parse the file content
    try:
        if aas_file.suffix == ".xml":
            with open(aas_file, "r", encoding="utf-8") as f:
                data = xmltodict.parse(f.read())
        else:
            with open(aas_file, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing file: {str(e)}")

    logger.debug(f"📄 Parsed data from {aas_file.name}: {list(data.keys())}")

    # ✅ 6. Try to auto-extract DPP fields dynamically
    extracted_data = auto_extract_fields(data)

    if not extracted_data:
        raise HTTPException(status_code=400, detail="No relevant DPP fields found in uploaded file")

    if "attributes" not in extracted_data or extracted_data["attributes"] in ("", None, []):
        extracted_data["attributes"] = {}

    # ✅ 7. Validate extracted data with Pydantic schema
    try:
        validated = DPPBase(**extracted_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Schema validation failed: {str(e)}")

    # ✅ 7.1 Auto-generate product_id if missing
    from uuid import uuid4
    if not validated.product_id or len(validated.product_id.strip()) < 3:
        validated.product_id = f"AUTO-{uuid4().hex[:8]}"
        logger.warning(f"⚠️ Missing product_id in AASX — generated {validated.product_id}")

    # ✅ 8. Store unified data in DB
    new_dpp = DPP(
        product_id=validated.product_id,
        manufacturer=validated.manufacturer,
        model_number=getattr(validated, "model_number", None),
        attributes=validated.dict(exclude_none=True),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(new_dpp)
    db.commit()
    db.refresh(new_dpp)

    logger.info(f"✅ Stored DPP record: {new_dpp.product_id} ({new_dpp.manufacturer})")

    # ✅ 9. Return response
    return {
        "message": "AASX file processed and stored successfully",
        "filename": file.filename,
        "parsed_from": aas_file.name,
        "fields_extracted": list(extracted_data.keys()),
        "product_id": new_dpp.product_id,
        "manufacturer": new_dpp.manufacturer,
    }