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
async def create_dpp(
    dpp: DPPCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    dpp_dict = dpp.dict()
    
    # Extract specific columns
    title = dpp_dict.pop("title")
    dpp_uuid = dpp_dict.pop("product_id")
    
    # The rest of the data goes into the JSONB column
    new_dpp = DPP(
        title=title,
        dpp_uuid=dpp_uuid,
        owner_id=current_user.id,
        dpp_data=dpp_dict,  # Store remaining fields (identification, etc.) here
        is_published=False
    )
    
    db.add(new_dpp)
    await db.commit()
    await db.refresh(new_dpp)
    return new_dpp


@router.get("/{dpp_id}", response_model=DPPResponse)
async def get_dpp(
    dpp_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    dpp = await db.get(DPP, dpp_id)
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP not found")
    
    # Access Control
    if not dpp.is_published and dpp.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this unpublished DPP")

    return dpp


@router.put("/{dpp_id}", response_model=DPPResponse)
async def update_dpp(
    dpp_id: int, 
    update_data: DPPUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    dpp = await db.get(DPP, dpp_id)
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP not found")

    # Ownership Check
    if dpp.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this DPP")

    update_dict = update_data.dict(exclude_unset=True)

    # Handle specific column updates
    if "title" in update_dict:
        dpp.title = update_dict.pop("title")
    if "product_id" in update_dict:
        dpp.dpp_uuid = update_dict.pop("product_id")

    # Merge remaining fields into dpp_data
    if update_dict:
        current_data = dict(dpp.dpp_data) if dpp.dpp_data else {}
        current_data.update(update_dict)
        dpp.dpp_data = current_data

    await db.commit()
    await db.refresh(dpp)
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
async def delete_dpp(
    dpp_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    dpp = await db.get(DPP, dpp_id)
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP not found")
    
    # Ownership Check
    if dpp.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this DPP")

    await db.delete(dpp)
    await db.commit()
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
