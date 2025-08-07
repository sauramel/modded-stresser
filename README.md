# Modular Exploit Framework

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
- **Advanced Target Profiler**: Before engaging a target, the framework can run a detailed profile to fingerprint the server. It identifies the server type (Vanilla, Forge, etc.), version, and can enumerate the complete mod list on Forge servers.
- **Distributed Architecture**: Scale your operations by deploying multiple `actor` nodes. The system is designed for horizontal scaling via Docker Compose.
- **Web UI Mission Control**: A modern, responsive web interface to profile targets, select and configure exploit modules, and monitor operations in real-time.
- **Live Log Streaming**: A WebSocket endpoint provides a live, color-coded feed of logs from the controller and all connected actors.
- **Dynamic UI**: The UI is not static. It dynamically fetches the list of available exploits from the controller's API, ensuring the frontend always reflects the backend's capabilities.

---

## Exploit Engine

The power of this framework lies in its modularity. To create a new exploit, simply add a new Python file to the `app/exploits/` directory containing a class that inherits from `exploits.base.Exploit`.

### Included Modules

| ID              | Name                 | Category          | Description                                                              |
| --------------- | -------------------- | ----------------- | ------------------------------------------------------------------------ |
| `login_flood`   | Login Flood          | Denial of Service | Floods the server with fake player login attempts to exhaust resources.  |
| `modded_flood`  | Modded Flood (FML)   | Modded            | A login flood optimized for Forge servers, using the FML handshake.      |

The framework will automatically discover, register, and display the new module in the UI.

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

For more granular control or integration with custom scripts, you can run the controller and actor containers manually.

### Prerequisites
- Docker

### 1. Build the Docker Image

First, build the universal Docker image from the project's root directory. We'll tag it as `exploit-framework` for easy reference.

```bash
docker build -t exploit-framework -f app/Dockerfile .
```

### 2. Create a Docker Network

For the containers to communicate, they must share a network. Let's create one called `exploit-net`.

```bash
docker network create exploit-net
```

### 3. Run the Controller Container

Launch the controller container on the `exploit-net` network. We give it the name `controller` so actors can find it easily.

```bash
docker run -d \
  --name controller \
  --network exploit-net \
  -p 8000:8000 \
  -e MODE=controller \
  -e API_KEY="your-secret-api-key-here" \
  exploit-framework
```
- `-d`: Run in detached mode.
- `--name controller`: Critical for service discovery by actors.
- `--network exploit-net`: Attaches the container to our shared network.
- `-p 8000:8000`: Exposes the web UI and API on your host machine.
- `-e MODE=controller`: Tells the container to start in controller mode.
- `-e API_KEY`: Sets your secret API key.

### 4. Run Actor Containers

Now, launch as many actor containers as you need. They will connect to the controller using its container name (`controller`) as the hostname.

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
- The `ACTOR_ID` is automatically generated from the container's unique hostname, so you don't need to set it manually.
- You can run the command multiple times to scale up the number of actors.

### 5. Stopping and Cleanup

```bash
# Stop and remove the containers
docker stop controller && docker rm controller
# You will need to find and stop each actor container individually or by a script
docker ps -a | grep exploit-framework | awk '{print $1}' | xargs docker stop | xargs docker rm

# Remove the network
docker network rm exploit-net
```

---

## Manual Execution (Without Docker)

For development or if you prefer not to use Docker, you can run the controller and actors directly on your machine.

### Prerequisites
- Python 3.7+
- `pip` and `venv`

### 1. Setup

First, set up a Python virtual environment and install the required dependencies.

```bash
# Create a virtual environment
python3 -m venv venv

# Activate it
# On macOS and Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies from the app directory
pip install -r app/requirements.txt
```

### 2. Run the Controller

Open a terminal, activate the virtual environment, and run the following command to start the controller:

```bash
# Set the mode and run the main script
MODE=controller python app/main.py
```
The controller will start on `http://localhost:8000` by default. You can customize the host, port, and API key with environment variables:
`API_KEY=my-secret-key LISTEN_PORT=8080 MODE=controller python app/main.py`

### 3. Run Actors

Open one or more new terminals to run the actor processes. **It is critical that each actor has a unique `ACTOR_ID`**.

**Terminal 1 - Actor 1:**
```bash
# Activate the virtual environment first
source venv/bin/activate

# Run the first actor
MODE=actor ACTOR_ID=manual-actor-01 python app/main.py
```

**Terminal 2 - Actor 2:**
```bash
# Activate the virtual environment first
source venv/bin/activate

# Run the second actor with a different ID
MODE=actor ACTOR_ID=manual-actor-02 python app/main.py
```

The actors will automatically connect to the controller at `http://localhost:8000`. You can point them to a different controller using the `CONTROLLER_HOST` environment variable.

---

## API Documentation

The controller listens on port `8000`. All administrative endpoints under `/api/` require an API key to be sent in the `X-API-Key` header.

#### `GET /api/exploits`
Lists all available, registered exploit modules.

#### `POST /api/profile`
Profiles a target server. Requires `host` and `port` in the JSON body. Returns detailed server information, including mod lists for Forge servers.

#### `GET /api/status`
(Implicitly used by WebSocket) Get the current status, configuration, and active actors.

#### `POST /api/start`
Starts an operation. Requires a configuration object in the body specifying the `host`, `port`, `threads`, `duration`, and `exploit` ID.

#### `POST /api/stop`
Stops the current operation.

#### `PUT /api/config`
Updates the task configuration for a running operation on-the-fly.

### WebSocket Endpoint

#### `WS /ws/logs`
Connect to this endpoint to receive a real-time JSON stream of system status updates and log messages from all components.
