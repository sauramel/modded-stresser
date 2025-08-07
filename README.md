# Minecraft Server Stresser

A distributed, containerized stress testing tool for Minecraft server networks. This tool is designed to simulate various types of client connection loads to test server performance, plugin stability, and proxy configurations under pressure.

It operates on a controller/actor model. The `controller` provides a REST API, a WebSocket endpoint, and a web UI to manage and monitor the test. Multiple `actor` nodes carry out the actual stress tests by polling the controller for tasks.

---

## Legal Disclaimer

**THIS SOFTWARE IS INTENDED FOR EDUCATIONAL AND AUTHORIZED TESTING PURPOSES ONLY.**

The use of this software to attack, disrupt, or gain unauthorized access to any computer system or network is **strictly prohibited** and **illegal**. The authors and contributors of this software are not responsible for any damage or legal consequences resulting from its misuse.

**You shall not use this software on any server, network, or service that you do not have explicit, written permission to test.** Unauthorized testing is a criminal offense. By using this software, you agree to take full responsibility for your actions.

---

## Features

- **Distributed Architecture**: Scale your tests by deploying multiple actor nodes.
- **Web UI Control Panel**: Modern, responsive web interface to start, stop, configure, and monitor tests.
- **Live Server Query**: Fetches and displays live server status (MOTD, players, version) using the `mcquery` protocol.
- **Real-time Log Streaming**: A WebSocket endpoint provides a live, color-coded feed of logs from all actors.
- **Unique Actor IDs**: Actors automatically get unique IDs from their container hostnames for easy identification.
- **Multiple Attack Modes**: Simulate different types of load on your server.
- **Containerized**: Easily deploy the entire system using Docker and Docker Compose.

---

## Attack Modes

This tool is most effective against servers in **offline mode** (where player accounts are not authenticated with Mojang).

| Mode              | Description                                                                                             | Intensity | Use Case                                                              |
| ----------------- | ------------------------------------------------------------------------------------------------------- | --------- | --------------------------------------------------------------------- |
| `login_flood`     | The standard attack. A large number of bots attempt to join the server and then disconnect.             | Medium    | Testing raw connection handling and player login processing.          |
| `join_spam`       | Bots connect, stay for a few seconds, and disconnect repeatedly. Creates high player churn.             | High      | Stressing player data loading/unloading and join/leave event handlers.|
| `chat_flood`      | Bots join and continuously send random chat messages.                                                   | High      | Testing chat plugins, anti-spam systems, and server thread performance. |
| `motd_spam`       | Rapidly sends server list pings (MOTD requests). A network-level flood.                                 | Low       | Testing proxy performance (BungeeCord, Velocity) and network stack.     |
| `modded_probe`    | A utility mode. A single actor connects to the server to get its mod list.                              | N/A       | Gathers information required for the `modded_replay` attack.          |
| `modded_replay`   | Simulates modded clients joining by replaying the mod list gathered by the probe.                       | Medium    | Testing modded servers that require clients to have a matching mod set. |

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

4.  **Open the Control Panel**: Navigate to `http://localhost:8000` in your web browser.

5.  **Configure and Run a Test**:
    -   Enter your API key if you changed it.
    -   If testing a server on your **local machine**, set the **Target Host** to `host.docker.internal`. This special DNS name allows the Docker containers to reach services running on your computer.
    -   For a remote server, use its IP address or domain name.
    -   The Server Status card will show live information if the server has `enable-query=true` in its `server.properties`.
    -   Choose your desired attack mode, threads, and duration.
    -   Click "Start".

6.  **View Live Logs**: Logs from all actors will stream into the "Live Logs" panel in real-time. Actor IDs will appear as `project_actor_1`, `project_actor_2`, etc.

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

#### `POST /api/query`
Queries a server for its status using the UDP query protocol. Requires `host` and `port` in the JSON body.

#### `GET /api/status`
Get the current status, configuration, and active actors.

#### `POST /api/start`
Starts the stress test. You can optionally provide a new configuration in the request body.

#### `POST /api/stop`
Stops the stress test.

#### `PUT /api/config`
Updates the task configuration without starting or stopping the test.

### WebSocket Endpoint

#### `WS /ws/logs`
Connect to this endpoint with any WebSocket client to receive a real-time stream of logs from all actors.
