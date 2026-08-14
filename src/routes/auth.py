from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..auth import Token, UserRegister, create_access_token, pwd_context, verify_password
from ..budget_db_backend import User as UserTable
from ..db import get_session

router = APIRouter(tags=["auth"])


@router.post("/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_session)],
) -> Token:
    # Fetch user details directly from PostgreSQL
    user = db.query(UserTable).filter(UserTable.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserRegister,
    db: Annotated[Session, Depends(get_session)],
) -> None:
    existing_username = db.query(UserTable).filter(UserTable.username == user_in.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already registered."
        )

    # 2. Check if the email is already taken
    existing_email = db.query(UserTable).filter(UserTable.email == user_in.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered."
        )

    # 3. Hash the raw password safely
    hashed_pass = pwd_context.hash(user_in.password)

    # 4. Create the database record
    new_user = UserTable(username=user_in.username, email=user_in.email, password_hash=hashed_pass)

    db.add(new_user)
    return None
