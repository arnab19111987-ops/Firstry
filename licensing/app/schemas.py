from typing import List, Optional

from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    product: str = Field(..., examples=["firsttry"])
    key: str = Field(...)


class VerifyResponse(BaseModel):
    valid: bool
    reason: Optional[str] = None
    features: List[str] = []
