(function () {
    const body = document.body;
    const statusUrl = body.dataset.statusUrl;
    const stopUrl = body.dataset.stopUrl;

    const serviceChip = document.getElementById('service-chip');
    const pollIntervalEl = document.getElementById('poll-interval');
    const heartbeatEl = document.getElementById('last-heartbeat');
    const lastEventEl = document.getElementById('last-event');
    const lastErrorEl = document.getElementById('last-error');
    const activeCountEl = document.getElementById('active-count');
    const historyCountEl = document.getElementById('history-count');
    const logCountEl = document.getElementById('log-count');
    const generatedAtEl = document.getElementById('generated-at');

    const openTable = document.getElementById('open-ports-table');
    const openBody = openTable.querySelector('tbody');
    const openEmpty = document.getElementById('open-empty');

    const historyTable = document.getElementById('history-table');
    const historyBody = historyTable.querySelector('tbody');
    const historyEmpty = document.getElementById('history-empty');

    const logList = document.getElementById('log-list');
    const logsEmpty = document.getElementById('logs-empty');

    const stopButton = document.getElementById('stop-button');
    const actionFeedback = document.getElementById('action-feedback');

    let requestInFlight = false;
    let latestServiceState = {};

    function formatTimestamp(value) {
        if (!value) {
            return '—';
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return value;
        }
        return date.toLocaleString();
    }

    function formatPid(value) {
        if (!value || Number(value) === 0) {
            return '—';
        }
        return String(value);
    }

    function setServiceChip(running, desiredState) {
        serviceChip.className = 'status-chip';
        if (running) {
            serviceChip.classList.add('status-chip--running');
            serviceChip.textContent = desiredState === 'stop' ? 'Stopping…' : 'Running';
        } else {
            serviceChip.classList.add('status-chip--stopped');
            serviceChip.textContent = 'Stopped';
        }
    }

    function renderOpenPorts(rows) {
        openBody.innerHTML = '';
        if (!rows.length) {
            openTable.style.display = 'none';
            openEmpty.style.display = 'block';
            return;
        }
        openTable.style.display = 'table';
        openEmpty.style.display = 'none';

        rows.forEach((row) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${row.protocol || ''}</td>
                <td>${row.address || ''}</td>
                <td>${row.port ?? ''}</td>
                <td>${formatPid(row.pid)}</td>
                <td>${row.process_name || ''}</td>
                <td>${formatTimestamp(row.start_time)}</td>
            `;
            openBody.appendChild(tr);
        });
    }

    function renderHistory(rows) {
        historyBody.innerHTML = '';
        if (!rows.length) {
            historyTable.style.display = 'none';
            historyEmpty.style.display = 'block';
            return;
        }
        historyTable.style.display = 'table';
        historyEmpty.style.display = 'none';

        rows.forEach((row) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${row.protocol || ''}</td>
                <td>${row.address || ''}</td>
                <td>${row.port ?? ''}</td>
                <td>${formatPid(row.pid)}</td>
                <td>${row.process_name || ''}</td>
                <td>${formatTimestamp(row.start_time)}</td>
                <td>${formatTimestamp(row.end_time)}</td>
            `;
            historyBody.appendChild(tr);
        });
    }

    function renderLogs(rows) {
        logList.innerHTML = '';
        if (!rows.length) {
            logList.style.display = 'none';
            logsEmpty.style.display = 'block';
            return;
        }
        logList.style.display = 'block';
        logsEmpty.style.display = 'none';

        rows.forEach((row) => {
            const li = document.createElement('li');
            const timestamp = formatTimestamp(row.timestamp);
            const message = row.message || '';
            const alreadyTagged = /^\s*\[.+\]/.test(message);
            li.textContent = alreadyTagged ? message : `[${timestamp}] ${message}`;
            logList.appendChild(li);
        });
        logList.scrollTop = logList.scrollHeight;
    }

    function updateSnapshot(data) {
        const service = data.service || {};
        latestServiceState = service;
        const openPorts = Array.isArray(data.open_ports) ? data.open_ports : [];
        const history = Array.isArray(data.history) ? data.history : [];
        const logs = Array.isArray(data.logs) ? data.logs : [];

        setServiceChip(Boolean(service.is_running), service.desired_state);
        pollIntervalEl.textContent = service.poll_interval ? `${Number(service.poll_interval).toFixed(1)}s` : '—';
        heartbeatEl.textContent = formatTimestamp(service.last_heartbeat);

        if (history.length) {
            const latest = history[0];
            const latestTimestamp = latest.end_time || latest.start_time;
            lastEventEl.textContent = formatTimestamp(latestTimestamp);
        } else {
            lastEventEl.textContent = '—';
        }

        lastErrorEl.textContent = service.last_error || 'None';
        activeCountEl.textContent = String(openPorts.length);
        historyCountEl.textContent = String(history.length);
        logCountEl.textContent = String(logs.length);
        generatedAtEl.textContent = formatTimestamp(data.generated_at);

        if (service.desired_state === 'stop' && service.is_running) {
            actionFeedback.textContent = 'Stop requested; waiting for the worker to finish.';
        } else if (!service.is_running && !requestInFlight) {
            actionFeedback.textContent = '';
        } else if (!requestInFlight && service.is_running && service.desired_state !== 'stop') {
            actionFeedback.textContent = '';
        }

        renderOpenPorts(openPorts);
        renderHistory(history);
        renderLogs(logs);

        if (!requestInFlight) {
            stopButton.disabled = !service.is_running;
        }
    }

    async function refreshStatus() {
        if (!statusUrl) {
            return;
        }

        try {
            const response = await fetch(statusUrl, { cache: 'no-store' });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            updateSnapshot(data);
        } catch (error) {
            serviceChip.className = 'status-chip status-chip--error';
            serviceChip.textContent = 'Unavailable';
            if (!requestInFlight) {
                actionFeedback.textContent = 'Unable to load the latest monitor status.';
            }
        }
    }

    if (stopButton && stopUrl) {
        stopButton.addEventListener('click', async () => {
            if (requestInFlight) {
                return;
            }
            requestInFlight = true;
            stopButton.disabled = true;
            actionFeedback.textContent = 'Sending stop request…';
            try {
                const response = await fetch(stopUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({}),
                });
                let payload = {};
                try {
                    payload = await response.json();
                } catch (parseError) {
                    payload = {};
                }
                if (!response.ok) {
                    throw new Error(payload.message || 'Request failed');
                }
                actionFeedback.textContent = payload.message || 'Stop request sent.';
            } catch (error) {
                actionFeedback.textContent = 'Unable to send stop request. Please try again.';
            }
            await refreshStatus();
            requestInFlight = false;
            const isRunning = Boolean(latestServiceState && latestServiceState.is_running);
            stopButton.disabled = !isRunning;
        });
    }

    if (statusUrl) {
        refreshStatus();
        setInterval(refreshStatus, 7000);
    }
})();
