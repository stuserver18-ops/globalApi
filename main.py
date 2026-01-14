from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from app.server_manager.port_manager.port_manager_crud import router as portManager_router
from app.server_manager.server_management_user import router as ServerManagementUser_router
from app.shared import router as shared_router
from app.systemd.systemd import router as systemd_router
from app.server_manager.file_manager.router import router as filemanager_router  # ✅ NEW ROUTER

# Import WebSocket handlers
from app.server_manager import hardware_ws
from app.systemd.systemd_ws import live_service_status, live_service_logs


app = FastAPI(title="Multi-App API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API routers
app.include_router(portManager_router, prefix="/api/portManager", tags=["PortManager"])
app.include_router(ServerManagementUser_router, prefix="/api/ServerManagerUser", tags=["ServerManagerUser"])
app.include_router(shared_router, prefix="/api/shared", tags=["Shared"])
app.include_router(systemd_router, prefix="/api/systemd", tags=["Systemd"])
app.include_router(filemanager_router, prefix="/api/filemanager", tags=["Filemanager"])  # ✅ NEW ROUTER

# Hardware WebSocket endpoints
@app.websocket("/hardware/cpu")
async def cpu_ws(websocket: WebSocket):
    await hardware_ws.websocket_endpoint(websocket, "cpu")

@app.websocket("/hardware/memory")
async def memory_ws(websocket: WebSocket):
    await hardware_ws.websocket_endpoint(websocket, "memory")

@app.websocket("/hardware/disk")
async def disk_ws(websocket: WebSocket):
    await hardware_ws.websocket_endpoint(websocket, "disk")

@app.websocket("/hardware/network")
async def network_ws(websocket: WebSocket):
    await hardware_ws.websocket_endpoint(websocket, "network")

# Systemd WebSocket endpoints
@app.websocket("/systemd/services/{service_id}/status/live")
async def systemd_status_ws(websocket: WebSocket, service_id: int):
    await live_service_status(websocket, service_id)

@app.websocket("/systemd/services/{service_id}/logs/live")
async def systemd_logs_ws(websocket: WebSocket, service_id: int):
    await live_service_logs(websocket, service_id)

# Startup event
@app.on_event("startup")
async def startup_event():
    hardware_ws.start_broadcasts()