# Minecraft Server Stresser

A distributed, containerized stress testing tool for Minecraft server networks. This tool is designed to simulate various types of client connection loads to test server performance, plugin stability, and proxy configurations under pressure.

It operates on a controller/actor model. The `controller` provides a REST API and WebSocket endpoint to manage and monitor the test, while multiple `actor` nodes carry out the actual stress tests by polling the controller for tasks.

---

##  юридическое уведомление (Legal Disclaimer)

**THIS SOFTWARE IS INTENDED FOR EDUCATIONAL AND AUTHORIZED TESTING PURPOSES ONLY.**

The use of this software to attack, disrupt, or gain unauthorized access to any computer system or network is **strictly prohibited** and **illegal**. The authors and contributors of this software are not responsible for any damage or legal consequences resulting from its misuse.

**You shall not use this software on any server, network, or service that you do not have explicit, written permission to test.** Unauthorized testing is a criminal offense. By using this software, you agree to take full responsibility for your actions.

---

## Features

- **Distributed Architecture**: Scale your tests by deploying multiple actor nodes.
- **RESTful API Control**: A central controller with a secure, key-protected API to start, stop, configure, and monitor tests.
- **Real-time Log Streaming**: A WebSocket endpoint provides a live feed of logs from all actors.
- **Multiple Test Modes**:
    - `login_flood`: Simulates a large number of clients joining the server.
    - `modded_probe`: Probes the server to get its mod list for use in more realistic attacks.
    - `modded_replay`: Simulates modded clients joining, which can be more resource-intensive for the server to handle.
- **Containerized**: Easily deploy the entire system using Docker and Docker Compose.

---

## API Documentation

The controller listens on port `8000` by default. All administrative endpoints under `/api/` require an API key to be sent in the `X-API-Key` header.

### Authentication

-   **Header**: `X-API-Key: <your_secret_key>`

### Admin Endpoints

#### `GET /api/status`
Get the current status of the stress test, including whether it's running and the current task configuration.

-   **Success Response (200)**:
    ```json
    {
      "running": true,
      "task_config": {
        "host": "127.0.0.1",
        "port": 25565,
        "threads": 200,
        "duration": 60,
        "mode": "login_flood"
      },
      "actors": {
        "actor-abc123": { "last_seen": "2023-10-27T10:00:00.123Z" }
      }
    }
    ```

#### `POST /api/start`
Starts the stress test. Actors will begin executing the configured task. You can optionally provide a new configuration in the request body.

-   **Request Body (Optional)**:
    ```json
    {
      "host": "play.example.com",
      "port": 25565,
      "threads": 500,
      "duration": 120,
      "mode": "login_flood"
    }
    ```
-   **Success Response (200)**:
    ```json
    {
      "status": "Stress test started",
      "config": { ... }
    }
    ```

#### `POST /api/stop`
Stops the stress test. Actors will be instructed to go idle.

-   **Success Response (200)**:
    ```json
    { "status": "Stress test stopped" }
    ```

#### `PUT /api/config`
Updates the task configuration without starting or stopping the test. The new configuration will be used the next time the test is started.

-   **Request Body (Required)**:
    ```json
    {
      "host": "play.example.com",
      "port": 25565,
      "threads": 500,
      "duration": 120,
      "mode": "login_flood"
    }
    ```
-   **Success Response (200)**:
    ```json
    {
      "status": "Configuration updated",
      "new_config": { ... }
    }
    ```

#### `GET /api/actors`
Get a list of all actors that have checked in with the controller and their last-seen timestamp.

-   **Success Response (200)**:
    ```json
    {
      "actor-fde5a4": { "last_seen": "2023-10-27T10:05:10.456Z" },
      "actor-9b3c1a": { "last_seen": "2023-10-27T10:05:12.789Z" }
    }
    ```

#### `GET /api/logs`
Get a list of available log files by actor ID.

-   **Success Response (200)**:
    ```json
    [ "actor-fde5a4.log", "actor-9b3c1a.log" ]
    ```

#### `GET /api/logs/{actor_id}`
Download the raw log file for a specific actor.

-   **Success Response (200)**: Returns the contents of the log file.

### WebSocket Endpoint

#### `WS /ws/logs`
Connect to this endpoint with any WebSocket client to receive a real-time stream of logs from all actors as they are submitted to the controller.

---

## Deployment with Docker

The easiest way to run the system is with Docker Compose.

### Prerequisites
- Docker
- Docker Compose

### Instructions

1.  **Create a `docker-compose.yml` file** (or use the one provided in this repository).

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
    # Build the images and start the controller and 3 actor containers
    docker-compose up --build --scale actor=3 -d
    ```

4.  **Interact with the API**: The controller is now running on `http://localhost:8000`.
    ```bash
    # Check status (replace with your API key)
    curl -X GET http://localhost:8000/api/status \
      -H "X-API-Key: you-should-really-change-this"

    # Start a test
    curl -X POST http://localhost:8000/api/start \
      -H "X-API-Key: you-should-really-change-this" \
      -H "Content-Type: application/json" \
      -d '{
            "host": "your.target.server",
            "port": 25565,
            "threads": 100,
            "duration": 30,
            "mode": "login_flood"
          }'
    ```

5.  **View Live Logs**: Connect a WebSocket client to `ws://localhost:8000/ws/logs`.

6.  **Scale Actors**: You can change the number of running actors at any time.
    ```bash
    # Scale up to 10 actors
    docker-compose up --scale actor=10 -d
    ```

7.  **Stop the System**:
    ```bash
    docker-compose down
    ```
