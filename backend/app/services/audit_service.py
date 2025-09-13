"""
Audit logging service for tracking user actions and system events.
"""
import logging
from typing import Optional, Dict, Any, Union
from datetime import datetime
from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..models.audit_log import AuditLog, SecurityEvent, AuditAction, AuditSeverity
from ..models.user import User
from ..db.database import get_db


logger = logging.getLogger(__name__)


class AuditService:
    """Service for creating and managing audit logs."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_action(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        http_method: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.LOW,
        description: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        success: Optional[str] = "success",
        error_message: Optional[str] = None,
        request: Optional[Request] = None
    ) -> Optional[AuditLog]:
        """
        Log a user action or system event.
        
        Args:
            action: The action being performed
            user_id: ID of the user performing the action
            user_email: Email of the user (for deleted users)
            resource_type: Type of resource being acted upon
            resource_id: ID of the resource being acted upon
            ip_address: IP address of the client
            user_agent: User agent string
            endpoint: API endpoint being accessed
            http_method: HTTP method used
            severity: Severity level of the action
            description: Human-readable description
            details: Additional structured data
            success: Whether the action was successful
            error_message: Error message if action failed
            request: FastAPI request object (will extract details automatically)
        
        Returns:
            Created AuditLog instance or None if creation failed
        """
        try:
            # Extract details from request if provided
            if request:
                ip_address = ip_address or self._get_client_ip(request)
                user_agent = user_agent or request.headers.get("user-agent")
                endpoint = endpoint or str(request.url.path)
                http_method = http_method or request.method
            
            # Create audit log entry
            audit_log = AuditLog(
                user_id=user_id,
                user_email=user_email,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                endpoint=endpoint,
                http_method=http_method,
                severity=severity,
                description=description,
                details=details,
                success=success,
                error_message=error_message
            )
            
            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(audit_log)
            
            # Log to application logger as well
            log_level = self._get_log_level(severity)
            logger.log(
                log_level,
                f"Audit: {action.value} by user {user_id or 'anonymous'} "
                f"from {ip_address} - {success}"
            )
            
            return audit_log
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to create audit log: {e}")
            self.db.rollback()
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating audit log: {e}")
            return None
    
    def log_security_event(
        self,
        event_type: str,
        severity: AuditSeverity,
        description: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ) -> Optional[SecurityEvent]:
        """
        Log a security-related event.
        
        Args:
            event_type: Type of security event
            severity: Severity level
            description: Description of the event
            ip_address: IP address involved
            user_agent: User agent string
            user_id: User ID if applicable
            metadata: Additional metadata
            request: FastAPI request object
        
        Returns:
            Created SecurityEvent instance or None if creation failed
        """
        try:
            # Extract details from request if provided
            if request:
                ip_address = ip_address or self._get_client_ip(request)
                user_agent = user_agent or request.headers.get("user-agent")
            
            security_event = SecurityEvent(
                event_type=event_type,
                severity=severity,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent,
                user_id=user_id,
                metadata=metadata
            )
            
            self.db.add(security_event)
            self.db.commit()
            self.db.refresh(security_event)
            
            # Log critical security events immediately
            if severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
                logger.critical(
                    f"Security Event: {event_type} - {description} "
                    f"from {ip_address} (User: {user_id})"
                )
            
            return security_event
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to create security event log: {e}")
            self.db.rollback()
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating security event log: {e}")
            return None
    
    def log_authentication_event(
        self,
        action: AuditAction,
        user_email: str,
        success: bool,
        request: Request,
        user_id: Optional[str] = None,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authentication-related events."""
        severity = AuditSeverity.MEDIUM if not success else AuditSeverity.LOW
        
        self.log_action(
            action=action,
            user_id=user_id,
            user_email=user_email,
            severity=severity,
            description=f"Authentication {action.value} for {user_email}",
            success="success" if success else "failure",
            error_message=error_message,
            details=details,
            request=request
        )
        
        # Log security event for failed authentication
        if not success:
            self.log_security_event(
                event_type="authentication_failure",
                severity=AuditSeverity.MEDIUM,
                description=f"Failed {action.value} attempt for {user_email}",
                user_id=user_id,
                metadata={"error": error_message, "details": details},
                request=request
            )
    
    def log_data_access(
        self,
        resource_type: str,
        resource_id: str,
        action: str,
        user_id: str,
        request: Request,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log data access events."""
        self.log_action(
            action=AuditAction(action) if hasattr(AuditAction, action.upper()) else AuditAction.DASHBOARD_VIEWED,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            description=f"Accessed {resource_type} {resource_id}",
            details=details,
            request=request
        )
    
    def log_sensitive_operation(
        self,
        action: AuditAction,
        user_id: str,
        resource_type: str,
        resource_id: str,
        request: Request,
        details: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ):
        """Log sensitive operations that require special attention."""
        self.log_action(
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            severity=AuditSeverity.HIGH,
            description=description or f"Sensitive operation: {action.value}",
            details=details,
            request=request
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded IP first (behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check other common headers
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _get_log_level(self, severity: AuditSeverity) -> int:
        """Convert audit severity to logging level."""
        severity_map = {
            AuditSeverity.LOW: logging.INFO,
            AuditSeverity.MEDIUM: logging.WARNING,
            AuditSeverity.HIGH: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL
        }
        return severity_map.get(severity, logging.INFO)


# Dependency for getting audit service
def get_audit_service(db: Session = None) -> AuditService:
    """Get audit service instance."""
    if db is None:
        db = next(get_db())
    return AuditService(db)


# Decorator for automatic audit logging
def audit_action(
    action: AuditAction,
    resource_type: Optional[str] = None,
    severity: AuditSeverity = AuditSeverity.LOW,
    description: Optional[str] = None
):
    """
    Decorator for automatic audit logging of function calls.
    
    Usage:
        @audit_action(AuditAction.TRANSACTION_CREATED, "transaction")
        def create_transaction(user_id: str, transaction_data: dict):
            # Function implementation
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This is a simplified version - in practice, you'd need to
            # extract user_id, request, and other details from the function context
            try:
                result = func(*args, **kwargs)
                # Log successful action
                return result
            except Exception as e:
                # Log failed action
                raise e
        return wrapper
    return decorator