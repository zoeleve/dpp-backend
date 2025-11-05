from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, PasswordUpdate
from app.utils.security import hash_password
from app.utils.auth import role_checker
from app.db.database_postgre import get_db
from app.configs.roles import Role, UserSubRole

router = APIRouter(prefix="/users", tags=["Users"])

# ---------------------------------------------------------------------
# READ USERS
# ---------------------------------------------------------------------
@router.get("/all", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.get("/paginated", response_model=List[UserResponse])
def get_paginated_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    Return users in paginated form.
    Example:
      /users/paginated?skip=0&limit=10
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    """Get user details by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/filter", response_model=List[UserResponse])
def filter_users(
    role: Optional[Role] = None,
    subrole: Optional[UserSubRole] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Filter users dynamically based on role, subrole, email, or username.
    Example:
      /users/filter?role=technician
      /users/filter?email=@core-innovation.eu
    """
    query = db.query(User)

    if role:
        query = query.filter(User.role == role.value)
    if subrole:
        query = query.filter(User.subrole == subrole.value)
    if email:
        query = query.filter(User.email.ilike(f"%{email}%"))
    if username:
        query = query.filter(User.username.ilike(f"%{username}%"))

    return query.all()


# ---------------------------------------------------------------------
# CREATE USER
# ---------------------------------------------------------------------
@router.post("/", response_model=UserResponse)
def create_user(
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(None),
    password: str = Form(...),
    role: Role = Form(Role.USER),
    subrole: Optional[UserSubRole] = Form(None),
    db: Session = Depends(get_db),
):
    """Create a new user."""
    existing_user = db.query(User).filter(User.email == email).first()
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
    db.commit()
    db.refresh(new_user)
    return new_user


# ---------------------------------------------------------------------
# UPDATE USER INFO
# ---------------------------------------------------------------------
@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Update a user's information."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_update.email:
        existing_email = db.query(User).filter(User.email == user_update.email, User.id != user_id).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already in use")

    # Update fields dynamically
    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------
# UPDATE PASSWORD
# ---------------------------------------------------------------------
@router.put("/{user_id}/password")
def update_password(user_id: int, pw_update: PasswordUpdate, db: Session = Depends(get_db)):
    """Change a user's password."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(pw_update.new_password)
    db.commit()
    return {"message": f"Password updated successfully for user ID {user_id}."}


# ---------------------------------------------------------------------
# DELETE USER
# ---------------------------------------------------------------------
@router.delete("/{user_id}")
def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(role_checker("admin"))
    ):
    """Delete a user by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": f"User with ID {user_id} deleted successfully."}