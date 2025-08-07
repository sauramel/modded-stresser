# Voidout - Modular Exploit Framework

A professional-grade, distributed, and containerized framework for testing Minecraft server network resilience. This tool has been architected for extensibility, allowing for the rapid development and deployment of new exploit modules.

It operates on a controller/actor model. The `controller` provides a REST API, a WebSocket endpoint, and a web UI to manage and monitor operations. Multiple `actor` nodes carry out the actual tasks by polling the controller.

---

## Legal Disclaimer

**THIS SOFTWARE IS INTENDED FOR EDUCATIONAL AND AUTHORIZED TESTING PURPOSES ONLY.**

The use of this software to attack, disrupt, or gain unauthorized access to any computer system or network is **strictly prohibited** and **illegal**. The authors and contributors of this software are not responsible for any damage or legal consequences resulting from its misuse.

**You shall not use this software on any server, network, or service that you do not have explicit, written permission to test.** Unauthorized testing is a criminal offense. By using this software, you agree to take full responsibility for your actions.

---

## Core Features

- **Modular Exploit Engine**: Gone are the days of hardcoded attacks. The framework now features a dynamic exploit loader. Each exploit is a self-contained Python class in the `app/exploits/` directory, allowing for easy creation of new, complex modules.
- **Advanced Target Profiler**: Before engaging a target, the framework can run a detailed profile to fingerprint the server. It identifies the server type (Vanilla, Forge, etc.), and can enumerate the complete mod list on Forge servers.
- **Distributed Architecture**: Scale your operations by deploying multiple `actor` nodes. The system is designed for horizontal scaling via Docker Compose.
- **Web UI Mission Control**: A modern, responsive web interface to profile targets, select and configure exploit modules, and monitor operations in real-time.
- **Live Log Streaming**: A WebSocket endpoint provides a live, color-coded feed of logs from the controller and all connected actors.
- **Dynamic UI**: The UI is not static. It dynamically fetches the list of available exploits and their required arguments from the controller's API, ensuring the frontend always reflects the backend's capabilities.

---

## Exploit Engine

The power of this framework lies in its modularity. To create a new exploit, simply add a new Python file to the `app/exploits/` directory containing a class that inherits from `exploits.base.Exploit`.

### How it Works
1.  **Create a File**: Add a new `.py` file in `app/exploits/` (e.g., `app/exploits/my_new_exploit.py`).
2.  **Inherit from Base**: Your class must inherit from `exploits.base.Exploit`.
3.  **Define Metadata**: Set the class attributes `id`, `name`, `description`, and `category`.
4.  **Define Arguments**: If your exploit needs custom parameters from the UI, define them in the `args` list. These will be rendered automatically on the frontend.
5.  **Implement `run`**: The core logic of your exploit goes into the `run` method. This method is what each thread will execute in a loop.

### Example: Creating a Chat Spammer

```python
# in app/exploits/chat_spam.py
import time
from .base import Exploit

class ChatSpamExploit(Exploit):
    # --- Metadata ---
    id = "chat_spam"
    name = "Chat Spam"
    description = "Floods the server chat with a configurable message."
    category = "Legitimate Stress Test"
    
    # --- Arguments for the UI ---
    args = [
        {
            "name": "username",
            "type": "string",
            "label": "Bot Username",
            "default": "SpamBot"
        },
        {
            "name": "message",
            "type": "string",
            "label": "Spam Message",
            "default": "This is a test message!"
        }
    ]

    def run(self, log_callback):
        # Access arguments passed from the UI
        username = self.exploit_args.get("username")
        message = self.exploit_args.get("message")

        # In a real implementation, you would connect and send the chat packet.
        # Here, we just log it.
        log_callback({
            "level": "INFO",
            "message": f"Simulating '{username}' sending chat message: '{message}'"
        })
        time.sleep(1) # Simulate action
```
The framework will automatically discover, register, and display the new module in the UI.

---

## Included Modules

| ID                  | Name                 | Category                   | Description                                                                                             |
| ------------------- | -------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------- |
| `login_flood`       | Login Flood          | Legitimate Stress Test     | Floods the server with login attempts using random usernames.                                           |
| `join_spam`         | Join/Leave Spam      | Legitimate Stress Test     | Repeatedly joins and leaves the server to stress player handling plugins.                               |
| `handshake_crash`   | Handshake Crash      | Denial of Service          | Sends a malformed handshake packet that can crash older or unpatched servers.                           |
| `forge_mod_exploit` | Forge Mod Exploit    | Denial of Service          | Example exploit that requires the server to be running Forge. Checks for a specific mod before running. |

---

## Deployment with Docker Compose

The easiest way to run the system is with Docker Compose.

### Prerequisites
- Docker
- Docker Compose

### Instructions

1.  **Set your API Key**: It is strongly recommended to change the default API key in the `docker-compose.yml` file.
    ```yaml
    services:
      controller:
        ...
        environment:
          - API_KEY=you-should-really-change-this
    ```

2.  **Build and Run**:
    ```bash
    # Build the images and start the controller and 3 actor containers in the background
    docker-compose up --build --scale actor=3 -d
    ```

3.  **Open Mission Control**: Navigate to `http://localhost:8000` in your web browser.

4.  **Stop the System**:
    ```bash
    docker-compose down
    ```

---

## Manual Container Execution (with `docker run`)

For more granular control, you can run the controller and actor containers manually.

### 1. Build the Docker Image
```bash
docker build -t exploit-framework -f app/Dockerfile .
```

### 2. Create a Docker Network
```bash
docker network create exploit-net
```

### 3. Run the Controller Container
```bash
docker run -d \
  --name controller \
  --network exploit-net \
  -p 8000:8000 \
  -v ./logs:/app/logs \
  -e MODE=controller \
  -e API_KEY="your-secret-api-key-here" \
  exploit-framework
```

### 4. Run Actor Containers
Launch as many actor containers as you need. The `ACTOR_ID` is automatically generated from the container's unique hostname.
```bash
# Launch the first actor
docker run -d \
  --network exploit-net \
  -e MODE=actor \
  -e CONTROLLER_HOST="http://controller:8000" \
  exploit-framework

# Launch a second actor
docker run -d \
  --network exploit-net \
  -e MODE=actor \
  -e CONTROLLER_HOST="http://controller:8000" \
  exploit-framework
```

---

## Manual Execution (Without Docker)

### 1. Setup
```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r app/requirements.txt
```

### 2. Run the Controller
```bash
MODE=controller python app/main.py
```

### 3. Run Actors
Open one or more new terminals. **It is critical that each actor has a unique `ACTOR_ID` when running manually on the same machine.**

**Terminal 1 - Actor 1:**
```bash
source venv/bin/activate
MODE=actor ACTOR_ID=manual-actor-01 python app/main.py
```

**Terminal 2 - Actor 2:**
```bash
source venv/bin/activate
MODE=actor ACTOR_ID=manual-actor-02 python app/main.py
```

---

## API Documentation

The controller listens on port `8000`. All administrative endpoints under `/api/` require an API key to be sent in the `X-API-Key` header.

#### `GET /api/exploits`
Lists all available, registered exploit modules and their configurable arguments.

#### `POST /api/profile`
Profiles a target server. Returns detailed server information, including mod lists for Forge servers.
- **Body**: `{ "host": "...", "port": ... }`

#### `POST /api/start`
Starts an operation.
- **Body**: `{ "host": "...", "port": ..., "threads": ..., "duration": ..., "exploit": "exploit_id", "exploit_args": { "arg1": "value1", ... } }`
- **Note**: If the chosen exploit `requires_forge`, you must profile the target first. The controller will use the cached profile data.

#### `POST /api/stop`
Stops the current operation.

#### `PUT /api/config`
Updates the task configuration that will be used when the *next* task is started. Cannot be used while a task is running.
- **Body**: Same as `/api/start`.

### WebSocket Endpoint

#### `WS /ws/logs`
Connect to this endpoint to receive a real-time JSON stream of system status updates and log messages.
- **Message Format**: `{ "type": "log" | "status_update", "payload": { ... } }`
