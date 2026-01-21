# utils/router_logger.py

import logging
from typing import Optional
from fastapi import Request, WebSocket

# -----------------------
# Base logger configuration
# -----------------------
def configure_logger(name: Optional[str] = None):
    logger = logging.getLogger(name or "router_logger")
    logger.setLevel(logging.INFO)

    # Prevent adding multiple handlers if logger is reused
    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


# -----------------------
# Public function
# -----------------------
def get_router_logger(name: Optional[str] = None):
    return configure_logger(name)


# -----------------------
# Helper functions
# -----------------------
def log_request(request: Request):
    """
    Log a standard HTTP request
    """
    client_host = request.client.host if request.client else "unknown"
    method = request.method
    url = request.url.path
    logger = get_router_logger()
    logger.info(f"[HTTP] {method} {url} from {client_host}")


async def log_ws_connection(websocket: WebSocket):
    """
    Log a websocket connection
    """
    client_host = websocket.client.host if websocket.client else "unknown"
    path = websocket.url.path
    logger = get_router_logger()
    logger.info(f"[WS] Client connected to {path} from {client_host}")


async def log_ws_disconnection(websocket: WebSocket):
    """
    Log a websocket disconnection
    """
    client_host = websocket.client.host if websocket.client else "unknown"
    path = websocket.url.path
    logger = get_router_logger()
    logger.info(f"[WS] Client disconnected from {path} ({client_host})")
