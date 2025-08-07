document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const apiKeyInput = document.getElementById('apiKey');
    const statusIndicatorDot = document.getElementById('status-indicator-dot');
    const statusText = document.getElementById('status-text');
    
    // Actor display
    const actorCount = document.getElementById('actor-count');
    const actorList = document.getElementById('actor-list');
    
    // Logs
    const logBox = document.getElementById('log-box');
    const logContainer = document.getElementById('log-container');
    const pauseScrollCheckbox = document.getElementById('pause-scroll');
    const clearLogBtn = document.getElementById('clear-log-btn');
    
    // Main Attack Form
    const form = document.getElementById('control-form');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const updateBtn = document.getElementById('update-btn');
    const exploitSelect = document.getElementById('exploit');
    
    // Profiler View
    const profileBtn = document.getElementById('profile-btn');
    const profileHostInput = document.getElementById('profile-host');
    const profilePortInput = document.getElementById('profile-port');
    const profileStatusText = document.getElementById('profile-status-text');
    const serverStatusList = document.getElementById('server-status-list');
    const profileOnlineStatus = document.getElementById('profile-online-status');
    const profileMotd = document.getElementById('profile-motd');
    const profilePlayers = document.getElementById('profile-players');
    const profileVersion = document.getElementById('profile-version');
    const profileType = document.getElementById('profile-type');
    const modListContainer = document.getElementById('mod-list-container');
    const modCount = document.getElementById('mod-count');
    const modList = document.getElementById('mod-list');

    // Dashboard summary
    const profileOnlineStatusSummary = document.getElementById('profile-online-status-summary');
    const profileVersionSummary = document.getElementById('profile-version-summary');
    const profilePlayersSummary = document.getElementById('profile-players-summary');

    // Exploit Library
    const exploitLibraryList = document.getElementById('exploit-library-list');

    // Navigation
    const navItems = document.querySelectorAll('.nav-item');
    const views = document.querySelectorAll('.view');
    const viewTitle = document.getElementById('view-title');

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

    const profileServer = async () => {
        const host = profileHostInput.value;
        const port = parseInt(profilePortInput.value, 10);
        if (!host || !port) {
            profileStatusText.textContent = 'Enter a host and port to profile.';
            serverStatusList.classList.add('hidden');
            return;
        }

        profileStatusText.textContent = 'Profiling server...';
        profileStatusText.classList.remove('hidden');
        serverStatusList.classList.add('hidden');
        profileBtn.disabled = true;

        try {
            const data = await fetchAPI('/api/profile', {
                method: 'POST',
                headers: getHeaders(),
                body: JSON.stringify({ host, port }),
            });
            updateProfileUI(data, true);
        } catch (error) {
            updateProfileUI({ error: error.message }, false);
        } finally {
            profileBtn.disabled = false;
        }
    };

    const getFormData = () => ({
        host: document.getElementById('host').value,
        port: parseInt(document.getElementById('port').value, 10),
        threads: parseInt(document.getElementById('threads').value, 10),
        duration: parseInt(document.getElementById('duration').value, 10),
        exploit: exploitSelect.value,
    });

    // --- UI Update Functions ---
    const updateStatusUI = (data) => {
        // Main status
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
        
        // Task config form and details
        const config = data.task_config || {};
        document.getElementById('config-host').textContent = config.host || 'N/A';
        document.getElementById('config-port').textContent = config.port || 'N/A';
        document.getElementById('config-mode').textContent = config.exploit || 'N/A';
        document.getElementById('config-threads').textContent = config.threads || 'N/A';
        document.getElementById('config-duration').textContent = config.duration || 'N/A';
        
        // Pre-fill form if empty
        if (!form.host.value && config.host) form.host.value = config.host;
        if (form.port.value === "25565" && config.port) form.port.value = config.port;
        if (form.threads.value === "200" && config.threads) form.threads.value = config.threads;
        if (form.duration.value === "60" && config.duration) form.duration.value = config.duration;
        if (config.exploit && exploitSelect.querySelector(`option[value="${config.exploit}"]`)) {
            exploitSelect.value = config.exploit;
        }
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
            const actor = actors[id];
            const li = document.createElement('li');
            const lastSeen = new Date(actor.last_seen).toLocaleString();
            li.innerHTML = `<strong>${id.substring(0, 12)}...</strong><span>Last seen: ${lastSeen}</span>`;
            actorList.appendChild(li);
        });
    };

    const updateProfileUI = (data, isOnline) => {
        profileStatusText.classList.add('hidden');
        serverStatusList.classList.remove('hidden');

        if (isOnline) {
            // Main profiler view
            profileOnlineStatus.textContent = 'Online';
            profileOnlineStatus.style.color = 'var(--accent-success)';
            profileMotd.innerHTML = data.motd.replace(/§./g, ''); // Basic color code stripping
            profilePlayers.textContent = `${data.players.online} / ${data.players.max}`;
            profileVersion.textContent = data.version.name;
            profileType.textContent = data.type;

            // Dashboard summary
            profileOnlineStatusSummary.textContent = 'Online';
            profileOnlineStatusSummary.style.color = 'var(--accent-success)';
            profileVersionSummary.textContent = data.version.name;
            profilePlayersSummary.textContent = `${data.players.online} / ${data.players.max}`;

            if (data.mods && data.mods.length > 0) {
                modListContainer.classList.remove('hidden');
                modCount.textContent = data.mods.length;
                modList.innerHTML = data.mods.map(mod => `<li>${mod.modid} (${mod.version})</li>`).join('');
            } else {
                modListContainer.classList.add('hidden');
            }

        } else {
            // Main profiler view
            profileOnlineStatus.textContent = 'Offline';
            profileOnlineStatus.style.color = 'var(--accent-danger)';
            profileMotd.textContent = data.error || 'Failed to connect.';
            profilePlayers.textContent = 'N/A';
            profileVersion.textContent = 'N/A';
            profileType.textContent = 'N/A';
            modListContainer.classList.add('hidden');

            // Dashboard summary
            profileOnlineStatusSummary.textContent = 'Offline';
            profileOnlineStatusSummary.style.color = 'var(--accent-danger)';
            profileVersionSummary.textContent = 'N/A';
            profilePlayersSummary.textContent = 'N/A';
        }
    };

    const logToScreen = (logData) => {
        if (!logContainer) return; // Guard against errors if element not found
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

    const populateExploits = async () => {
        try {
            const exploits = await fetchAPI('/api/exploits', { headers: getHeaders() });
            
            // Populate attack form dropdown
            exploitSelect.innerHTML = '';
            const categories = {};
            exploits.forEach(exploit => {
                if (!categories[exploit.category]) categories[exploit.category] = [];
                categories[exploit.category].push(exploit);
            });
            for (const category in categories) {
                const optgroup = document.createElement('optgroup');
                optgroup.label = category;
                categories[category].forEach(exploit => {
                    const option = document.createElement('option');
                    option.value = exploit.id;
                    option.textContent = exploit.name;
                    option.disabled = exploit.disabled;
                    optgroup.appendChild(option);
                });
                exploitSelect.appendChild(optgroup);
            }

            // Populate exploit library view
            exploitLibraryList.innerHTML = '';
             for (const category in categories) {
                const categoryDiv = document.createElement('div');
                categoryDiv.className = 'exploit-category';
                const categoryTitle = document.createElement('h3');
                categoryTitle.textContent = category;
                categoryDiv.appendChild(categoryTitle);
                
                const list = document.createElement('ul');
                categories[category].forEach(exploit => {
                    const item = document.createElement('li');
                    item.innerHTML = `<strong>${exploit.name}</strong><p>${exploit.description}</p>`;
                    list.appendChild(item);
                });
                categoryDiv.appendChild(list);
                exploitLibraryList.appendChild(categoryDiv);
            }

        } catch (error) {
            exploitSelect.innerHTML = '<option value="">Error loading exploits</option>';
            exploitLibraryList.innerHTML = '<p>Could not load exploit library. Check API key and controller status.</p>';
        }
    };

    // --- SPA Navigation ---
    const switchView = (viewName) => {
        views.forEach(view => view.classList.add('hidden'));
        const targetView = document.getElementById(`${viewName}-view`);
        if (targetView) {
            targetView.classList.remove('hidden');
        }

        navItems.forEach(item => {
            if (item.dataset.view === viewName) {
                item.classList.add('active');
                viewTitle.textContent = item.querySelector('span').textContent;
            } else {
                item.classList.remove('active');
            }
        });
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
        logToScreen({ level: 'SYSTEM', message: 'API Key updated. Reloading exploits...' });
        populateExploits();
    });

    clearLogBtn.addEventListener('click', () => {
        logBox.innerHTML = '';
        logToScreen({ level: 'SYSTEM', message: 'Log view cleared.' });
    });

    profileBtn.addEventListener('click', profileServer);

    navItems.forEach(item => {
        item.addEventListener('click', () => switchView(item.dataset.view));
    });

    // --- Initialization ---
    const init = () => {
        logToScreen({ level: 'SYSTEM', message: 'Voidout UI initialized.' });
        setupWebSocket();
        populateExploits();
        switchView('dashboard'); // Set initial view
        
        // Auto-fill profiler from dashboard form if empty
        profileHostInput.value = document.getElementById('host').value;
        profilePortInput.value = document.getElementById('port').value;
    };

    init();
});
