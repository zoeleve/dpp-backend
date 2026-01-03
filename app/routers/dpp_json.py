# app/routers/dpp_json.py
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from app.db.database_postgre import get_db
from app.models.dpp import DPP
from app.models.user import User
from app.configs.roles import Role
from app.schemas.dpp import (
    DPPCreate,
    DPPUpdate,
    DPPResponse,
    DPPStatus,
    DPPStats,
    SearchSchema,
    SearchResponse,
    SearchMode
)
from app.utils.jwt_handler import get_current_active_user
from app.utils.dpp_search_engine import search_dpps
from loguru import logger

router = APIRouter(prefix="/dpp/json", tags=["DPP JSON"])

@router.get("/stats", response_model=DPPStats)
async def get_dpp_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Returns statistics for DPPs visible to the current user.
    """
    
    # 1. Published DPPs (Visible to everyone)
    published_query = select(func.count()).select_from(DPP).where(DPP.is_published == True)
    published_count = (await db.execute(published_query)).scalar_one()

    # 2. Draft DPPs (Visibility depends on role)
    if current_user.role == Role.ADMIN:
        # Admin sees ALL drafts
        draft_query = select(func.count()).select_from(DPP).where(DPP.is_published == False)
    else:
        # Regular users only see THEIR OWN drafts
        draft_query = select(func.count()).select_from(DPP).where(
            and_(DPP.is_published == False, DPP.owner_id == current_user.id)
        )
    draft_count = (await db.execute(draft_query)).scalar_one()

    # 3. Total DPPs (Visible)
    # Logic: Total = Published + Visible Drafts
    if current_user.role == Role.ADMIN:
        total_query = select(func.count()).select_from(DPP)
    else:
        total_query = select(func.count()).select_from(DPP).where(
            or_(
                DPP.is_published == True,
                DPP.owner_id == current_user.id
            )
        )
    total_count = (await db.execute(total_query)).scalar_one()

    # 4. My DPPs (Owned by current user, regardless of status)
    my_dpps_query = select(func.count()).select_from(DPP).where(DPP.owner_id == current_user.id)
    my_dpps_count = (await db.execute(my_dpps_query)).scalar_one()

    return DPPStats(
        total_dpps=total_count,
        published_dpps=published_count,
        draft_dpps=draft_count,
        my_dpps=my_dpps_count
    )

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

    # Check if DPP with the same UUID already exists
    existing_dpp = await db.execute(select(DPP).where(DPP.dpp_uuid == dpp_uuid))
    if existing_dpp.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A DPP with Product ID '{dpp_uuid}' already exists."
        )
    
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
    
    # Access Control: Admin can see everything, others check ownership/published status
    if current_user.role != Role.ADMIN:
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

    # Ownership Check: Only owner or Admin can edit
    if current_user.role != Role.ADMIN and dpp.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this DPP")

    update_dict = update_data.dict(exclude_unset=True)

    # Handle specific column updates
    if "title" in update_dict:
        dpp.title = update_dict.pop("title")
    if "product_id" in update_dict:
        new_uuid = update_dict.pop("product_id")
        # Check if the new UUID already exists (and it's not the current DPP)
        if new_uuid != dpp.dpp_uuid:
            existing_dpp = await db.execute(select(DPP).where(DPP.dpp_uuid == new_uuid))
            if existing_dpp.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"A DPP with Product ID '{new_uuid}' already exists."
                )
        dpp.dpp_uuid = new_uuid

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
    Only the DPP owner or Admin can perform this action.
    """
    dpp = await db.get(DPP, dpp_id)
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP not found")
    
    if current_user.role != Role.ADMIN and dpp.owner_id != current_user.id:
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
    Only the DPP owner or Admin can perform this action.
    """
    dpp = await db.get(DPP, dpp_id)
    if not dpp:
        raise HTTPException(status_code=404, detail="DPP not found")
    
    if current_user.role != Role.ADMIN and dpp.owner_id != current_user.id:
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
    
    # Ownership Check: Only owner or Admin can delete
    if current_user.role != Role.ADMIN and dpp.owner_id != current_user.id:
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
