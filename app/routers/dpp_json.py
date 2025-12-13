# app/routers/dpp_json.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database_postgre import get_db
from app.models.dpp import DPP
from app.models.user import User
from app.schemas.dpp import (
    DPPCreate,
    DPPUpdate,
    DPPResponse,
    DPPStatus,
    SearchSchema,
    SearchResponse,
    SearchMode
)
from app.utils.jwt_handler import get_current_active_user
from app.utils.dpp_search_engine import search_dpps
from loguru import logger

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


@router.put("/{dpp_id}/publish", response_model=DPPStatus)
async def publish_dpp(
        dpp_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Publishes a DPP, making it discoverable via search by non-owners.
    Only the DPP owner can perform this action.
    """
    dpp = await db.get(DPP, dpp_id)
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP not found")
    if dpp.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to publish this DPP")

    if dpp.is_published:
        return DPPStatus(
            dpp_uuid=dpp.dpp_uuid,
            is_published=True,
            message="DPP is already published. Status not changed."
        )

    dpp.is_published = True
    db.add(dpp)
    await db.commit()
    await db.refresh(dpp)

    return DPPStatus(
        dpp_uuid=dpp.dpp_uuid,
        is_published=True,
        message="DPP successfully published."
    )


@router.put("/{dpp_id}/unpublish", response_model=DPPStatus)
async def unpublish_dpp(
        dpp_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Unpublishes a DPP, hiding it from non-owner search results.
    Only the DPP owner can perform this action.
    """
    dpp = await db.get(DPP, dpp_id)
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP not found")
    if dpp.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to unpublish this DPP")

    if not dpp.is_published:
        return DPPStatus(
            dpp_uuid=dpp.dpp_uuid,
            is_published=False,
            message="DPP is already unpublished. Status not changed."
        )

    dpp.is_published = False
    db.add(dpp)
    await db.commit()
    await db.refresh(dpp)

    return DPPStatus(
        dpp_uuid=dpp.dpp_uuid,
        is_published=False,
        message="DPP successfully unpublished."
    )


@router.delete("/{dpp_id}")
def delete_dpp(dpp_id: int, db: Session = Depends(get_db)):
    dpp = db.query(DPP).filter(DPP.id == dpp_id).first()
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP not found")
    db.delete(dpp)
    db.commit()
    return {"detail": f"DPP {dpp_id} deleted successfully"}


@router.post("/search", response_model=SearchResponse)
async def search_dpp_entries(
        search_data: SearchSchema,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    """
    Performs search across DPP entries supporting Simple, Advanced, and SPARQL modes.
    Access control (is_published vs. owner_id) is applied automatically.
    """

    if search_data.search_mode == SearchMode.SPARQL:
        # --- SPARQL Search Mode ---
        # NOTE: This part requires the Semantic Web setup (Jena Fuseki connection)
        try:
            # Placeholder for SPARQL client implementation
            return SearchResponse(
                total_count=0,
                limit=search_data.limit,
                offset=search_data.offset,
                results=[],
            )
        except Exception as e:
            logger.exception("SPARQL Query Execution Failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"SPARQL Query Execution Failed: {str(e)}"
            )

    else:
        # --- Simple or Advanced Search Mode (PostgreSQL/JSONB) ---
        try:
            dpps, total_count = await search_dpps(db, search_data, current_user)

            # Map DPP SQLAlchemy objects to DPPResponse Pydantic schemas
            response_results = [DPPResponse.from_orm(dpp) for dpp in dpps]

            return SearchResponse(
                total_count=total_count,
                limit=search_data.limit,
                offset=search_data.offset,
                results=response_results
            )

        except ValueError as e:
            logger.warning(f"Search failed with ValueError: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.exception("An unexpected error occurred during database search.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during database search."
            )



