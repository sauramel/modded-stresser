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

- **Modular Exploit Engine**: Each exploit is a self-contained Python class in the `app/exploits/` directory, allowing for easy creation of new modules.
- **Advanced Target Profiler**: Uses the UDP query protocol to fingerprint servers (requires `enable-query=true` in `server.properties`).
- **Distributed Architecture**: Scale your operations by deploying multiple `actor` nodes. The system is designed for horizontal scaling via Docker Compose.
- **Web UI Mission Control**: A modern, responsive web interface to profile targets, select and configure exploit modules, and monitor operations in real-time.
- **Live Log Streaming & Culling**: A WebSocket endpoint provides a live, color-coded feed of logs from all actors. The UI automatically culls logs after 500 entries to prevent browser slowdown.
- **Scalability-Aware Actors**: Actors use batched logging and randomized check-in intervals (jitter) to reduce controller load and support larger-scale operations.

---

## Included Modules

| Category                     | Name                 | Description                                                                                                                            |
| ---------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Vanilla (Offline-Mode)**   | Login Flood          | Floods the server with login attempts using random usernames. Effective against offline-mode servers.                                  |
| **Vanilla (Any Mode)**       | Chat Spam            | Joins the server and floods the chat with configurable messages.                                                                       |
| **Vanilla (Any Mode)**       | Book Ban (Kick)      | Crafts a book with excessive NBT data that can kick players who open it.                                                               |
| **Vanilla (Any Mode)**       | Join/Leave Spam      | Repeatedly joins and leaves the server to stress player handling plugins and logs.                                                     |
| **Denial of Service**        | Handshake Crash      | Sends a malformed handshake packet that can crash older or unpatched servers (e.g., 1.7.x).                                            |
| **Remote Code Execution**    | Log4Shell RCE        | Sends a functional Log4Shell payload via chat. **Requires user-hosted malicious LDAP server.** Misuse is illegal and strictly prohibited. |
| **Proxy Exploits**           | BungeeGuard Exploit  | Attempts to join a backend server directly, bypassing the proxy. Only works if the backend is exposed and misconfigured. (Disabled by default) |

---

## Scalability

The framework has been designed with scaling in mind. However, the default controller/actor model via HTTP polling has natural limits.

### Built-in Enhancements
- **Actor Jitter**: Actors add a small, random delay to their check-in interval. This prevents thousands of actors from polling the controller at the exact same microsecond (the "thundering herd" problem).
- **Batched Logging**: Actors collect logs locally and send them to the controller in batches, significantly reducing the number of `POST /log` requests.
- **Asynchronous Processing**: The controller processes incoming data asynchronously to remain responsive under load.

### Scaling to Thousands of Actors
For deployments exceeding a few hundred actors, the HTTP polling model will become a bottleneck. The recommended architecture for hyper-scale operations is to replace the direct HTTP communication with a message broker like **Redis (Pub/Sub)** or **RabbitMQ**.

- **Controller**: Publishes tasks to a message queue topic (e.g., `voidout:tasks`).
- **Actors**: Subscribe to the `voidout:tasks` topic to receive work.
- **Logging**: Actors publish logs to a `voidout:logs` topic, which can be consumed by a dedicated logging service or the controller.

This decoupled architecture is significantly more resilient and scalable.

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
