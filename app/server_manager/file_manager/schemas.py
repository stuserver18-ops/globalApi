from pydantic import BaseModel
from typing import Literal

class RenamePayload(BaseModel):
    new_name: str

class MoveCopyPayload(BaseModel):
    destination: str
