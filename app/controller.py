from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import os
import json

from .config import TARGET_HOST, TARGET_PORT, THREADS, DURATION, API_KEY

# --- Pydantic Models ---
class TaskConfig(BaseModel):
    host: str
    port: int
    threads: int
    duration: int
    mode: str  # 'login_flood', 'modded_probe', 'modded_replay'

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
    "actors": {}
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

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

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

# Mount static files for the web UI
static_dir = Path(__file__).parent / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# --- Actor-facing endpoints ---

@app.get("/task")
def get_task(actor_id: str = "unknown"):
    """Endpoint for actors to poll for tasks and report their status."""
    state["actors"][actor_id] = {"last_seen": datetime.utcnow().isoformat()}
    if state["running"]:
        return state["task_config"]
    else:
        return {"mode": "idle"}

@app.post("/log")
async def post_log(data: dict):
    """Endpoint for actors to post logs."""
    actor_id = data.get("actor_id", "unknown")
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"{actor_id}.log"
    
    log_line_data = data.copy()
    log_line_data['timestamp'] = datetime.utcnow().isoformat()
    log_line = json.dumps(log_line_data)

    with open(log_path, "a") as f:
        f.write(log_line + "\n")
    
    await manager.broadcast(log_line)
    return {"status": "ok"}

# --- Admin API endpoints ---

@app.get("/api/status", dependencies=[Depends(get_api_key)])
def get_status():
    """Get the current status, configuration, and active actors."""
    return state

@app.get("/api/actors", dependencies=[Depends(get_api_key)])
def get_actors():
    """Get a list of all actors that have checked in."""
    return state["actors"]

@app.get("/api/logs", dependencies=[Depends(get_api_key)], response_model=List[str])
def list_logs():
    """Get a list of available log files."""
    log_dir = Path("logs")
    if not log_dir.is_dir():
        return []
    return sorted([f.name for f in log_dir.iterdir() if f.is_file() and f.name.endswith(".log")])

@app.get("/api/logs/{actor_id}", dependencies=[Depends(get_api_key)])
def get_log_file(actor_id: str):
    """Download the log file for a specific actor."""
    log_file = Path("logs") / f"{actor_id}.log"
    if not log_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log file not found for this actor.")
    return FileResponse(log_file)

@app.post("/api/start", dependencies=[Depends(get_api_key)])
def start_task(config: Optional[TaskConfig] = None):
    """Start the stress test. Optionally provide a new configuration."""
    if config:
        state["task_config"] = config.dict()
    state["running"] = True
    return {"status": "Stress test started", "config": state["task_config"]}

@app.post("/api/stop", dependencies=[Depends(get_api_key)])
def stop_task():
    """Stop the stress test."""
    state["running"] = False
    return {"status": "Stress test stopped"}

@app.put("/api/config", dependencies=[Depends(get_api_key)])
def update_config(config: TaskConfig):
    """Update the task configuration. This does not start or stop the test."""
    state["task_config"] = config.dict()
    return {"status": "Configuration updated", "new_config": state["task_config"]}

# --- WebSocket Endpoint ---

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive by waiting for a message (which we discard)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected from WebSocket")

# --- Web UI Endpoint ---

@app.get("/", response_class=FileResponse)
async def read_index():
    """Serves the main index.html file for the web UI."""
    index_path = Path(__file__).parent / "static" / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="index.html not found")
    return FileResponse(index_path)
