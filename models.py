"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


class IndustryEnum(str, Enum):
    """Industry options"""
    TECNOLOGIA = "Tecnologia"
    SAUDE = "Saúde"
    EDUCACAO = "Educação"
    VAREJO = "Varejo"
    SERVICOS = "Serviços"
    INDUSTRIA = "Indústria"
    OUTRO = "Outro"


class StatusEnum(str, Enum):
    """Submission status"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


# Request Models

class SubmissionCreate(BaseModel):
    """Lead form submission request with LinkedIn fields for enhanced analysis"""
    name: str
    email: EmailStr
    company: str
    website: Optional[str] = None
    linkedin_company: Optional[str] = None
    linkedin_founder: Optional[str] = None
    industry: IndustryEnum
    challenge: Optional[str] = None

    @field_validator('name', 'company')
    @classmethod
    def validate_min_length(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError('Must be at least 2 characters')
        return v

    @field_validator('challenge')
    @classmethod
    def validate_challenge_length(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 200:
            raise ValueError('Challenge must be maximum 200 characters')
        return v

    @field_validator('email')
    @classmethod
    def validate_corporate_email(cls, v: str) -> str:
        """Ensure email is corporate (not personal)"""
        personal_domains = ['gmail.com', 'hotmail.com', 'outlook.com', 'yahoo.com']
        domain = v.split('@')[1].lower()
        if domain in personal_domains:
            raise ValueError('Please use a corporate email address')
        return v

    @field_validator('website')
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        """Validate website URL format"""
        if v and v.strip():
            if not v.startswith(('http://', 'https://')):
                v = f'https://{v}'
        return v if v and v.strip() else None


# Response Models

class SubmissionResponse(BaseModel):
    """Response after creating a submission"""
    success: bool
    submission_id: Optional[int] = None
    error: Optional[str] = None


class Submission(BaseModel):
    """Full submission model"""
    id: int
    name: str
    email: str
    company: str
    website: Optional[str]
    industry: str
    challenge: Optional[str]
    status: StatusEnum
    report_json: Optional[str]
    error_message: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SubmissionsListResponse(BaseModel):
    """Response for listing submissions"""
    success: bool
    data: Optional[list[Submission]] = None
    error: Optional[str] = None


class ReprocessResponse(BaseModel):
    """Response for reprocess request"""
    success: bool
    error: Optional[str] = None


# AI Analysis Models

class SWOTAnalysis(BaseModel):
    """SWOT Analysis structure"""
    forças: list[str]
    fraquezas: list[str]
    oportunidades: list[str]
    ameaças: list[str]


class PESTELHighlights(BaseModel):
    """PESTEL Analysis highlights"""
    político: str
    econômico: str
    social: str
    tecnológico: str
    ambiental: str
    legal: str


class OKR(BaseModel):
    """OKR structure"""
    objetivo: str
    resultados_chave: list[str]


class AnalysisReport(BaseModel):
    """Complete analysis report structure"""
    diagnostico_estrategico: SWOTAnalysis
    analise_mercado: PESTELHighlights
    oportunidades_identificadas: list[str]
    recomendacoes_prioritarias: list[str]
    proposta_okrs: list[OKR]


# Error Response

class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: str


# Authentication Models

class LoginRequest(BaseModel):
    """Login request with email and password"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User information response"""
    id: str
    email: str


class TokenResponse(BaseModel):
    """Authentication token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginResponse(BaseModel):
    """Login response"""
    success: bool
    data: Optional[TokenResponse] = None
    error: Optional[str] = None


class SignupRequest(BaseModel):
    """Signup request with email and password"""
    email: EmailStr
    password: str


class SignupResponse(BaseModel):
    """Signup response"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


# AI Editor Models

class EditRequest(BaseModel):
    """Request to edit a section of a report"""
    selected_text: str
    section_path: str
    instruction: str
    complexity: Optional[Literal["simple", "complex"]] = None


class EditResponse(BaseModel):
    """Response with suggested edit"""
    success: bool
    suggested_edit: Optional[str] = None
    original_text: Optional[str] = None
    reasoning: Optional[str] = None
    model_used: Optional[str] = None
    complexity: Optional[str] = None
    cost_estimate: Optional[float] = None
    error: Optional[str] = None


class ApplyEditRequest(BaseModel):
    """Request to apply an edit to the report"""
    section_path: str
    new_text: str


class ApplyEditResponse(BaseModel):
    """Response after applying edit"""
    success: bool
    updated_report: Optional[dict] = None
    edit_count: Optional[int] = None
    error: Optional[str] = None


class RegeneratePDFResponse(BaseModel):
    """Response after regenerating PDF"""
    success: bool
    pdf_url: Optional[str] = None
    error: Optional[str] = None
