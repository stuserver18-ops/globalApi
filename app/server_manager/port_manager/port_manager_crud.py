from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from crud import add, update, delete, get
from datetime import datetime
import sys
import subprocess
import socket

from utils.router_logger import get_router_logger

router = APIRouter()
APP_NAME = "portManager"

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
# Schemas
# -----------------------
class PortCreate(BaseModel):
    name: str
    http_port: int
    https_port: Optional[int] = None


class PortUpdate(BaseModel):
    name: Optional[str] = None
    http_port: Optional[int] = None
    https_port: Optional[int] = None


# -----------------------
# PORTS CRUD
# -----------------------

@router.get("/ports", dependencies=[Depends(log_router_errors)])
async def get_ports():
    rows = get("ports", app_name=APP_NAME, limit=None)
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "http_port": r["http_port"],
            "https_port": r.get("https_port"),
            "created_at": r["created_at"],
        }
        for r in rows
    ] if rows else []


@router.post("/ports", status_code=201, dependencies=[Depends(log_router_errors)])
async def create_port(port: PortCreate):
    if not (1 <= port.http_port <= 65535):
        raise HTTPException(status_code=400, detail="Invalid HTTP port")

    if port.https_port is not None and not (1 <= port.https_port <= 65535):
        raise HTTPException(status_code=400, detail="Invalid HTTPS port")

    created_at = datetime.utcnow().isoformat()

    port_id = add(
        "ports",
        {
            "name": port.name,
            "http_port": port.http_port,
            "https_port": port.https_port,
            "created_at": created_at,
        },
        app_name=APP_NAME,
    )

    return {
        "id": port_id,
        "name": port.name,
        "http_port": port.http_port,
        "https_port": port.https_port,
        "created_at": created_at,
    }


@router.put("/ports/{port_id}", dependencies=[Depends(log_router_errors)])
async def update_port(port_id: int, port: PortUpdate):
    existing = get(
        "ports",
        where="id=%s",
        params=(port_id,),
        app_name=APP_NAME,
    )

    if not existing:
        raise HTTPException(status_code=404, detail="Port not found")

    existing = existing[0]

    if port.http_port is not None and not (1 <= port.http_port <= 65535):
        raise HTTPException(status_code=400, detail="Invalid HTTP port")

    if port.https_port is not None and not (1 <= port.https_port <= 65535):
        raise HTTPException(status_code=400, detail="Invalid HTTPS port")

    updated_data = {
        "name": port.name or existing["name"],
        "http_port": port.http_port if port.http_port is not None else existing["http_port"],
        "https_port": port.https_port if port.https_port is not None else existing.get("https_port"),
    }

    rows_updated = update(
        "ports",
        updated_data,
        where="id=%s",
        params=(port_id,),
        app_name=APP_NAME,
    )

    return {
        "success": rows_updated > 0,
        "port": {**existing, **updated_data},
    }


@router.delete("/ports/{port_id}", dependencies=[Depends(log_router_errors)])
async def delete_port(port_id: int):
    existing = get(
        "ports",
        columns=["id"],
        where="id=%s",
        params=(port_id,),
        app_name=APP_NAME,
    )

    if not existing:
        raise HTTPException(status_code=404, detail="Port not found")

    rows_deleted = delete(
        "ports",
        where="id=%s",
        params=(port_id,),
        app_name=APP_NAME,
    )

    return {"success": rows_deleted > 0}


@router.get("/check-port/{port}", dependencies=[Depends(log_router_errors)])
async def check_port(port: int):
    if port <= 0 or port > 65535:
        raise HTTPException(status_code=400, detail="Invalid port")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)

    try:
        s.bind(("127.0.0.1", port))
        s.close()
        return {"available": True}

    except OSError:
        used_by = "Unknown process"

        try:
            if sys.platform.startswith("win"):
                cmd = f'netstat -ano | findstr :{port}'
                output = subprocess.check_output(cmd, shell=True, text=True)
                pid = output.strip().split()[-1]

                name_cmd = f'tasklist /FI "PID eq {pid}" /FO CSV /NH'
                name_out = subprocess.check_output(name_cmd, shell=True, text=True)
                used_by = name_out.split(',')[0].replace('"', '') + f" (PID {pid})"

            else:
                pid = subprocess.check_output(
                    f"lsof -i :{port} -t",
                    shell=True,
                    text=True
                ).strip()

                name = subprocess.check_output(
                    f"ps -p {pid} -o comm=",
                    shell=True,
                    text=True
                ).strip()

                used_by = f"{name} (PID {pid})"

        except Exception:
            # Any failure here is logged automatically
            pass

        return {"available": False, "usedBy": used_by}
