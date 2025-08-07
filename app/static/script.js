document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const apiKeyInput = document.getElementById('apiKey');
    const statusIndicatorDot = document.getElementById('status-indicator-dot');
    const statusText = document.getElementById('status-text');
    
    // Config display
    const configHost = document.getElementById('config-host');
    const configPort = document.getElementById('config-port');
    const configThreads = document.getElementById('config-threads');
    const configDuration = document.getElementById('config-duration');
    const configMode = document.getElementById('config-mode');
    
    // Actor display
    const actorCount = document.getElementById('actor-count');
    const actorList = document.getElementById('actor-list');
    
    // Logs
    const logBox = document.getElementById('log-box');
    const logContainer = document.getElementById('log-container');
    const pauseScrollCheckbox = document.getElementById('pause-scroll');
    const clearLogBtn = document.getElementById('clear-log-btn');
    
    // Form
    const form = document.getElementById('control-form');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const updateBtn = document.getElementById('update-btn');
    
    // Query
    const queryBtn = document.getElementById('query-btn');
    const queryStatusText = document.getElementById('query-status-text');
    const serverStatusList = document.getElementById('server-status-list');
    const queryOnlineStatus = document.getElementById('query-online-status');
    const queryMotd = document.getElementById('query-motd');
    const queryPlayers = document.getElementById('query-players');
    const queryVersion = document.getElementById('query-version');
    const queryPlugins = document.getElementById('query-plugins');

    const API_BASE = window.location.origin;

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
                logToScreen({ level: 'ERROR', message: `API Error: ${errorData.detail || `HTTP ${response.status}`}` });
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            return response.json();
        } catch (error) {
            logToScreen({ level: 'ERROR', message: `Request failed: ${error.message}` });
            throw error;
        }
    };

    const queryServer = async () => {
        const host = document.getElementById('host').value;
        const port = parseInt(document.getElementById('port').value, 10);
        if (!host || !port) {
            queryStatusText.textContent = 'Enter a host and port to query.';
            serverStatusList.classList.add('hidden');
            return;
        }

        queryStatusText.textContent = 'Pinging server...';
        queryStatusText.classList.remove('hidden');
        serverStatusList.classList.add('hidden');

        try {
            const data = await fetchAPI('/api/query', {
                method: 'POST',
                headers: getHeaders(),
                body: JSON.stringify({ host, port }),
            });
            updateQueryUI(data, true);
        } catch (error) {
            updateQueryUI({ error: error.message }, false);
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
            statusIndicatorDot.className = 'indicator-dot running';
            statusText.textContent = 'Task Running';
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } else {
            statusIndicatorDot.className = 'indicator-dot stopped';
            statusText.textContent = 'Idle';
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
        const config = data.task_config || {};
        configHost.textContent = config.host || 'N/A';
        configPort.textContent = config.port || 'N/A';
        configThreads.textContent = config.threads || 'N/A';
        configDuration.textContent = config.duration || 'N/A';
        configMode.textContent = config.mode || 'N/A';

        // Pre-fill form if empty
        if (!form.host.value && config.host) form.host.value = config.host;
        if (form.port.value === "25565" && config.port) form.port.value = config.port;
        if (form.threads.value === "200" && config.threads) form.threads.value = config.threads;
        if (form.duration.value === "60" && config.duration) form.duration.value = config.duration;
        if (config.mode) form.mode.value = config.mode;
    };

    const updateActorsUI = (actors) => {
        const actorIds = Object.keys(actors);
        actorCount.textContent = actorIds.length;
        actorList.innerHTML = '';
        if (actorIds.length === 0) {
            actorList.innerHTML = '<li>No actors have checked in.</li>';
            return;
        }
        actorIds.sort().forEach(id => {
            const li = document.createElement('li');
            li.textContent = `${id.substring(0, 12)}`; // Shorten ID
            actorList.appendChild(li);
        });
    };

    const updateQueryUI = (data, isOnline) => {
        queryStatusText.classList.add('hidden');
        serverStatusList.classList.remove('hidden');

        if (isOnline) {
            queryOnlineStatus.textContent = 'Online';
            queryOnlineStatus.style.color = 'var(--accent-success)';
            queryMotd.innerHTML = data.motd.replace(/§./g, ''); // Basic color code stripping
            queryPlayers.textContent = `${data.num_players} / ${data.max_players}`;
            queryVersion.textContent = data.version;
            queryPlugins.textContent = data.plugins.length > 50 ? 'Too many to display' : (data.plugins || 'N/A');
        } else {
            queryOnlineStatus.textContent = 'Offline';
            queryOnlineStatus.style.color = 'var(--accent-danger)';
            queryMotd.textContent = data.error || 'Failed to connect.';
            queryPlayers.textContent = 'N/A';
            queryVersion.textContent = 'N/A';
            queryPlugins.textContent = 'N/A';
        }
    };

    const logToScreen = (logData) => {
        const timestamp = new Date(logData.timestamp || Date.now()).toLocaleTimeString();
        const line = document.createElement('span');
        line.classList.add('log-line');

        const timeEl = document.createElement('span');
        timeEl.classList.add('log-timestamp');
        timeEl.textContent = `[${timestamp}]`;
        line.appendChild(timeEl);

        const msgEl = document.createElement('span');
        const level = (logData.level || 'info').toLowerCase();
        const actorId = logData.actor_id;
        
        let message = logData.message || JSON.stringify(logData);
        if (actorId) {
            message = `[${actorId.substring(0, 12)}] ${message}`;
        }

        msgEl.classList.add(`log-${level}`);
        msgEl.textContent = message;
        line.appendChild(msgEl);
        
        logBox.appendChild(line);

        if (!pauseScrollCheckbox.checked) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    };

    // --- WebSocket ---
    const setupWebSocket = () => {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/logs`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => logToScreen({ level: 'SYSTEM', message: 'Framework connection established.' });
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                switch (data.type) {
                    case 'status_update':
                        updateStatusUI(data.payload);
                        updateActorsUI(data.payload.actors || {});
                        break;
                    case 'log':
                        logToScreen(data.payload);
                        break;
                    default:
                        logToScreen({ level: 'WARN', message: `Unknown WS message type: ${data.type}` });
                }
            } catch (e) {
                logToScreen({ level: 'ERROR', message: 'Failed to parse WebSocket message.' });
                console.error("WS Parse Error:", e, event.data);
            }
        };

        ws.onclose = () => {
            logToScreen({ level: 'WARN', message: 'Connection lost. Reconnecting in 5s...' });
            setTimeout(setupWebSocket, 5000);
        };

        ws.onerror = (error) => {
            logToScreen({ level: 'ERROR', message: 'WebSocket error. See console.' });
            console.error('WebSocket Error:', error);
        };
    };

    // --- Event Listeners ---
    startBtn.addEventListener('click', async () => {
        logToScreen({ level: 'SYSTEM', message: 'Initiating task...' });
        const config = getFormData();
        try {
            await fetchAPI('/api/start', {
                method: 'POST',
                headers: getHeaders(),
                body: JSON.stringify(config),
            });
        } catch (error) {}
    });

    stopBtn.addEventListener('click', async () => {
        logToScreen({ level: 'SYSTEM', message: 'Sending termination signal...' });
        try {
            await fetchAPI('/api/stop', {
                method: 'POST',
                headers: getHeaders(),
            });
        } catch (error) {}
    });

    updateBtn.addEventListener('click', async () => {
        logToScreen({ level: 'SYSTEM', message: 'Updating live configuration...' });
        const config = getFormData();
        try {
            await fetchAPI('/api/config', {
                method: 'PUT',
                headers: getHeaders(),
                body: JSON.stringify(config),
            });
            logToScreen({ level: 'SUCCESS', message: 'Live configuration updated.' });
        } catch (error) {}
    });
    
    apiKeyInput.addEventListener('change', () => {
        logToScreen({ level: 'SYSTEM', message: 'API Key updated.' });
    });

    clearLogBtn.addEventListener('click', () => {
        logBox.innerHTML = '';
        logToScreen({ level: 'SYSTEM', message: 'Log view cleared.' });
    });

    queryBtn.addEventListener('click', queryServer);

    // --- Initialization ---
    const init = () => {
        logToScreen({ level: 'SYSTEM', message: 'Mission Control UI initialized.' });
        setupWebSocket();
        // Initial query on load if host is set
        if (document.getElementById('host').value) {
            setTimeout(queryServer, 500);
        }
    };

    init();
});
