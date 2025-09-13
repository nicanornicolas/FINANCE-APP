from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List
import jwt
import logging

from ..db.database import get_db
from ..crud import user as crud_user
from ..models.user import User as UserModel
from ..core.config import settings
from ..services.rbac_service import RBACService
from ..services.mfa_service import MFAService
from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditSeverity

security = HTTPBearer()
logger = logging.getLogger(__name__)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    request: Request = None
) -> UserModel:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
            
        # Check if token has MFA verification flag for sensitive operations
        mfa_verified = payload.get("mfa_verified", False)
        
    except jwt.PyJWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        if request:
            audit_service = AuditService(db)
            audit_service.log_authentication_event(
                action=AuditAction.LOGIN_FAILED,
                user_email=email if 'email' in locals() else "unknown",
                success=False,
                request=request,
                error_message="Invalid JWT token"
            )
        raise credentials_exception
    
    user = crud_user.user.get_by_email(db, email=email)
    if user is None:
        if request:
            audit_service = AuditService(db)
            audit_service.log_authentication_event(
                action=AuditAction.LOGIN_FAILED,
                user_email=email,
                success=False,
                request=request,
                error_message="User not found"
            )
        raise credentials_exception
    
    # Store MFA verification status in user object for later use
    user._mfa_verified = mfa_verified
    
    return user


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """Get the current authenticated and active user."""
    if not crud_user.user.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_user_with_mfa(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> UserModel:
    """Get current user and verify MFA if required for sensitive operations."""
    mfa_service = MFAService(db)
    
    # Check if user has MFA enabled
    if mfa_service.user_has_mfa(str(current_user.id)):
        # Check if current token has MFA verification
        if not getattr(current_user, '_mfa_verified', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Multi-factor authentication required for this operation"
            )
    
    return current_user


def require_permission(resource: str, action: str):
    """
    Dependency factory for requiring specific permissions.
    
    Usage:
        @app.get("/transactions")
        async def get_transactions(
            user: UserModel = Depends(require_permission("transaction", "read"))
        ):
            pass
    """
    async def permission_dependency(
        current_user: UserModel = Depends(get_current_active_user),
        db: Session = Depends(get_db),
        request: Request = None
    ) -> UserModel:
        rbac_service = RBACService(db)
        
        # Check permission
        has_permission = rbac_service.check_permission(
            user_id=str(current_user.id),
            resource=resource,
            action=action,
            log_access=True
        )
        
        if not has_permission:
            # Log unauthorized access attempt
            if request:
                audit_service = AuditService(db)
                audit_service.log_action(
                    action=AuditAction.UNAUTHORIZED_ACCESS,
                    user_id=str(current_user.id),
                    user_email=current_user.email,
                    severity=AuditSeverity.HIGH,
                    description=f"Unauthorized access attempt to {resource}:{action}",
                    success="failure",
                    request=request
                )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {resource}:{action}"
            )
        
        return current_user
    
    return permission_dependency


def require_roles(required_roles: List[str]):
    """
    Dependency factory for requiring specific roles.
    
    Usage:
        @app.get("/admin/users")
        async def get_all_users(
            user: UserModel = Depends(require_roles(["admin"]))
        ):
            pass
    """
    async def role_dependency(
        current_user: UserModel = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> UserModel:
        rbac_service = RBACService(db)
        
        # Get user roles
        user_roles = rbac_service.get_user_roles(str(current_user.id))
        user_role_names = [role.name for role in user_roles]
        
        # Check if user has any of the required roles
        has_required_role = any(role in user_role_names for role in required_roles)
        
        if not has_required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(required_roles)}"
            )
        
        return current_user
    
    return role_dependency


async def get_rbac_service(db: Session = Depends(get_db)) -> RBACService:
    """Get RBAC service instance."""
    return RBACService(db)


async def get_mfa_service(db: Session = Depends(get_db)) -> MFAService:
    """Get MFA service instance."""
    return MFAService(db)


async def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    """Get audit service instance."""
    return AuditService(db)


# Common permission dependencies
require_admin = require_roles(["admin"])
require_user_or_admin = require_roles(["user", "admin", "business_user"])
require_business_user = require_roles(["business_user", "admin"])

# Common resource permission dependencies
can_read_transactions = require_permission("transaction", "read")
can_create_transactions = require_permission("transaction", "create")
can_update_transactions = require_permission("transaction", "update")
can_delete_transactions = require_permission("transaction", "delete")
can_import_transactions = require_permission("transaction", "import")

can_read_accounts = require_permission("account", "read")
can_create_accounts = require_permission("account", "create")
can_update_accounts = require_permission("account", "update")
can_delete_accounts = require_permission("account", "delete")

can_generate_reports = require_permission("report", "generate")
can_export_reports = require_permission("report", "export")

can_file_taxes = require_permission("tax", "file")
can_read_tax_data = require_permission("tax", "read")

can_manage_business = require_permission("business", "create")
can_read_business = require_permission("business", "read")
can_update_business = require_permission("business", "update")

can_admin_system = require_permission("system", "admin")
can_view_audit_logs = require_permission("system", "audit")