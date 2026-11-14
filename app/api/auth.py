import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from app.database.mongo import users_col, MongoUser
from app.core.security import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user

auth_router = APIRouter(prefix="/api/auth", tags=["Auth"])

class RegisterSchema(BaseModel):
    email: EmailStr
    password: str

@auth_router.post("/signup")
async def signup(payload: RegisterSchema):
    col = users_col()
    existing = await col.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered")

    new_user_id = str(uuid.uuid4())
    user_doc = {
        "_id": new_user_id,
        "email": payload.email,
        "hashed_password": hash_password(payload.password),
        "created_at": datetime.utcnow()
    }
    await col.insert_one(user_doc)
    return {"message": "Account created successfully", "user_id": new_user_id}

@auth_router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    col = users_col()
    user = await col.find_one({"email": form_data.username})
    if not user or not verify_password(form_data.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token({"sub": str(user["_id"]), "email": user["email"]})
    return {"access_token": token, "token_type": "bearer", "email": user["email"]}

@auth_router.get("/me")
async def get_me(current_user: MongoUser = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email
    }
