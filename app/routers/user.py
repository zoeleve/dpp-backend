from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, PasswordUpdate
from app.utils.security import hash_password
from app.utils.auth import role_checker
from app.db.database_postgre import get_db
from app.configs.roles import Role, UserSubRole
from sqlalchemy import select

router = APIRouter(prefix="/users", tags=["Users"])

# ---------------------------------------------------------------------
# READ USERS
# ---------------------------------------------------------------------
@router.get("/all", response_model=List[UserResponse])
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    return result.scalars().all()


@router.get("/paginated", response_model=List[UserResponse])
async def get_paginated_users(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """
    Return users in paginated form.
    Example:
      /users/paginated?skip=0&limit=10
    """
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get user details by ID."""
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
):
    """
    Filter users dynamically based on role, subrole, email, or username.
    Example:
      /users/filter?role=technician
      /users/filter?email=@core-innovation.eu
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
# CREATE USER
# ---------------------------------------------------------------------
@router.post("/", response_model=UserResponse)
async def create_user(
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(None),
    password: str = Form(...),
    role: Role = Form(Role.USER),
    subrole: Optional[UserSubRole] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user."""
    result = await db.execute(select(User).filter(User.email == email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    if subrole == "" or role in [Role.ADMIN, Role.VIEWER]:
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
# UPDATE USER INFO
# ---------------------------------------------------------------------
@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate, db: AsyncSession = Depends(get_db)):
    """Update a user's information."""
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
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------
# UPDATE PASSWORD
# ---------------------------------------------------------------------
@router.put("/{user_id}/password")
async def update_password(user_id: int, pw_update: PasswordUpdate, db: AsyncSession = Depends(get_db)):
    """Change a user's password."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(pw_.new_password)
    await db.commit()
    return {"message": f"Password updated successfully for user ID {user_id}."}


# ---------------------------------------------------------------------
# DELETE USER
# ---------------------------------------------------------------------
@router.delete("/{user_id}")
async def delete_user(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        current_user=Depends(role_checker("admin"))
    ):
    """Delete a user by ID."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return {"message": f"User with ID {user_id} deleted successfully."}
