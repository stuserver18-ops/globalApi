# schemas.py

from pydantic import BaseModel, Field
from typing import Optional

class AllowedRootBase(BaseModel):
    path: str = Field(..., description="Absolute filesystem path")
    description: Optional[str] = Field(None, description="Optional human-readable description")
    is_allowed: bool = Field(True, description="Whether this path is allowed (True) or explicitly blocked (False)")

class AllowedRootCreate(AllowedRootBase):
    # On creation, default is_allowed=True unless specified
    pass

class AllowedRootUpdate(BaseModel):
    path: Optional[str] = Field(None, description="New absolute filesystem path")
    description: Optional[str] = Field(None, description="Updated description")
    is_allowed: Optional[bool] = Field(None, description="Toggle allowed status")

    class Config:
        extra = "forbid"

class AllowedRootResponse(AllowedRootBase):
    id: int

    class Config:
        from_attributes = True