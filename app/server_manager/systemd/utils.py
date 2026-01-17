# systemd_utils.py
import subprocess
from pathlib import Path
from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from utils.router_logger import get_router_logger

# -----------------------
# Constants
# -----------------------
SYSTEMD_DIR = Path("/etc/systemd/system")
SYSTEMCTL = "/usr/bin/systemctl"
JOURNALCTL = "/usr/bin/journalctl"

APP_NAME = "systemdManager"
logger = get_router_logger(APP_NAME)

# -----------------------
# Schemas
# -----------------------
class ServiceCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    description: str
    exec_start: str
    working_directory: Optional[str] = None
    restart: str = "always"


class ServiceUpdate(BaseModel):
    description: Optional[str] = None
    exec_start: Optional[str] = None
    working_directory: Optional[str] = None
    restart: Optional[str] = None


# -----------------------
# Helper Functions
# -----------------------
def run(cmd: list[str]) -> str:
    """Run a system command safely."""
    if cmd[0] == "systemctl":
        cmd[0] = SYSTEMCTL
    if cmd[0] == "journalctl":
        cmd[0] = JOURNALCTL
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except FileNotFoundError:
        raise HTTPException(500, f"{cmd[0]} not found")
    except subprocess.CalledProcessError as e:
        msg = e.stderr.strip() if e.stderr else "Command failed"
        raise HTTPException(400, msg)


def service_file(name: str) -> Path:
    return SYSTEMD_DIR / f"{name}.service"


def reload_systemd():
    run(["systemctl", "daemon-reload"])


def validate_exec_start(cmd: str):
    if not cmd.startswith("/"):
        raise HTTPException(400, "ExecStart must be an absolute path")


def get_service_active_state(name: str) -> str:
    """Get the active state of a systemd service (e.g., active, inactive, failed)."""
    try:
        result = subprocess.run(
            [SYSTEMCTL, "is-active", name],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"
    
def get_service_full_status(service_name: str) -> str:
    """
    Returns the full output of 'systemctl status <service_name>'.
    """
    try:
        if not service_name or not isinstance(service_name, str):
            return "Error: Invalid service name"

        result = subprocess.run(
            ["systemctl", "status", service_name],
            capture_output=True,
            text=True,
            timeout=10  # systemctl status is usually fast, but be safe
        )
        # Return stdout; if failed, include stderr for visibility
        if result.returncode == 0:
            return result.stdout
        else:
            # Often, non-zero just means inactive/failed — still show stdout + hint
            return result.stdout or f"Error: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Timeout while fetching service status"
    except Exception as e:
        return f"Error: {str(e)}"