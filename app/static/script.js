document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const apiKeyInput = document.getElementById('apiKey');
    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const configHost = document.getElementById('config-host');
    const configPort = document.getElementById('config-port');
    const configThreads = document.getElementById('config-threads');
    const configDuration = document.getElementById('config-duration');
    const configMode = document.getElementById('config-mode');
    const actorList = document.getElementById('actor-list');
    const logBox = document.getElementById('log-box');
    const form = document.getElementById('control-form');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const updateBtn = document.getElementById('update-btn');

    const API_BASE = window.location.origin;
    let statusInterval;

    // --- API Functions ---
    const getHeaders = () => ({
        'Content-Type': 'application/json',
        'X-API-Key': apiKeyInput.value,
    });

    const fetchAPI = async (endpoint, options = {}) => {
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, options);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(`HTTP ${response.status}: ${errorData.detail}`);
            }
            return response.json();
        } catch (error) {
            logToScreen(`API Error: ${error.message}`, 'error');
            throw error;
        }
    };

    const getStatus = async () => {
        try {
            const data = await fetchAPI('/api/status', { headers: getHeaders() });
            updateStatusUI(data);
            updateActorsUI(data.actors || {});
        } catch (error) {
            // Error is already logged by fetchAPI
            updateStatusUI({ running: false, task_config: {} });
            updateActorsUI({});
        }
    };

    const getFormData = () => ({
        host: document.getElementById('host').value,
        port: parseInt(document.getElementById('port').value, 10),
        threads: parseInt(document.getElementById('threads').value, 10),
        duration: parseInt(document.getElementById('duration').value, 10),
        mode: document.getElementById('mode').value,
    });

    // --- UI Update Functions ---
    const updateStatusUI = (data) => {
        if (data.running) {
            statusIndicator.className = 'indicator-running';
            statusText.textContent = 'Running';
        } else {
            statusIndicator.className = 'indicator-stopped';
            statusText.textContent = 'Idle';
        }
        const config = data.task_config || {};
        configHost.textContent = config.host || 'N/A';
        configPort.textContent = config.port || 'N/A';
        configThreads.textContent = config.threads || 'N/A';
        configDuration.textContent = config.duration || 'N/A';
        configMode.textContent = config.mode || 'N/A';

        // Populate form with current config if not already filled
        if (!form.host.value && config.host) form.host.value = config.host;
        if (!form.port.value && config.port) form.port.value = config.port;
        if (!form.threads.value && config.threads) form.threads.value = config.threads;
        if (!form.duration.value && config.duration) form.duration.value = config.duration;
        if (!form.mode.value && config.mode) form.mode.value = config.mode;
    };

    const updateActorsUI = (actors) => {
        actorList.innerHTML = '';
        const actorIds = Object.keys(actors);
        if (actorIds.length === 0) {
            actorList.innerHTML = '<li>No actors have checked in.</li>';
            return;
        }
        actorIds.forEach(id => {
            const li = document.createElement('li');
            li.textContent = `ID: ${id}`;
            actorList.appendChild(li);
        });
    };

    const logToScreen = (message, type = 'info') => {
        const timestamp = new Date().toLocaleTimeString();
        let formattedMessage = `[${timestamp}] `;
        if (typeof message === 'object') {
            formattedMessage += JSON.stringify(message, null, 2);
        } else {
            formattedMessage += message;
        }
        logBox.textContent += formattedMessage + '\n';
        logBox.scrollTop = logBox.scrollHeight;
    };

    // --- WebSocket ---
    const setupWebSocket = () => {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/logs`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            logToScreen('WebSocket connection established.', 'system');
        };

        ws.onmessage = (event) => {
            try {
                const logData = JSON.parse(event.data);
                logToScreen(logData, 'log');
            } catch (e) {
                logToScreen(event.data, 'raw');
            }
        };

        ws.onclose = () => {
            logToScreen('WebSocket connection closed. Reconnecting in 5 seconds...', 'system');
            setTimeout(setupWebSocket, 5000);
        };

        ws.onerror = (error) => {
            logToScreen('WebSocket error. See console for details.', 'error');
            console.error('WebSocket Error:', error);
        };
    };

    // --- Event Listeners ---
    startBtn.addEventListener('click', async () => {
        logToScreen('Starting stress test...', 'system');
        const config = getFormData();
        try {
            const data = await fetchAPI('/api/start', {
                method: 'POST',
                headers: getHeaders(),
                body: JSON.stringify(config),
            });
            logToScreen(data.status, 'success');
            getStatus();
        } catch (error) {}
    });

    stopBtn.addEventListener('click', async () => {
        logToScreen('Stopping stress test...', 'system');
        try {
            const data = await fetchAPI('/api/stop', {
                method: 'POST',
                headers: getHeaders(),
            });
            logToScreen(data.status, 'success');
            getStatus();
        } catch (error) {}
    });

    updateBtn.addEventListener('click', async () => {
        logToScreen('Updating configuration...', 'system');
        const config = getFormData();
        try {
            const data = await fetchAPI('/api/config', {
                method: 'PUT',
                headers: getHeaders(),
                body: JSON.stringify(config),
            });
            logToScreen(data.status, 'success');
            getStatus();
        } catch (error) {}
    });
    
    apiKeyInput.addEventListener('change', () => {
        logToScreen('API Key updated. Fetching new status.', 'system');
        getStatus();
    });

    // --- Initialization ---
    const init = () => {
        logToScreen('Control panel initialized.', 'system');
        getStatus();
        statusInterval = setInterval(getStatus, 10000); // Refresh status every 10 seconds
        setupWebSocket();
    };

    init();
});
