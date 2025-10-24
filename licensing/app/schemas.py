from pydantic import BaseModel, Field
from typing import List, Optional


class VerifyRequest(BaseModel):
    product: str = Field(..., examples=["firsttry"])
    key: str = Field(...)


class VerifyResponse(BaseModel):
    valid: bool
    reason: Optional[str] = None
    features: List[str] = []
