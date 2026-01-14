from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from crud import add, get, update, delete
from utils.router_logger import get_router_logger
import bcrypt
import uuid

router = APIRouter()
APP_NAME = "server_management"
logger = get_router_logger(APP_NAME)

# -----------------------
# Error logging dependency
# -----------------------
async def log_router_errors(request: Request):
    try:
        yield
    except Exception as exc:
        logger.error(f"{request.method} {request.url.path} | {exc}", exc_info=True)
        raise

# -----------------------
# Schemas
# -----------------------
class UserCreate(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    password: str
    role: Optional[str] = "USER"  # default role

class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

class UserOut(BaseModel):
    id: str
    name: Optional[str]
    email: EmailStr
    role: str
    createdAt: datetime

# -----------------------
# Roles
# -----------------------
ROLES = ["ADMIN", "USER"]

@router.get("/roles", dependencies=[Depends(log_router_errors)])
async def get_roles():
    return ROLES

# -----------------------
# USERS CRUD
# -----------------------

@router.get("/users", response_model=List[UserOut], dependencies=[Depends(log_router_errors)])
async def get_users(
    name: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    role: Optional[str] = Query(None)
):
    """
    Fetch users filtered by name, email, or role. 
    If no filters are provided, returns all users.
    """
    # Fetch all users
    rows = get("User", app_name=APP_NAME, limit=None)

    if not rows:
        return []

    # Filter rows based on query params
    filtered = []
    for r in rows:
        if name and name.lower() not in (r.get("name") or "").lower():
            continue
        if email and email.lower() != r.get("email", "").lower():
            continue
        if role and role.upper() != r.get("role", "USER").upper():
            continue
        filtered.append({
            "id": r["id"],
            "name": r.get("name"),
            "email": r["email"],
            "role": r.get("role", "USER"),
            "createdAt": r["createdAt"],
        })

    return filtered

@router.post("/users", response_model=UserOut, status_code=201, dependencies=[Depends(log_router_errors)])
async def create_user(user: UserCreate):
    # Validate role
    if user.role.upper() not in ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of {ROLES}")

    # Check if user exists
    existing = get("User", where="email=%s", params=(user.email,), app_name=APP_NAME)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # Hash password
    hashed_password = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()

    # Generate UUID for id
    user_id = str(uuid.uuid4())
    createdAt = datetime.utcnow().isoformat()

    add(
        "User",
        {
            "id": user_id,
            "name": user.name,
            "email": user.email,
            "password": hashed_password,
            "role": user.role.upper(),
            "createdAt": createdAt,
        },
        app_name=APP_NAME,
    )

    return {
        "id": user_id,
        "name": user.name,
        "email": user.email,
        "role": user.role.upper(),
        "createdAt": createdAt,
    }


@router.put("/users/{user_id}", response_model=UserOut, dependencies=[Depends(log_router_errors)])
async def update_user(user_id: str, user: UserUpdate):
    existing = get("User", where="id=%s", params=(user_id,), app_name=APP_NAME)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    existing = existing[0]

    updated_role = user.role.upper() if user.role else existing.get("role")
    if updated_role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of {ROLES}")

    updated_data = {
        "name": user.name or existing.get("name"),
        "role": updated_role,
        "password": bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode() if user.password else existing.get("password"),
    }

    rows_updated = update("User", updated_data, where="id=%s", params=(user_id,), app_name=APP_NAME)

    return {**existing, **updated_data}

@router.delete("/users/{user_id}", dependencies=[Depends(log_router_errors)])
async def delete_user(user_id: str):
    existing = get("User", where="id=%s", params=(user_id,), app_name=APP_NAME)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    rows_deleted = delete("User", where="id=%s", params=(user_id,), app_name=APP_NAME)

    return {"success": rows_deleted > 0}