import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
import psutil

clients = {
    "cpu": set(),
    "memory": set(),
    "disk": set(),
    "network": set()
}

# -----------------------
# Metric functions
# -----------------------
async def get_cpu_metrics():
    freq = psutil.cpu_freq()
    cpu_max = freq.max if freq else 0
    cpu_current = freq.current if freq else 0
    cpu_min = freq.min if freq else 0

    temps = psutil.sensors_temperatures()
    temp_values = [t.current for t in temps.get("coretemp", [])]
    temp_max = max(temp_values) if temp_values else 0
    temp_min = min(temp_values) if temp_values else 0
    temp_current = sum(temp_values)/len(temp_values) if temp_values else 0

    return {
        "freq": {"max": cpu_max, "used": cpu_current, "min": cpu_min},
        "temp": temp_current
    }

async def get_memory_metrics():
    mem = psutil.virtual_memory()
    return {
        "memory": {"max": mem.total, "used": mem.used, "min": mem.available},
        "swap": {"max": psutil.swap_memory().total, "used": psutil.swap_memory().used, "min": psutil.swap_memory().free}
    }

async def get_disk_metrics():
    partitions = psutil.disk_partitions()
    disks = []
    for p in partitions:
        try:
            usage = psutil.disk_usage(p.mountpoint)
            disks.append({
                "mountpoint": p.mountpoint,
                "fstype": p.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free
            })
        except PermissionError:
            continue
    return disks  # Each disk has total/used/free (raw numbers)

async def get_network_metrics():
    net_io = psutil.net_io_counters()
    return {
        "network": {"sent": net_io.bytes_sent, "recv": net_io.bytes_recv}
    }

# -----------------------
# Broadcast loop
# -----------------------
async def broadcast(metric_name, get_metric_fn):
    while True:
        if clients[metric_name]:
            data = await get_metric_fn()
            message = json.dumps(data)
            disconnected = set()
            for ws in clients[metric_name]:
                try:
                    await ws.send_text(message)
                except:
                    disconnected.add(ws)
            clients[metric_name].difference_update(disconnected)
        await asyncio.sleep(1)

# -----------------------
# WebSocket handler
# -----------------------
async def websocket_endpoint(websocket: WebSocket, metric_name: str):
    await websocket.accept()
    clients[metric_name].add(websocket)
    print(f"[{metric_name.upper()}] Client connected")
    try:
        while True:
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        pass
    finally:
        clients[metric_name].remove(websocket)
        print(f"[{metric_name.upper()}] Client disconnected")

# -----------------------
# Startup to launch all broadcasters
# -----------------------
def start_broadcasts():
    asyncio.create_task(broadcast("cpu", get_cpu_metrics))
    asyncio.create_task(broadcast("memory", get_memory_metrics))
    asyncio.create_task(broadcast("disk", get_disk_metrics))
    asyncio.create_task(broadcast("network", get_network_metrics))
