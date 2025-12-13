from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database_postgre import get_db
from app.models.dpp import DPP
from app.models.user import User
from app.utils.jwt_handler import get_current_active_user


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """ Returns hashed code """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ Verify that the plain password matches the hashed one """
    return pwd_context.verify(plain_password, hashed_password)


async def get_dpp_if_owner(
        dpp_id: str,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
) -> DPP:
    """Checks if the connected user is the owner of the DPP."""

    # Assuming dpp_id in URL is the dpp_uuid
    dpp = await db.get(DPP, dpp_id)

    if not dpp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DPP not found."
        )

    if dpp.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to manage this DPP. User is not the owner."
        )

    return dpp