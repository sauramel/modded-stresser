from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import json
import asyncio

from .config import TARGET_HOST, TARGET_PORT, THREADS, DURATION, API_KEY
from . import mcquery
from .stress import probe_server_for_mods # Import the probe function

# --- Pydantic Models ---
class TaskConfig(BaseModel):
    host: str
    port: int
    threads: int
    duration: int
    mode: str

class QueryRequest(BaseModel):
    host: str
    port: int
    timeout: Optional[int] = 3

# --- In-memory State ---
state: Dict[str, Any] = {
    "running": False,
    "task_config": {
        "host": TARGET_HOST,
        "port": TARGET_PORT,
        "threads": THREADS,
        "duration": DURATION,
        "mode": "login_flood"
    },
    "actors": {},
    "modlist_cache": None # Cache for the modded attack
}

# --- Connection Manager for WebSockets ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_json(self, data: dict):
        message = json.dumps(data, default=str)
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- State Management & Broadcasting ---
async def broadcast_status_update():
    """Broadcasts the current state to all connected WebSocket clients."""
    await manager.broadcast_json({"type": "status_update", "payload": state})

async def broadcast_log(log_data: dict):
    """Broadcasts a single log entry."""
    await manager.broadcast_json({"type": "log", "payload": log_data})

# --- API Key Security ---
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(key: str = Depends(api_key_header)):
    if key == API_KEY:
        return key
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )

# --- FastAPI App ---
app = FastAPI(title="Stresser Controller API", description="Controller for distributed stress tests.")

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- Actor-facing endpoints ---

@app.get("/task")
async def get_task(actor_id: str = "unknown"):
    now = datetime.utcnow()
    if actor_id not in state["actors"]:
        # New actor checked in, broadcast update
        state["actors"][actor_id] = {"last_seen": now.isoformat()}
        await broadcast_status_update()
    else:
        state["actors"][actor_id]["last_seen"] = now.isoformat()

    if state["running"]:
        task_payload = state["task_config"].copy()
        if task_payload["mode"] == "modded_flood":
            task_payload["mod_data"] = state.get("modlist_cache")
        return task_payload
    else:
        return {"mode": "idle"}

@app.post("/log")
async def post_log(data: dict):
    log_line_data = data.copy()
    log_line_data['timestamp'] = datetime.utcnow().isoformat()
    
    # Persist log to file (optional, but good practice)
    actor_id = data.get("actor_id", "unknown")
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"{actor_id}.log"
    with open(log_path, "a") as f:
        f.write(json.dumps(log_line_data) + "\n")
    
    # Push log to UI via WebSocket
    await broadcast_log(log_line_data)
    return {"status": "ok"}

# --- Admin API endpoints ---

@app.get("/api/status", dependencies=[Depends(get_api_key)])
def get_status():
    # This endpoint is now mainly for direct API users,
    # the UI will rely on WebSockets.
    return state

@app.post("/api/query", dependencies=[Depends(get_api_key)])
def query_server(req: QueryRequest):
    """Query a Minecraft server for its status."""
    try:
        query_port = req.port
        query_data = mcquery.query(req.host, query_port, req.timeout)
        return query_data
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"Failed to query server: {e}"}
        )

@app.post("/api/start", dependencies=[Depends(get_api_key)])
async def start_task(config: TaskConfig):
    if state["running"]:
        raise HTTPException(status_code=400, detail="A task is already running.")

    state["task_config"] = config.dict()
    state["modlist_cache"] = None # Clear previous cache

    # For modded flood, probe first
    if config.mode == "modded_flood":
        await broadcast_log({"level": "SYSTEM", "message": f"Probing {config.host}:{config.port} for modlist..."})
        try:
            mod_data = probe_server_for_mods(config.host, config.port)
            state["modlist_cache"] = mod_data
            await broadcast_log({"level": "SUCCESS", "message": f"Probe successful. Found {len(mod_data.get('modinfo', {}).get('modlist', []))} mods."})
        except Exception as e:
            await broadcast_log({"level": "ERROR", "message": f"Failed to probe server for mods: {e}. Aborting."})
            raise HTTPException(status_code=400, detail=f"Failed to probe server for mods: {e}")

    state["running"] = True
    await broadcast_status_update()
    return {"status": "Stress test started", "config": state["task_config"]}

@app.post("/api/stop", dependencies=[Depends(get_api_key)])
async def stop_task():
    state["running"] = False
    await broadcast_status_update()
    return {"status": "Stress test stopped"}

@app.put("/api/config", dependencies=[Depends(get_api_key)])
async def update_config(config: TaskConfig):
    state["task_config"] = config.dict()
    await broadcast_status_update()
    return {"status": "Configuration updated", "new_config": state["task_config"]}

# --- WebSocket Endpoint ---

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send initial state on connect
    await websocket.send_text(json.dumps({"type": "status_update", "payload": state}, default=str))
    try:
        while True:
            # Keep connection alive, all updates are pushed from the server
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- Periodic Actor Pruning ---
async def prune_inactive_actors():
    while True:
        await asyncio.sleep(30)
        now = datetime.utcnow()
        pruned_actors = {
            id: info for id, info in state["actors"].items()
            if (now - datetime.fromisoformat(info["last_seen"])).total_seconds() < 60
        }
        if len(pruned_actors) != len(state["actors"]):
            state["actors"] = pruned_actors
            await broadcast_status_update()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(prune_inactive_actors())

# --- Web UI Endpoint ---

@app.get("/", response_class=FileResponse)
async def read_index():
    index_path = Path(__file__).parent / "static" / "index.html"
    return FileResponse(index_path)
