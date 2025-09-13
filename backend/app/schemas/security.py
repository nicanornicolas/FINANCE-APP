"""
Security-related Pydantic schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# RBAC Schemas
class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    parent_role_id: Optional[str] = None


class RoleUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class RoleResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    is_system_role: bool
    is_active: bool
    parent_role_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PermissionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)


class PermissionResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    resource: str
    action: str
    is_system_permission: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserRoleAssignment(BaseModel):
    role_id: str


class UserPermissionGrant(BaseModel):
    permission_id: str
    permission_type: str = Field(..., regex="^(grant|deny)$")
    resource_id: Optional[str] = None
    expires_at: Optional[datetime] = None


# MFA Schemas
class MFASetupResponse(BaseModel):
    method_id: str
    secret: str
    qr_code: str
    backup_codes: List[str]
    provisioning_uri: str


class MFAVerifyRequest(BaseModel):
    method_id: str
    code: str = Field(..., min_length=6, max_length=6)


class MFAMethodResponse(BaseModel):
    id: str
    method_type: str
    method_name: Optional[str]
    is_verified: bool
    last_used: Optional[datetime]
    use_count: int
    backup_codes_remaining: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# Audit Schemas
class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str]
    user_email: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    endpoint: Optional[str]
    http_method: Optional[str]
    severity: str
    description: Optional[str]
    details: Optional[Dict[str, Any]]
    success: Optional[str]
    error_message: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class SecurityEventResponse(BaseModel):
    id: str
    event_type: str
    severity: str
    description: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    user_id: Optional[str]
    metadata: Optional[Dict[str, Any]]
    resolved: bool
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SecurityDashboardResponse(BaseModel):
    failed_logins_24h: int
    security_events_24h: int
    unresolved_security_events: int
    active_users_24h: int


# Password Security Schemas
class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str


class PasswordResetRequest(BaseModel):
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str


# Security Settings Schemas
class SecuritySettingsResponse(BaseModel):
    mfa_enabled: bool
    password_last_changed: Optional[datetime]
    last_login: Optional[datetime]
    failed_login_attempts: int
    account_locked: bool
    active_sessions: int


class SecuritySettingsUpdate(BaseModel):
    enable_mfa: Optional[bool] = None
    session_timeout: Optional[int] = Field(None, ge=5, le=480)  # 5 minutes to 8 hours


# API Key Schemas
class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    key_preview: str  # Only show last 4 characters
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


# Security Report Schemas
class SecurityReportRequest(BaseModel):
    start_date: datetime
    end_date: datetime
    report_type: str = Field(..., regex="^(audit|security_events|user_activity)$")
    user_id: Optional[str] = None
    include_details: bool = False


class SecurityReportResponse(BaseModel):
    report_id: str
    report_type: str
    start_date: datetime
    end_date: datetime
    total_records: int
    generated_at: datetime
    download_url: str


# Rate Limiting Schemas
class RateLimitStatus(BaseModel):
    limit: int
    remaining: int
    reset: int
    window: int


class RateLimitExceeded(BaseModel):
    error: str
    limit: int
    reset: int
    retry_after: int


# Vulnerability Assessment Schemas
class VulnerabilityAssessmentResult(BaseModel):
    assessment_id: str
    scan_type: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str  # "running", "completed", "failed"
    vulnerabilities_found: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    report_url: Optional[str]


class VulnerabilityDetail(BaseModel):
    id: str
    severity: str
    title: str
    description: str
    affected_component: str
    recommendation: str
    cve_id: Optional[str]
    cvss_score: Optional[float]
    discovered_at: datetime
    status: str  # "open", "fixed", "accepted_risk"


# Compliance Schemas
class ComplianceCheckResult(BaseModel):
    check_id: str
    check_name: str
    category: str
    status: str  # "pass", "fail", "warning", "not_applicable"
    description: str
    recommendation: Optional[str]
    last_checked: datetime


class ComplianceReport(BaseModel):
    report_id: str
    framework: str  # "SOC2", "PCI_DSS", "GDPR", etc.
    generated_at: datetime
    overall_score: float
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    checks: List[ComplianceCheckResult]