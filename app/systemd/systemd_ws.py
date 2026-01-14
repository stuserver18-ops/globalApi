# app/systemd_ws.py
import asyncio
import subprocess
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from utils.router_logger import get_router_logger
from .utils import get_service_full_status

JOURNALCTL = "journalctl"
logger = get_router_logger("systemd_ws")


def get_service_active_state(service_name: str) -> str:
    """
    Returns the active state of a systemd service using 'systemctl is-active'.
    Possible outputs: 'active', 'inactive', 'failed', 'unknown', etc.
    """
    try:
        if not service_name or not isinstance(service_name, str):
            return "invalid"

        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        status = result.stdout.strip()
        return status if status else "unknown"
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception:
        return "error"


def get_service_or_404(service_id: int) -> dict:
    APP_NAME = "systemdManager"
    from crud import get
    rows = get(
        table="systemd_services",
        where="id = %s",
        params=(service_id,),
        app_name=APP_NAME
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Service not found")
    return rows[0]


async def live_service_status(websocket: WebSocket, service_id: int):
    await websocket.accept()
    service_name = None
    last_status = None  # Track the last sent status to avoid duplicates

    try:
        service = get_service_or_404(service_id)
        service_name = service["name"]

        while True:
            current_status = get_service_full_status(service_name)

            # Only send if the status has changed
            if current_status != last_status:
                await websocket.send_json({"status": current_status})
                last_status = current_status

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for service {service_name or service_id} status")
    except HTTPException as e:
        logger.warning(f"Service {service_id} access denied: {e.status_code} {e.detail}")
        close_code = 4404 if e.status_code == 404 else 4403
        await websocket.close(code=close_code)
    except Exception as e:
        logger.error(f"Error in live status WebSocket for {service_name or service_id}: {e}", exc_info=True)
        await websocket.close(code=1011)


async def live_service_logs(websocket: WebSocket, service_id: int):
    await websocket.accept()
    service_name = None
    proc = None
    try:
        service = get_service_or_404(service_id)
        service_name = service["name"]

        proc = await asyncio.create_subprocess_exec(
            JOURNALCTL,
            "-u", service_name,
            "-f",
            "--output=short-iso",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        assert proc.stdout is not None

        while True:
            line = await proc.stdout.readline()
            if line:
                decoded_line = line.decode('utf-8', errors='replace').rstrip()
                await websocket.send_text(decoded_line)
            elif proc.returncode is not None:
                break
            else:
                await asyncio.sleep(0.01)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for service {service_name or service_id} logs")
    except HTTPException as e:
        logger.warning(f"Service {service_id} access denied: {e.status_code} {e.detail}")
        close_code = 4404 if e.status_code == 404 else 4403
        await websocket.close(code=close_code)
    except Exception as e:
        logger.error(f"Error in live logs WebSocket for {service_name or service_id}: {e}", exc_info=True)
    finally:
        if proc and proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        await websocket.close()