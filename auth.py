from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
import os

SECRET_KEY = os.getenv("JWT_SECRET", "supersecret")  # store in .env
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

def create_token(user_id: str):
    payload = {"sub": user_id}
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
