"""
Security management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ...db.database import get_db
from ...api.dependencies import (
    get_current_active_user, get_current_user_with_mfa,
    require_admin, can_admin_system, can_view_audit_logs,
    get_rbac_service, get_mfa_service, get_audit_service
)
from ...models.user import User
from ...services.rbac_service import RBACService
from ...services.mfa_service import MFAService
from ...services.audit_service import AuditService
from ...models.audit_log import AuditAction, AuditSeverity
from ...schemas.security import (
    RoleCreate, RoleUpdate, RoleResponse,
    PermissionCreate, PermissionResponse,
    UserRoleAssignment, UserPermissionGrant,
    MFASetupResponse, MFAVerifyRequest,
    AuditLogResponse, SecurityEventResponse,
    SecurityDashboardResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)


# RBAC Endpoints
@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(require_admin),
    rbac_service: RBACService = Depends(get_rbac_service),
    audit_service: AuditService = Depends(get_audit_service),
    request: Request = None
):
    """Create a new role (admin only)."""
    try:
        role = rbac_service.create_role(
            name=role_data.name,
            display_name=role_data.display_name,
            description=role_data.description,
            parent_role_id=role_data.parent_role_id
        )
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create role"
            )
        
        # Audit log
        audit_service.log_action(
            action=AuditAction.USER_CREATED,  # Using closest available action
            user_id=str(current_user.id),
            resource_type="role",
            resource_id=str(role.id),
            description=f"Created role: {role.name}",
            request=request
        )
        
        return RoleResponse.from_orm(role)
        
    except Exception as e:
        logger.error(f"Error creating role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/roles", response_model=List[RoleResponse])
async def get_roles(
    current_user: User = Depends(require_admin),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """Get all roles (admin only)."""
    roles = rbac_service.get_all_roles()
    return [RoleResponse.from_orm(role) for role in roles]


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: User = Depends(require_admin),
    rbac_service: RBACService = Depends(get_rbac_service),
    audit_service: AuditService = Depends(get_audit_service),
    request: Request = None
):
    """Update a role (admin only)."""
    role = rbac_service.update_role(
        role_id=role_id,
        display_name=role_data.display_name,
        description=role_data.description,
        is_active=role_data.is_active
    )
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Audit log
    audit_service.log_action(
        action=AuditAction.USER_UPDATED,  # Using closest available action
        user_id=str(current_user.id),
        resource_type="role",
        resource_id=role_id,
        description=f"Updated role: {role.name}",
        request=request
    )
    
    return RoleResponse.from_orm(role)


@router.post("/users/{user_id}/roles")
async def assign_role_to_user(
    user_id: str,
    assignment: UserRoleAssignment,
    current_user: User = Depends(require_admin),
    rbac_service: RBACService = Depends(get_rbac_service),
    audit_service: AuditService = Depends(get_audit_service),
    request: Request = None
):
    """Assign role to user (admin only)."""
    success = rbac_service.assign_role_to_user(
        user_id=user_id,
        role_id=assignment.role_id,
        assigned_by=str(current_user.id)
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to assign role"
        )
    
    # Audit log
    audit_service.log_action(
        action=AuditAction.USER_UPDATED,
        user_id=str(current_user.id),
        resource_type="user_role",
        resource_id=user_id,
        description=f"Assigned role {assignment.role_id} to user {user_id}",
        request=request
    )
    
    return {"message": "Role assigned successfully"}


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role_from_user(
    user_id: str,
    role_id: str,
    current_user: User = Depends(require_admin),
    rbac_service: RBACService = Depends(get_rbac_service),
    audit_service: AuditService = Depends(get_audit_service),
    request: Request = None
):
    """Remove role from user (admin only)."""
    success = rbac_service.remove_role_from_user(user_id, role_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove role"
        )
    
    # Audit log
    audit_service.log_action(
        action=AuditAction.USER_UPDATED,
        user_id=str(current_user.id),
        resource_type="user_role",
        resource_id=user_id,
        description=f"Removed role {role_id} from user {user_id}",
        request=request
    )
    
    return {"message": "Role removed successfully"}


# MFA Endpoints
@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user: User = Depends(get_current_active_user),
    mfa_service: MFAService = Depends(get_mfa_service),
    audit_service: AuditService = Depends(get_audit_service),
    request: Request = None
):
    """Set up MFA for current user."""
    try:
        result = mfa_service.setup_totp(str(current_user.id))
        
        # Audit log
        audit_service.log_action(
            action=AuditAction.MFA_ENABLED,
            user_id=str(current_user.id),
            description="MFA setup initiated",
            request=request
        )
        
        return MFASetupResponse(**result)
        
    except Exception as e:
        logger.error(f"Error setting up MFA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set up MFA"
        )


@router.post("/mfa/verify-setup")
async def verify_mfa_setup(
    verify_request: MFAVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    mfa_service: MFAService = Depends(get_mfa_service),
    audit_service: AuditService = Depends(get_audit_service),
    request: Request = None
):
    """Verify MFA setup."""
    success = mfa_service.verify_totp_setup(
        verify_request.method_id,
        verify_request.code
    )
    
    if not success:
        # Audit failed attempt
        audit_service.log_action(
            action=AuditAction.MFA_ENABLED,
            user_id=str(current_user.id),
            description="MFA setup verification failed",
            success="failure",
            request=request
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Audit successful setup
    audit_service.log_action(
        action=AuditAction.MFA_ENABLED,
        user_id=str(current_user.id),
        description="MFA setup completed successfully",
        request=request
    )
    
    return {"message": "MFA setup verified successfully"}


@router.get("/mfa/methods")
async def get_mfa_methods(
    current_user: User = Depends(get_current_active_user),
    mfa_service: MFAService = Depends(get_mfa_service)
):
    """Get user's MFA methods."""
    methods = mfa_service.get_user_mfa_methods(str(current_user.id))
    return {"methods": methods}


@router.delete("/mfa/methods/{method_id}")
async def disable_mfa_method(
    method_id: str,
    current_user: User = Depends(get_current_user_with_mfa),  # Require MFA for this sensitive operation
    mfa_service: MFAService = Depends(get_mfa_service),
    audit_service: AuditService = Depends(get_audit_service),
    request: Request = None
):
    """Disable MFA method (requires MFA verification)."""
    success = mfa_service.disable_mfa_method(method_id, str(current_user.id))
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to disable MFA method"
        )
    
    # Audit log
    audit_service.log_action(
        action=AuditAction.MFA_DISABLED,
        user_id=str(current_user.id),
        resource_type="mfa_method",
        resource_id=method_id,
        description="MFA method disabled",
        severity=AuditSeverity.HIGH,
        request=request
    )
    
    return {"message": "MFA method disabled successfully"}


# Audit and Monitoring Endpoints
@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    current_user: User = Depends(can_view_audit_logs),
    db: Session = Depends(get_db)
):
    """Get audit logs (admin only)."""
    from ...models.audit_log import AuditLog
    
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    audit_logs = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    
    return [AuditLogResponse.from_orm(log) for log in audit_logs]


@router.get("/security-events", response_model=List[SecurityEventResponse])
async def get_security_events(
    skip: int = 0,
    limit: int = 100,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    current_user: User = Depends(can_view_audit_logs),
    db: Session = Depends(get_db)
):
    """Get security events (admin only)."""
    from ...models.audit_log import SecurityEvent
    
    query = db.query(SecurityEvent)
    
    if severity:
        query = query.filter(SecurityEvent.severity == severity)
    
    if resolved is not None:
        query = query.filter(SecurityEvent.resolved == resolved)
    
    events = query.order_by(SecurityEvent.created_at.desc()).offset(skip).limit(limit).all()
    
    return [SecurityEventResponse.from_orm(event) for event in events]


@router.get("/dashboard", response_model=SecurityDashboardResponse)
async def get_security_dashboard(
    current_user: User = Depends(can_view_audit_logs),
    db: Session = Depends(get_db)
):
    """Get security dashboard data (admin only)."""
    from ...models.audit_log import AuditLog, SecurityEvent
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta
    
    # Get stats for last 24 hours
    last_24h = datetime.utcnow() - timedelta(hours=24)
    
    # Failed login attempts
    failed_logins = db.query(func.count(AuditLog.id)).filter(
        and_(
            AuditLog.action == AuditAction.LOGIN_FAILED,
            AuditLog.timestamp >= last_24h
        )
    ).scalar()
    
    # Security events
    security_events = db.query(func.count(SecurityEvent.id)).filter(
        SecurityEvent.created_at >= last_24h
    ).scalar()
    
    # Unresolved security events
    unresolved_events = db.query(func.count(SecurityEvent.id)).filter(
        SecurityEvent.resolved == False
    ).scalar()
    
    # Active users (logged in last 24h)
    active_users = db.query(func.count(func.distinct(AuditLog.user_id))).filter(
        and_(
            AuditLog.action == AuditAction.LOGIN,
            AuditLog.timestamp >= last_24h
        )
    ).scalar()
    
    return SecurityDashboardResponse(
        failed_logins_24h=failed_logins,
        security_events_24h=security_events,
        unresolved_security_events=unresolved_events,
        active_users_24h=active_users
    )


@router.post("/security-events/{event_id}/resolve")
async def resolve_security_event(
    event_id: str,
    current_user: User = Depends(can_admin_system),
    db: Session = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
    request: Request = None
):
    """Resolve a security event (admin only)."""
    from ...models.audit_log import SecurityEvent
    from datetime import datetime
    
    event = db.query(SecurityEvent).filter(SecurityEvent.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security event not found"
        )
    
    event.resolved = True
    event.resolved_at = datetime.utcnow()
    event.resolved_by = current_user.id
    
    db.commit()
    
    # Audit log
    audit_service.log_action(
        action=AuditAction.SYSTEM_ERROR,  # Using closest available action
        user_id=str(current_user.id),
        resource_type="security_event",
        resource_id=event_id,
        description=f"Resolved security event: {event.event_type}",
        request=request
    )
    
    return {"message": "Security event resolved successfully"}