from fastapi import APIRouter, HTTPException, Request, Depends
from utils.router_logger import get_router_logger

# -----------------------
# Router setup
# -----------------------
router = APIRouter()
APP_NAME = "portChecker"

logger = get_router_logger(APP_NAME)

# -----------------------
# Error logging dependency
# -----------------------
async def log_router_errors(request: Request):
    try:
        yield
    except Exception as exc:
        logger.error(
            f"{request.method} {request.url.path} | {exc}",
            exc_info=True
        )
        raise

# -----------------------
# Routes
# -----------------------
@router.get("/status", dependencies=[Depends(log_router_errors)])
async def status():
    return {"status": "API running"}

