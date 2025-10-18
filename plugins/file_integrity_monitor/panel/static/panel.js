(function () {
    const { dataset } = document.body,
        statusUrl = dataset.statusUrl, ackUrl = dataset.ackUrl,
        baselineChip = document.getElementById('baseline-chip'),
        directoriesList = document.getElementById('directories-list'),
        directoriesEmpty = document.getElementById('directories-empty'),
        autoScanEl = document.getElementById('auto-scan'),
        intervalEl = document.getElementById('scan-interval'),
        baselineTimeEl = document.getElementById('baseline-time'), baselineCountEl = document.getElementById('baseline-count'),
        generatedAtEl = document.getElementById('generated-at'), lastScanMessage = document.getElementById('last-scan-message'),
        lastScanTrigger = document.getElementById('last-scan-trigger'), lastScanChanged = document.getElementById('last-scan-changed'),
        lastScanDeleted = document.getElementById('last-scan-deleted'), lastScanNew = document.getElementById('last-scan-new'),
        acknowledgeButton = document.getElementById('acknowledge-button'), acknowledgeStatus = document.getElementById('acknowledge-status'),
        historyTable = document.getElementById('history-table'),
        historyBody = historyTable.querySelector('tbody'),
        historyEmpty = document.getElementById('history-empty');
    let pendingSignature = null;
    function formatTimestamp(value) {
        if (!value) return '—';
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
    }
    function updateBaselineChip(hasBaseline) {
        baselineChip.className = 'status-chip';
        if (hasBaseline) {
            baselineChip.classList.add('status-chip--ready');
            baselineChip.textContent = 'Baseline ready';
        } else {
            baselineChip.classList.add('status-chip--missing');
            baselineChip.textContent = 'Baseline missing';
        }
    }
    function renderDirectories(entries) {
        directoriesList.innerHTML = '';
        const hasEntries = entries.length > 0;
        directoriesList.style.display = hasEntries ? 'block' : 'none';
        directoriesEmpty.style.display = hasEntries ? 'none' : 'block';
        if (!hasEntries) return;
        const fragment = document.createDocumentFragment();
        entries.forEach((path) => {
            const li = document.createElement('li');
            li.textContent = path;
            fragment.appendChild(li);
        });
        directoriesList.appendChild(fragment);
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
            ['run_at', 'trigger', 'changed_count', 'deleted_count', 'new_count', 'message'].forEach((key, index) => {
                const cell = document.createElement('td');
                if (key === 'run_at') cell.textContent = formatTimestamp(row.run_at);
                else if (key === 'message') {
                    cell.textContent = `${row.message || ''}${row.acknowledged ? ' (acknowledged)' : ''}`;
                } else cell.textContent = index >= 2 ? String(row[key] ?? 0) : row[key] || '—';
                tr.appendChild(cell);
            });
            historyBody.appendChild(tr);
        });
    }
    function updateAcknowledgeUI(scan) {
        if (!acknowledgeButton || !acknowledgeStatus) return;
        const hasFindings = (Number(scan?.changed_count ?? 0) + Number(scan?.deleted_count ?? 0) + Number(scan?.new_count ?? 0)) > 0;
        const acknowledged = Boolean(scan?.acknowledged);
        pendingSignature = hasFindings && !acknowledged ? scan?.signature || null : null;
        acknowledgeButton.disabled = !pendingSignature || !ackUrl;
        acknowledgeStatus.textContent = acknowledged
            ? 'Already acknowledged.'
            : pendingSignature
                ? 'Acknowledge to hide repeated alerts.'
                : '';
    }
    function renderLastScan(scan) {
        if (!scan) {
            lastScanMessage.textContent = 'No scans have been recorded yet.';
            lastScanTrigger.textContent = '—';
            lastScanChanged.textContent = lastScanDeleted.textContent = lastScanNew.textContent = '0';
            updateAcknowledgeUI(null);
            return;
        }
        lastScanMessage.textContent = scan.message || 'Scan finished.';
        lastScanTrigger.textContent = scan.trigger || 'Unknown';
        lastScanChanged.textContent = String(scan.changed_count ?? 0); lastScanDeleted.textContent = String(scan.deleted_count ?? 0); lastScanNew.textContent = String(scan.new_count ?? 0);
        updateAcknowledgeUI(scan);
    }
    async function refreshStatus() {
        if (!statusUrl) return;
        try {
            const response = await fetch(statusUrl, { credentials: 'include' });
            if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
            const data = await response.json();
            const baseline = data.baseline || {};
            const directories = Array.isArray(data.directories) ? data.directories : [];
            const intervalValue = Number.parseInt(data.interval_minutes, 10);
            const intervalLabel = Number.isFinite(intervalValue) && intervalValue > 0
                ? `${intervalValue} minute${intervalValue === 1 ? '' : 's'}`
                : '—';
            updateBaselineChip(Boolean(baseline.has_baseline));
            renderDirectories(directories);
            autoScanEl.textContent = data.auto_scan ? 'Enabled' : 'Disabled';
            intervalEl.textContent = intervalLabel;
            baselineTimeEl.textContent = formatTimestamp(baseline.captured_at);
            baselineCountEl.textContent = String(baseline.count ?? 0);
            generatedAtEl.textContent = formatTimestamp(data.generated_at);
            renderLastScan(data.last_scan);
            renderHistory(Array.isArray(data.history) ? data.history : []);
        } catch (error) {
            baselineChip.className = 'status-chip status-chip--missing';
            baselineChip.textContent = 'Status unavailable';
            lastScanMessage.textContent = error.message;
            historyTable.style.display = 'none';
            historyEmpty.style.display = 'block';
        }
    }
    async function acknowledgeCurrent() {
        if (!ackUrl || !pendingSignature) return;
        acknowledgeButton.disabled = true;
        acknowledgeStatus.textContent = 'Sending acknowledgement…';
        try {
            const response = await fetch(ackUrl, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ signature: pendingSignature }),
            });
            if (!response.ok) throw new Error('Failed to acknowledge changes.');
            acknowledgeStatus.textContent = 'Changes acknowledged.';
            pendingSignature = null;
            await refreshStatus();
        } catch (error) {
            acknowledgeStatus.textContent = error.message;
            acknowledgeButton.disabled = false;
        }
    }
    if (acknowledgeButton) acknowledgeButton.addEventListener('click', acknowledgeCurrent);
    refreshStatus();
    setInterval(refreshStatus, 15000);
})();
