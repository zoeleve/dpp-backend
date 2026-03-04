from fastapi import APIRouter, Depends, HTTPException, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import EmailStr
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, PasswordUpdate
from app.utils.security import hash_password
from app.utils.auth import role_checker, get_current_user
from app.db.database_postgre import get_db
from app.configs.roles import Role, UserSubRole
from sqlalchemy import select

router = APIRouter(prefix="/users", tags=["Users"])

# ---------------------------------------------------------------------
# READ USERS
# ---------------------------------------------------------------------
@router.get("/all", response_model=List[UserResponse])
async def get_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(role_checker(Role.ADMIN))
):
    """
    Get all users. Only Admins can access this.
    """
    result = await db.execute(select(User))
    return result.scalars().all()


@router.get("/paginated", response_model=List[UserResponse])
async def get_paginated_users(
    skip: int = 0, 
    limit: int = 10, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(role_checker(Role.ADMIN))
):
    """
    Return users in paginated form. Only Admins.
    Example:
      /users/paginated?skip=0&limit=10
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user details by ID. Users can see themselves, Admins can see everyone."""
    
    if current_user.role != Role.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/filter", response_model=List[UserResponse])
async def filter_users(
    role: Optional[Role] = None,
    subrole: Optional[UserSubRole] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(role_checker(Role.ADMIN))
):
    """
    Filter users dynamically. Only Admins.
    """
    query = select(User)

    if role:
        query = query.filter(User.role == role.value)
    if subrole:
        query = query.filter(User.subrole == subrole.value)
    if email:
        query = query.filter(User.email.ilike(f"%{email}%"))
    if username:
        query = query.filter(User.username.ilike(f"%{username}%"))

    result = await db.execute(query)
    return result.scalars().all()


# ---------------------------------------------------------------------
# PUBLIC REGISTRATION (Sign Up)
# ---------------------------------------------------------------------
@router.post("/create", response_model=UserResponse)
async def create_user(
    username: str = Form(...),
    email: EmailStr = Form(...),
    full_name: str = Form(None),
    password: str = Form(...),
    role: Role = Form(Role.USER),
    subrole: Optional[UserSubRole] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Public Sign Up.
    RESTRICTIONS:
    - Cannot create ADMIN accounts.
    - Cannot create MANUFACTURER subroles (requires verification).
    """
    # SECURITY: Prevent Admin creation
    if role == Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Admin creation is not allowed via public registration."
        )
    
    # SECURITY: Prevent Manufacturer creation (optional, but good practice)
    if subrole == UserSubRole.MANUFACTURER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Manufacturer accounts must be created by an Admin."
        )

    result = await db.execute(select(User).filter(User.email == email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    if subrole == "" or role == Role.VIEWER:
        subrole = None

    hashed_pw = hash_password(password)

    new_user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hashed_pw,
        role=role.value,
        subrole=subrole.value if subrole else None,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


# ---------------------------------------------------------------------
# ADMIN USER CREATION
# ---------------------------------------------------------------------
@router.post("/admin/create", response_model=UserResponse)
async def create_user_by_admin(
    username: str = Form(...),
    email: EmailStr = Form(...),
    full_name: str = Form(None),
    password: str = Form(...),
    role: Role = Form(...),
    subrole: Optional[UserSubRole] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(role_checker(Role.ADMIN))
):
    """
    Create ANY user (Admin, Manufacturer, etc.).
    Only accessible by existing Admins.
    """
    result = await db.execute(select(User).filter(User.email == email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(password)

    new_user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hashed_pw,
        role=role.value,
        subrole=subrole.value if subrole else None,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


# ---------------------------------------------------------------------
# UPDATE USER INFO
# ---------------------------------------------------------------------
@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int, 
    user_update: UserUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a user's information. Users can only update their own info, unless admin."""
    
    # Check permissions
    if current_user.id != user_id and current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_update.email:
        result = await db.execute(select(User).filter(User.email == user_update.email, User.id != user_id))
        existing_email = result.scalar_one_or_none()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already in use")

    # Update fields dynamically
    for field, value in user_update.model_dump(exclude_unset=True).items():
        # SECURITY: Prevent users from promoting themselves to ADMIN
        if field == "role" and value == Role.ADMIN and current_user.role != Role.ADMIN:
             raise HTTPException(status_code=403, detail="You cannot promote yourself to Admin.")
             
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------
# UPDATE PASSWORD
# ---------------------------------------------------------------------
@router.put("/{user_id}/password")
async def update_password(
    user_id: int, 
    pw_update: PasswordUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Change a user's password. Users can only change their own password, unless admin."""
    
    # Check permissions
    if current_user.id != user_id and current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user's password")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(pw_update.new_password)
    await db.commit()
    return {"message": f"Password updated successfully for user ID {user_id}."}


# ---------------------------------------------------------------------
# DELETE USER
# ---------------------------------------------------------------------
@router.delete("/{user_id}")
async def delete_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
    """Delete a user by ID. Users can delete themselves. Admins can delete anyone but themselves."""
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Permission Logic
    if current_user.role == Role.ADMIN:
        if current_user.id == user_id:
            raise HTTPException(status_code=400, detail="Admins cannot delete themselves.")
    else:
        # Normal user
        if current_user.id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this user")

    await db.delete(user)
    await db.commit()
    return {"message": f"User with ID {user_id} deleted successfully."}


# ---------------------------------------------------------------------
# UPDATE USER STATUS (ADMIN ONLY)
# ---------------------------------------------------------------------
@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(role_checker(Role.ADMIN))
):
    """
    Activate or Deactivate a user account.
    Only Admins can perform this action.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Admins cannot deactivate themselves.")

    user.is_active = is_active
    await db.commit()
    await db.refresh(user)
    
    status_msg = "activated" if is_active else "deactivated"
    return {"message": f"User {user.username} has been {status_msg}."}
