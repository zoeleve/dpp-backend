from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import zipfile
import os
import json
import xmltodict
from datetime import datetime

from app.db.database_postgre import get_db
from app.models.dpp import DPP
from app.schemas.dpp import DPPBase
from app.utils.validation import filter_non_empty_fields

router = APIRouter(prefix="/dpp/files", tags=["DPP Files"])

UPLOAD_DIR = Path("uploads/aasx")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
async def upload_aasx(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload and process an AASX (or .zip) file, validate fields,
    and store the extracted JSON into the DPP table.
    """
    if not file.filename.endswith((".aasx", ".zip")):
        raise HTTPException(status_code=400, detail="Only .aasx or .zip files are allowed")

    # Save uploaded file
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract the contents
    extract_dir = UPLOAD_DIR / file.filename.replace(".aasx", "").replace(".zip", "")
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    # Locate the main AAS file (xml or json)
    aas_file = None
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.endswith((".xml", ".json")):
                aas_file = Path(root) / f
                break
        if aas_file:
            break

    if not aas_file:
        raise HTTPException(status_code=400, detail="No valid .xml or .json AAS file found inside archive")

    # Parse AAS file
    try:
        if aas_file.suffix == ".xml":
            with open(aas_file, "r", encoding="utf-8") as f:
                data = xmltodict.parse(f.read())
        else:  # JSON file
            with open(aas_file, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing AAS file: {str(e)}")

    # Validate against DPPBase schema
    try:
        validated = DPPBase(**filter_non_empty_fields(data))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Schema validation failed: {str(e)}")

    # Store in DB (unified with /dpp/json)
    new_dpp = DPP(
        product_id=validated.product_id,
        manufacturer=validated.manufacturer,
        model=getattr(validated, "model_number", None),
        data=validated.dict(exclude_none=True),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_dpp)
    db.commit()
    db.refresh(new_dpp)

    return {
        "message": "AASX file processed and stored successfully",
        "filename": file.filename,
        "product_id": new_dpp.product_id,
        "manufacturer": new_dpp.manufacturer
    }
