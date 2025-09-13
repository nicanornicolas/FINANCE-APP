from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .api.routers import health, transactions, auth, accounts, reporting, categorization, categories, kra_tax, business, integrations, budget, security
from .middleware.security import (
    SecurityHeadersMiddleware, 
    AuditMiddleware, 
    SecurityMonitoringMiddleware,
    RequestSizeLimitMiddleware
)
from .middleware.rate_limiting import rate_limit_middleware
from .core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="Finance Backend", 
    version="0.1.0",
    description="Production-ready financial management platform with KRA tax integration",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Security Middleware (order matters!)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditMiddleware, exclude_paths=["/health", "/docs", "/openapi.json", "/favicon.ico"])
app.add_middleware(SecurityMonitoringMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_size=50 * 1024 * 1024)  # 50MB

# Rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# CORS (adjust origins as needed for production)
allowed_origins = ["*"] if settings.DEBUG else [
    "https://yourdomain.com",
    "https://www.yourdomain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
)

# Initialize RBAC on startup
@app.on_event("startup")
async def startup_event():
    """Initialize default roles and permissions on startup."""
    try:
        from .db.database import get_db
        from .services.rbac_service import RBACService
        
        db = next(get_db())
        rbac_service = RBACService(db)
        rbac_service.initialize_default_roles_and_permissions()
        
        logging.info("Application startup completed successfully")
    except Exception as e:
        logging.error(f"Error during startup: {e}")

# Routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(reporting.router, prefix="/api", tags=["reporting"])
app.include_router(categorization.router, prefix="/api", tags=["categorization"])
app.include_router(categories.router, prefix="/api", tags=["categories"])
app.include_router(kra_tax.router, prefix="/api/kra", tags=["kra-tax"])
app.include_router(business.router, prefix="/api/business", tags=["business"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])
app.include_router(budget.router, prefix="/api", tags=["budget"])
app.include_router(security.router, prefix="/api/security", tags=["security"])
