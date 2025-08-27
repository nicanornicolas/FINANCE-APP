from fastapi import APIRouter

router = APIRouter(tags=["health"])

@router.get("/healthz")
async def healthcheck():
    return {"status": "ok"}

@router.get("/readyz")
async def readycheck():
    return {"ready": True}
