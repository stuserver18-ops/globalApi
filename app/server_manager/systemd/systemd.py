# systemd_routes.py
import getpass
from fastapi import APIRouter, HTTPException, Request, Depends
from typing import Optional

from crud import add, update, delete, get
from utils.router_logger import get_router_logger
from .utils import (
    run,
    service_file,
    reload_systemd,
    validate_exec_start,
    get_service_active_state,
    ServiceCreate,
    ServiceUpdate,
    SYSTEMD_DIR,
    SYSTEMCTL,
    JOURNALCTL,
)

# -----------------------
# Router setup
# -----------------------
router = APIRouter()
APP_NAME = "systemdManager"
logger = get_router_logger(APP_NAME)

CURRENT_USER = getpass.getuser()


# -----------------------
# Error logging dependency
# -----------------------
async def log_router_errors(request: Request):
    try:
        yield
    except Exception as exc:
        logger.error(f"{request.method} {request.url.path} | {exc}", exc_info=True)
        raise


# -----------------------
# Database helper (router-specific)
# -----------------------
def get_service_or_404(service_id: int) -> dict:
    rows = get(
        table="systemd_services",
        where="id = %s",
        params=(service_id,),
        app_name=APP_NAME
    )
    if not rows:
        raise HTTPException(404, "Service not found")
    return rows[0]


# -----------------------
# CRUD Endpoints
# -----------------------
@router.post("/services", status_code=201, dependencies=[Depends(log_router_errors)])
async def create_service(service: ServiceCreate):
    path = service_file(service.name)
    if path.exists():
        raise HTTPException(409, "Service already exists")

    validate_exec_start(service.exec_start)

    content = [
        "[Unit]",
        f"Description={service.description}",
        "",
        "[Service]",
        f"ExecStart={service.exec_start}",
        f"Restart={service.restart}",
        f"User={CURRENT_USER}",
    ]

    if service.working_directory:
        content.append(f"WorkingDirectory={service.working_directory}")

    content.extend(["", "[Install]", "WantedBy=multi-user.target", ""])

    path.write_text("\n".join(content))
    reload_systemd()

    add(
        table="systemd_services",
        data={
            "name": service.name,
            "description": service.description,
            "exec_start": service.exec_start,
            "user": CURRENT_USER,
            "working_directory": service.working_directory,
            "restart_policy": service.restart,
            "enabled": False,
        },
        app_name=APP_NAME
    )

    return {"success": True, "service": service.name}


@router.put("/services/{service_id}", dependencies=[Depends(log_router_errors)])
async def update_service(service_id: int, service: ServiceUpdate):
    saved = get_service_or_404(service_id)
    path = service_file(saved["name"])

    if service.exec_start is not None:
        validate_exec_start(service.exec_start)

    lines = path.read_text().splitlines()
    updated = []

    for line in lines:
        if service.description is not None and line.startswith("Description="):
            line = f"Description={service.description}"
        elif service.exec_start is not None and line.startswith("ExecStart="):
            line = f"ExecStart={service.exec_start}"
        elif service.restart is not None and line.startswith("Restart="):
            line = f"Restart={service.restart}"
        elif service.working_directory is not None and line.startswith("WorkingDirectory="):
            line = f"WorkingDirectory={service.working_directory}"
        updated.append(line)

    path.write_text("\n".join(updated))
    reload_systemd()

    data = {k: v for k, v in {
        "description": service.description,
        "exec_start": service.exec_start,
        "working_directory": service.working_directory,
        "restart_policy": service.restart,
    }.items() if v is not None}

    if data:
        update(
            table="systemd_services",
            data=data,
            where="id = %s",
            params=(service_id,),
            app_name=APP_NAME
        )

    return {"success": True, "service": saved["name"]}


@router.delete("/services/{service_id}", dependencies=[Depends(log_router_errors)])
async def delete_service(service_id: int):
    service = get_service_or_404(service_id)
    path = service_file(service["name"])

    run(["systemctl", "stop", service["name"]])
    run(["systemctl", "disable", service["name"]])

    if path.exists():
        path.unlink()

    reload_systemd()

    delete(
        table="systemd_services",
        where="id = %s",
        params=(service_id,),
        app_name=APP_NAME
    )

    return {"success": True, "service": service["name"]}


# -----------------------
# Control Endpoints
# -----------------------
@router.post("/services/{service_id}/start")
async def start_service(service_id: int):
    service = get_service_or_404(service_id)
    run(["systemctl", "start", service["name"]])
    return {"status": "started", "service": service["name"]}


@router.post("/services/{service_id}/stop")
async def stop_service(service_id: int):
    service = get_service_or_404(service_id)
    run(["systemctl", "stop", service["name"]])
    return {"status": "stopped", "service": service["name"]}


@router.post("/services/{service_id}/restart")
async def restart_service(service_id: int):
    service = get_service_or_404(service_id)
    run(["systemctl", "restart", service["name"]])
    return {"status": "restarted", "service": service["name"]}


@router.post("/services/{service_id}/enable")
async def enable_service(service_id: int):
    service = get_service_or_404(service_id)
    run(["systemctl", "enable", service["name"]])
    update(
        table="systemd_services",
        data={"enabled": True},
        where="id = %s",
        params=(service_id,),
        app_name=APP_NAME
    )
    return {"status": "enabled", "service": service["name"]}


@router.post("/services/{service_id}/disable")
async def disable_service(service_id: int):
    service = get_service_or_404(service_id)
    run(["systemctl", "disable", service["name"]])
    update(
        table="systemd_services",
        data={"enabled": False},
        where="id = %s",
        params=(service_id,),
        app_name=APP_NAME
    )
    return {"status": "disabled", "service": service["name"]}


# -----------------------
# Status & Logs
# -----------------------
@router.get("/services/{service_id}/status")
async def service_status(service_id: int):
    service = get_service_or_404(service_id)
    output = run(["systemctl", "status", service["name"], "--no-pager"])
    return {"service": service["name"], "status": output}


@router.get("/services/{service_id}/logs")
async def service_logs(
    service_id: int,
    lines: int = 100,
    since: Optional[str] = None,
    until: Optional[str] = None,
):
    service = get_service_or_404(service_id)

    cmd = [
        "journalctl",
        "-u", service["name"],
        f"-n{lines}",
        "--no-pager",
        "--output=short-iso",
    ]

    if since:
        cmd.append(f"--since={since}")
    if until:
        cmd.append(f"--until={until}")

    output = run(cmd)
    return {
        "service": service["name"],
        "lines": lines,
        "logs": output.splitlines()
    }

@router.get("/services/{service_id}/isrunning")
async def is_service_running(service_id: int):
    service = get_service_or_404(service_id)
    active_state = get_service_active_state(service["name"])
    is_running = active_state == "active"
    return {"service": service["name"], "isrunning": is_running}

# -----------------------
# List all services
# -----------------------
@router.get("/services")
async def list_services():
    services = get(table="systemd_services", app_name=APP_NAME)
    enriched = []
    for svc in services:
        status = get_service_active_state(svc["name"])
        enriched.append({**svc, "status": status})
    return {"services": enriched}