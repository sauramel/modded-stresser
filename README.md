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

## Deployment with Docker

The easiest way to run the system is with Docker Compose.

### Prerequisites
- Docker
- Docker Compose

### Instructions

1.  **Clone the repository and navigate into it.**

2.  **Set your API Key**: It is strongly recommended to change the default API key in the `docker-compose.yml` file.
    ```yaml
    services:
      controller:
        ...
        environment:
          - API_KEY=you-should-really-change-this
    ```

3.  **Build and Run**:
    ```bash
    # Build the images and start the controller and 3 actor containers in the background
    docker-compose up --build --scale actor=3 -d
    ```

4.  **Open Mission Control**: Navigate to `http://localhost:8000` in your web browser.

5.  **Configure and Run an Operation**:
    -   Enter your API key if you changed it.
    -   Enter the **Target Host** and **Port**. If testing a server on your local machine, use `host.docker.internal` as the host.
    -   Click the **Profile** button to fingerprint the target. This will show its status, version, and enumerate mods if it's a Forge server.
    -   The **Exploit Module** dropdown will be populated with all available exploits. Select one.
    -   Configure **Threads** and **Duration**.
    -   Click **Start Task**.

6.  **View Live Logs**: Logs from the controller and all actors will stream into the "Live Operations Log" panel.

7.  **Scale Actors**: You can change the number of running actors at any time.
    ```bash
    # Scale up to 10 actors
    docker-compose up --scale actor=10 -d
    ```

8.  **Stop the System**:
    ```bash
    docker-compose down
    ```

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
