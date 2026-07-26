from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)


class ResearchSessionOut(BaseModel):
    id: str
    query: str
    status: str
    report_json: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Structured report output produced by the Synthesizer Agent ---
class Finding(BaseModel):
    claim: str
    source_url: Optional[str] = None
    confidence: str  # "high" | "medium" | "low"


class ResearchReport(BaseModel):
    executive_summary: str
    key_findings: list[Finding]
    detailed_analysis: str
    gaps_and_uncertainties: list[str]
    sources: list[str]


class KnowledgeChunkOut(BaseModel):
    id: str
    content: str
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True