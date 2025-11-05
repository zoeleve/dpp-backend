from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database_postgre import get_db
from app.models.dpp import DPP
from app.schemas.dpp import DPPCreate, DPPUpdate, DPPResponse

router = APIRouter(prefix="/dpp/json", tags=["DPP JSON"])

@router.post("/", response_model=DPPResponse)
def create_dpp(dpp: DPPCreate, db: Session = Depends(get_db)):
    # Validation already handled by Pydantic schema
    new_dpp = DPP(**dpp.dict())
    db.add(new_dpp)
    db.commit()
    db.refresh(new_dpp)
    return new_dpp


@router.get("/{dpp_id}", response_model=DPPResponse)
def get_dpp(dpp_id: int, db: Session = Depends(get_db)):
    dpp = db.query(DPP).filter(DPP.id == dpp_id).first()
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP not found")
    return dpp


@router.put("/{dpp_id}", response_model=DPPResponse)
def update_dpp(dpp_id: int, update_data: DPPUpdate, db: Session = Depends(get_db)):
    dpp = db.query(DPP).filter(DPP.id == dpp_id).first()
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP not found")

    # Validate before saving (Pydantic ensures correct schema)
    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(dpp, key, value)

    db.commit()
    db.refresh(dpp)
    return dpp


@router.delete("/{dpp_id}")
def delete_dpp(dpp_id: int, db: Session = Depends(get_db)):
    dpp = db.query(DPP).filter(DPP.id == dpp_id).first()
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP not found")
    db.delete(dpp)
    db.commit()
    return {"detail": f"DPP {dpp_id} deleted successfully"}
