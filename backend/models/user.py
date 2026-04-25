"""Pydantic models for User and MFA flows."""
from typing import List, Optional
from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class User(BaseModel):
    id: str
    email: str
    tier: str
    created_at: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    mfa_required: bool = False


# -- MFA models ---------------------------------------------------------------

class MfaSetupResponse(BaseModel):
    totp_uri: str


class MfaVerifyRequest(BaseModel):
    code: str


class MfaChallengeRequest(BaseModel):
    code: str


class MfaDisableRequest(BaseModel):
    password: str
    code: str


class BackupCodesResponse(BaseModel):
    backup_codes: List[str]


class MeResponse(BaseModel):
    id: str
    email: str
    tier: str
    mfa_enabled: bool
    daily_remaining: Optional[int] = None
    daily_limit: Optional[int] = None
    reset_at: Optional[str] = None
    disclaimers_accepted_at: Optional[str] = None
    tos_version: Optional[str] = None
