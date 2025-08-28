from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routers import health, transactions, auth, accounts, reporting, categorization, categories

app = FastAPI(title="Finance Backend", version="0.1.0")

# CORS (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(reporting.router, prefix="/api", tags=["reporting"])
app.include_router(categorization.router, prefix="/api", tags=["categorization"])
app.include_router(categories.router, prefix="/api", tags=["categories"])
