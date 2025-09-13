"""
Security middleware for the application.
"""
import time
import logging
from typing import Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..services.audit_service import AuditService
from ..models.audit_log import AuditAction, AuditSeverity
from ..core.config import settings


logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS header for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # CSP header
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        return response


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to audit API requests and responses."""
    
    def __init__(self, app, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/openapi.json", "/favicon.ico"]
    
    async def dispatch(self, request: Request, call_next):
        # Skip audit for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        start_time = time.time()
        
        # Extract request details
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        method = request.method
        path = request.url.path
        
        # Get user ID from token if available
        user_id = None
        try:
            # This would need to be implemented based on your auth system
            # user_id = await self._extract_user_id_from_request(request)
            pass
        except:
            pass
        
        # Process request
        response = None
        error_message = None
        status_code = 200
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            error_message = str(e)
            status_code = 500
            # Re-raise the exception
            raise
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Determine audit action based on method and path
        action = self._determine_audit_action(method, path)
        
        # Determine severity based on status code and path
        severity = self._determine_severity(status_code, path, method)
        
        # Log the request if it's significant
        if action and severity != AuditSeverity.LOW:
            try:
                from ..db.database import get_db
                db = next(get_db())
                audit_service = AuditService(db)
                
                audit_service.log_action(
                    action=action,
                    user_id=user_id,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    endpoint=path,
                    http_method=method,
                    severity=severity,
                    description=f"{method} {path} - {status_code}",
                    success="success" if 200 <= status_code < 400 else "failure",
                    error_message=error_message,
                    details={
                        "status_code": status_code,
                        "process_time": process_time,
                        "response_size": len(response.body) if response and hasattr(response, 'body') else 0
                    }
                )
            except Exception as e:
                logger.error(f"Failed to audit request: {e}")
        
        # Add processing time header
        if response:
            response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
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
    
    def _determine_audit_action(self, method: str, path: str) -> Optional[AuditAction]:
        """Determine audit action based on HTTP method and path."""
        # Authentication endpoints
        if "/auth/login" in path:
            return AuditAction.LOGIN
        elif "/auth/logout" in path:
            return AuditAction.LOGOUT
        elif "/auth/register" in path:
            return AuditAction.USER_CREATED
        
        # Transaction endpoints
        elif "/transactions" in path:
            if method == "POST":
                return AuditAction.TRANSACTION_CREATED
            elif method == "PUT" or method == "PATCH":
                return AuditAction.TRANSACTION_UPDATED
            elif method == "DELETE":
                return AuditAction.TRANSACTION_DELETED
        
        # Account endpoints
        elif "/accounts" in path:
            if method == "POST":
                return AuditAction.ACCOUNT_CREATED
            elif method == "PUT" or method == "PATCH":
                return AuditAction.ACCOUNT_UPDATED
            elif method == "DELETE":
                return AuditAction.ACCOUNT_DELETED
        
        # KRA endpoints
        elif "/kra" in path:
            if "file" in path:
                return AuditAction.TAX_FILING_SUBMITTED
            else:
                return AuditAction.KRA_API_CALL
        
        # Report endpoints
        elif "/reports" in path:
            if "generate" in path:
                return AuditAction.REPORT_GENERATED
            elif "export" in path:
                return AuditAction.REPORT_EXPORTED
        
        # Default for other endpoints
        return None
    
    def _determine_severity(self, status_code: int, path: str, method: str) -> AuditSeverity:
        """Determine audit severity based on status code and endpoint."""
        # Critical endpoints
        if any(critical in path for critical in ["/auth/", "/kra/", "/admin/"]):
            if status_code >= 400:
                return AuditSeverity.HIGH
            else:
                return AuditSeverity.MEDIUM
        
        # Error responses
        if status_code >= 500:
            return AuditSeverity.HIGH
        elif status_code >= 400:
            return AuditSeverity.MEDIUM
        
        # Write operations
        if method in ["POST", "PUT", "PATCH", "DELETE"]:
            return AuditSeverity.MEDIUM
        
        return AuditSeverity.LOW


class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to monitor for security threats and suspicious activity."""
    
    def __init__(self, app):
        super().__init__(app)
        self.suspicious_patterns = [
            # SQL injection patterns
            r"(\bunion\b|\bselect\b|\binsert\b|\bupdate\b|\bdelete\b|\bdrop\b)",
            # XSS patterns
            r"(<script|javascript:|onload=|onerror=)",
            # Path traversal
            r"(\.\./|\.\.\\)",
            # Command injection
            r"(;|\||&|\$\(|\`)",
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Check for suspicious patterns in request
        await self._check_suspicious_activity(request)
        
        # Process request
        response = await call_next(request)
        
        return response
    
    async def _check_suspicious_activity(self, request: Request):
        """Check request for suspicious patterns."""
        import re
        
        # Check URL path
        path = str(request.url.path).lower()
        query = str(request.url.query).lower()
        
        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, path, re.IGNORECASE) or re.search(pattern, query, re.IGNORECASE):
                await self._log_security_event(
                    request,
                    "suspicious_request_pattern",
                    f"Suspicious pattern detected: {pattern}",
                    AuditSeverity.HIGH
                )
                break
        
        # Check for excessive request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
            await self._log_security_event(
                request,
                "large_request_body",
                f"Large request body: {content_length} bytes",
                AuditSeverity.MEDIUM
            )
        
        # Check for suspicious user agents
        user_agent = request.headers.get("user-agent", "").lower()
        suspicious_agents = ["sqlmap", "nikto", "nmap", "masscan", "zap"]
        if any(agent in user_agent for agent in suspicious_agents):
            await self._log_security_event(
                request,
                "suspicious_user_agent",
                f"Suspicious user agent: {user_agent}",
                AuditSeverity.HIGH
            )
    
    async def _log_security_event(
        self,
        request: Request,
        event_type: str,
        description: str,
        severity: AuditSeverity
    ):
        """Log security event."""
        try:
            from ..db.database import get_db
            db = next(get_db())
            audit_service = AuditService(db)
            
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "")
            
            audit_service.log_security_event(
                event_type=event_type,
                severity=severity,
                description=description,
                ip_address=client_ip,
                user_agent=user_agent,
                metadata={
                    "path": str(request.url.path),
                    "method": request.method,
                    "query": str(request.url.query),
                    "headers": dict(request.headers)
                }
            )
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request size."""
    
    def __init__(self, app, max_size: int = 50 * 1024 * 1024):  # 50MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": {
                        "code": "REQUEST_TOO_LARGE",
                        "message": f"Request body too large. Maximum size: {self.max_size} bytes",
                        "details": {
                            "max_size": self.max_size,
                            "received_size": int(content_length)
                        }
                    }
                }
            )
        
        return await call_next(request)