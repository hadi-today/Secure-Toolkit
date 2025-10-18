
(function () {
    const STORAGE_KEY_SELECTED = 'secureEditorSelectedKey';

    const state = {
        token: null,
        baseUrl: window.location.pathname.replace(/\/$/, ''),
        notes: [],
        versions: [],
        selectedNoteId: null,
        selectedVersionId: null,
        compareTarget: '',
        keys: [],
        selectedKey: null,
        blockedRequest: null,
    };

    const elements = {
        status: document.getElementById('status-message'),
        notesList: document.getElementById('notes-list'),
        versionsList: document.getElementById('versions-list'),
        compareSelect: document.getElementById('compare-select'),
        contentView: document.getElementById('content-view'),
        contentTitle: document.getElementById('content-title'),
        diffViewer: document.getElementById('diff-viewer'),
        comparisonLabel: document.getElementById('comparison-label'),
        summaryCount: document.getElementById('summary-note-count'),
        summaryUpdated: document.getElementById('summary-updated'),
        keySelect: document.getElementById('key-select'),
        keyStatus: document.getElementById('key-status'),
        keyPassphrase: document.getElementById('key-passphrase'),
        keyPassphraseWrapper: document.getElementById('key-passphrase-wrapper'),
        unlockButton: document.getElementById('unlock-key-button'),
    };

    function extractToken() {
        const params = new URLSearchParams(window.location.search);
        const queryToken = params.get('token');
        if (queryToken) {
            localStorage.setItem('authToken', queryToken);
            return queryToken;
        }
        const stored = localStorage.getItem('authToken');
        if (stored) {
            return stored;
        }
        const cookieMatch = document.cookie.match(/(?:^|; )authToken=([^;]+)/);
        return cookieMatch ? decodeURIComponent(cookieMatch[1]) : null;
    }

    function setStatus(message, isError = false) {
        if (!elements.status) {
            return;
        }
        elements.status.textContent = message;
        elements.status.classList.toggle('error', Boolean(isError));
    }

    function setKeyStatus(message, isError = false) {
        if (!elements.keyStatus) {
            return;
        }
        elements.keyStatus.textContent = message;
        elements.keyStatus.classList.toggle('error', Boolean(isError));
    }

    function storeSelectedKey(value) {
        if (value) {
            localStorage.setItem(STORAGE_KEY_SELECTED, value);
        } else {
            localStorage.removeItem(STORAGE_KEY_SELECTED);
        }
    }

    function getKeyInfo(name) {
        if (!name) {
            return null;
        }
        return state.keys.find((key) => key.name === name) || null;
    }

    function refreshKeyUnlockState(keyName, unlocked) {
        const key = getKeyInfo(keyName);
        if (key) {
            key.is_unlocked = Boolean(unlocked);
        }
    }

    function formatTimestamp(timestamp) {
        if (!timestamp) {
            return '—';
        }
        const date = new Date(timestamp);
        if (Number.isNaN(date.getTime())) {
            return timestamp;
        }
        return date.toLocaleString();
    }

    function renderNotes() {
        elements.notesList.innerHTML = '';
        if (!state.notes.length) {
            const emptyItem = document.createElement('li');
            emptyItem.className = 'empty';
            emptyItem.textContent = 'No notes have been saved yet.';
            elements.notesList.appendChild(emptyItem);
            elements.summaryCount.textContent = '0 notes';
            elements.summaryUpdated.textContent = 'Last update: -';
            return;
        }

        let latestTimestamp = null;

        state.notes.forEach((note) => {
            if (note.latest_timestamp && (!latestTimestamp || note.latest_timestamp > latestTimestamp)) {
                latestTimestamp = note.latest_timestamp;
            }

            const item = document.createElement('li');
            item.dataset.noteId = String(note.id);
            item.innerHTML = `
                <strong>${note.name}</strong>
                <span class="meta">${note.version_count} version${note.version_count === 1 ? '' : 's'} · Updated ${formatTimestamp(note.latest_timestamp)}</span>
            `;
            if (state.selectedNoteId === note.id) {
                item.classList.add('active');
            }
            elements.notesList.appendChild(item);
        });

        const noteLabel = state.notes.length === 1 ? 'note' : 'notes';
        elements.summaryCount.textContent = `${state.notes.length} ${noteLabel}`;
        elements.summaryUpdated.textContent = latestTimestamp
            ? `Last update: ${formatTimestamp(latestTimestamp)}`
            : 'Last update: -';
    }

    function updateKeyStatus() {
        if (!elements.keySelect) {
            return;
        }

        const keyInfo = getKeyInfo(state.selectedKey);

        if (!keyInfo) {
            if (elements.keyPassphraseWrapper) {
                elements.keyPassphraseWrapper.classList.add('hidden');
            }
            if (elements.unlockButton) {
                elements.unlockButton.disabled = true;
                elements.unlockButton.textContent = 'Unlock';
            }
            if (!state.keys.length) {
                setKeyStatus('No private keys available in the keyring.', true);
            } else {
                setKeyStatus('Select a key to check its status.');
            }
            return;
        }

        if (elements.keySelect.value !== keyInfo.name) {
            elements.keySelect.value = keyInfo.name;
        }

        if (elements.unlockButton) {
            elements.unlockButton.disabled = !keyInfo.has_private_key;
            if (keyInfo.is_encrypted) {
                elements.unlockButton.textContent = keyInfo.is_unlocked ? 'Unlock again' : 'Unlock key';
            } else {
                elements.unlockButton.textContent = 'Use key';
            }
        }

        if (elements.keyPassphraseWrapper) {
            if (keyInfo.is_encrypted) {
                elements.keyPassphraseWrapper.classList.remove('hidden');
                if (!keyInfo.is_unlocked && elements.keyPassphrase) {
                    elements.keyPassphrase.value = '';
                }
            } else {
                elements.keyPassphraseWrapper.classList.add('hidden');
                if (elements.keyPassphrase) {
                    elements.keyPassphrase.value = '';
                }
            }
        }

        if (!keyInfo.has_private_key) {
            setKeyStatus(`No private key stored for '${keyInfo.name}'.`, true);
            return;
        }

        if (keyInfo.is_encrypted) {
            setKeyStatus(
                keyInfo.is_unlocked
                    ? `'${keyInfo.name}' is unlocked for this session.`
                    : `'${keyInfo.name}' is locked. Enter the passphrase to unlock.`,
                !keyInfo.is_unlocked
            );
        } else {
            setKeyStatus(`'${keyInfo.name}' is ready to decrypt versions.`);
        }
    }

    function renderKeyControls() {
        if (!elements.keySelect) {
            return;
        }

        elements.keySelect.innerHTML = '';

        if (!state.keys.length) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No keys available';
            elements.keySelect.appendChild(option);
            elements.keySelect.disabled = true;
            if (elements.unlockButton) {
                elements.unlockButton.disabled = true;
                elements.unlockButton.textContent = 'Unlock';
            }
            if (elements.keyPassphraseWrapper) {
                elements.keyPassphraseWrapper.classList.add('hidden');
            }
            storeSelectedKey(null);
            setKeyStatus('No private keys available in the keyring.', true);
            return;
        }

        elements.keySelect.disabled = false;

        const stored = localStorage.getItem(STORAGE_KEY_SELECTED);
        if (!state.selectedKey && stored && getKeyInfo(stored)) {
            state.selectedKey = stored;
        }
        if (!state.selectedKey || !getKeyInfo(state.selectedKey)) {
            state.selectedKey = state.keys[0].name;
        }

        state.keys.forEach((key) => {
            const option = document.createElement('option');
            option.value = key.name;
            option.textContent = key.is_encrypted ? `${key.name} (encrypted)` : key.name;
            elements.keySelect.appendChild(option);
        });

        if (state.selectedKey) {
            elements.keySelect.value = state.selectedKey;
            storeSelectedKey(state.selectedKey);
        }

        updateKeyStatus();
    }

    function renderVersions() {
        elements.versionsList.innerHTML = '';
        elements.compareSelect.innerHTML = '<option value="">Previous version</option>';
        elements.compareSelect.disabled = state.versions.length < 2;

        if (!state.versions.length) {
            const emptyItem = document.createElement('li');
            emptyItem.className = 'empty';
            emptyItem.textContent = state.selectedNoteId
                ? 'This note has no saved versions yet.'
                : 'Select a note to see its versions.';
            elements.versionsList.appendChild(emptyItem);
            return;
        }

        state.versions.forEach((version) => {
            const item = document.createElement('li');
            item.dataset.versionId = String(version.id);
            item.innerHTML = `
                <strong>${formatTimestamp(version.timestamp)}</strong>
                <span class="meta">Encrypted with ${version.key_name}</span>
            `;
            if (state.selectedVersionId === version.id) {
                item.classList.add('active');
            }
            elements.versionsList.appendChild(item);

            const option = document.createElement('option');
            option.value = String(version.id);
            option.textContent = `${formatTimestamp(version.timestamp)} (${version.key_name})`;
            elements.compareSelect.appendChild(option);
        });

        if (state.compareTarget) {
            const existing = Array.from(elements.compareSelect.options).some((opt) => opt.value === state.compareTarget);
            elements.compareSelect.value = existing ? state.compareTarget : '';
        } else {
            elements.compareSelect.value = '';
        }
    }

    function highlightSelection(container, selectedId, attribute) {
        Array.from(container.querySelectorAll('li')).forEach((item) => {
            if (item.dataset[attribute] === String(selectedId)) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }

    function showPlaceholderContent(message) {
        elements.contentTitle.textContent = 'Select a version to preview';
        elements.contentView.innerHTML = `<p class="placeholder">${message}</p>`;
        elements.diffViewer.innerHTML = 'A side-by-side diff will appear here once two versions are available.';
        elements.diffViewer.classList.add('placeholder');
        elements.comparisonLabel.textContent = 'No comparison selected.';
    }

    async function loadKeys() {
        if (!elements.keySelect) {
            return;
        }
        setKeyStatus('Loading keys…');
        try {
            const response = await fetch(`${state.baseUrl}/api/keys`, {
                headers: { Authorization: `Bearer ${state.token}` },
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(payload.error || 'Unable to load keys.');
            }
            state.keys = Array.isArray(payload.keys) ? payload.keys : [];
            renderKeyControls();
            if (!state.keys.length) {
                return;
            }
            updateKeyStatus();
        } catch (error) {
            console.error('Failed to load keys', error);
            state.keys = [];
            renderKeyControls();
            setKeyStatus(`Failed to load keys: ${error.message}`, true);
        }
    }

    async function unlockSelectedKey() {
        if (!state.selectedKey) {
            setKeyStatus('Select a key to unlock it.', true);
            return;
        }

        const keyInfo = getKeyInfo(state.selectedKey);
        if (!keyInfo) {
            setKeyStatus('Selected key is not available.', true);
            return;
        }

        if (!keyInfo.has_private_key) {
            setKeyStatus(`No private key stored for '${keyInfo.name}'.`, true);
            return;
        }

        const payload = { key_name: keyInfo.name };
        if (keyInfo.is_encrypted && elements.keyPassphrase) {
            payload.passphrase = elements.keyPassphrase.value;
        }

        try {
            if (elements.unlockButton) {
                elements.unlockButton.disabled = true;
                elements.unlockButton.textContent = 'Unlocking…';
            }
            const response = await fetch(`${state.baseUrl}/api/keys/unlock`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${state.token}`,
                },
                body: JSON.stringify(payload),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(data.error || 'Unable to unlock key.');
            }
            if (keyInfo.is_encrypted) {
                refreshKeyUnlockState(keyInfo.name, true);
                if (elements.keyPassphrase) {
                    elements.keyPassphrase.value = '';
                }
            }
            setKeyStatus(data.message || 'Key unlocked successfully.');
            updateKeyStatus();
            storeSelectedKey(keyInfo.name);

            if (
                state.blockedRequest &&
                state.blockedRequest.keyName === keyInfo.name &&
                state.blockedRequest.noteId &&
                state.blockedRequest.versionId
            ) {
                const { noteId, versionId } = state.blockedRequest;
                state.blockedRequest = null;
                loadVersionDetails(noteId, versionId);
            }
        } catch (error) {
            console.error('Failed to unlock key', error);
            refreshKeyUnlockState(state.selectedKey, false);
            setKeyStatus(error.message, true);
        } finally {
            if (elements.unlockButton) {
                elements.unlockButton.disabled = false;
            }
            updateKeyStatus();
        }
    }

    async function loadNotes() {
        setStatus('Loading notes…');
        try {
            const response = await fetch(`${state.baseUrl}/api/notes`, {
                headers: { Authorization: `Bearer ${state.token}` },
            });
            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                throw new Error(payload.error || 'Unexpected server response.');
            }
            const data = await response.json();
            state.notes = Array.isArray(data.notes) ? data.notes : [];
            renderNotes();
            setStatus(`Loaded ${state.notes.length} note${state.notes.length === 1 ? '' : 's'}.`);
        } catch (error) {
            console.error('Failed to load notes', error);
            setStatus(`Failed to load notes: ${error.message}`, true);
            showPlaceholderContent('Unable to load notes. Check the desktop application and try again.');
        }
    }

    async function loadVersions(noteId) {
        setStatus('Loading versions…');
        try {
            const response = await fetch(`${state.baseUrl}/api/notes/${noteId}/versions`, {
                headers: { Authorization: `Bearer ${state.token}` },
            });
            if (!response.ok) {
                const payload = await response.json().catch(() => ({}));
                throw new Error(payload.error || 'Unexpected server response.');
            }
            const data = await response.json();
            state.versions = Array.isArray(data.versions) ? data.versions : [];
            renderVersions();
            setStatus(state.versions.length ? 'Pick a version to see its contents.' : 'No versions found for this note.');
            if (!state.versions.length) {
                showPlaceholderContent('This note does not have any saved versions yet.');
            }
        } catch (error) {
            console.error('Failed to load versions', error);
            setStatus(`Failed to load versions: ${error.message}`, true);
            showPlaceholderContent('Unable to load version history.');
        }
    }

    async function loadVersionDetails(noteId, versionId) {
        setStatus('Decrypting version…');

        const versionMeta = state.versions.find((version) => version.id === versionId);
        if (versionMeta) {
            const keyInfo = getKeyInfo(versionMeta.key_name);
            if (keyInfo && keyInfo.is_encrypted && !keyInfo.is_unlocked) {
                state.blockedRequest = { noteId, versionId, keyName: versionMeta.key_name };
                state.selectedKey = versionMeta.key_name;
                if (elements.keySelect && keyInfo) {
                    elements.keySelect.value = keyInfo.name;
                }
                if (keyInfo) {
                    storeSelectedKey(keyInfo.name);
                }
                updateKeyStatus();
                setKeyStatus(`'${versionMeta.key_name}' is locked. Enter the passphrase above to view this version.`, true);
                showPlaceholderContent('Unlock the required private key to preview this version.');
                setStatus(`Unlock '${versionMeta.key_name}' to view this version.`, true);
                return;
            }
        }

        let lastPayload = null;

        try {
            const params = new URLSearchParams();
            if (state.compareTarget) {
                params.set('compare_to', state.compareTarget);
            }
            const query = params.toString();
            const url = `${state.baseUrl}/api/notes/${noteId}/versions/${versionId}${query ? `?${query}` : ''}`;
            const response = await fetch(url, {
                headers: { Authorization: `Bearer ${state.token}` },
            });
            const payload = await response.json().catch(() => ({}));
            lastPayload = payload;
            if (!response.ok) {
                throw new Error(payload.error || 'Unable to decrypt version.');
            }
            if (!payload || !payload.version) {
                throw new Error('Malformed response received from server.');
            }

            const note = state.notes.find((n) => n.id === noteId);
            const title = note ? `${note.name} — ${formatTimestamp(payload.version.timestamp)}` : formatTimestamp(payload.version.timestamp);
            elements.contentTitle.textContent = title;
            elements.contentView.innerHTML = payload.version.content_html
                ? `<article>${payload.version.content_html}</article>`
                : '<p class="placeholder">This version does not contain any content.</p>';
            elements.diffViewer.classList.remove('placeholder');

            if (payload.diff_html) {
                elements.diffViewer.innerHTML = payload.diff_html;
                if (payload.comparison) {
                    elements.comparisonLabel.textContent = `Comparing with version from ${formatTimestamp(payload.comparison.timestamp)}.`;
                    if (!state.compareTarget) {
                        elements.compareSelect.value = String(payload.comparison.id);
                    }
                } else {
                    elements.comparisonLabel.textContent = 'Comparison information unavailable.';
                }
            } else {
                elements.diffViewer.innerHTML = 'No differences to display. Select another version to compare.';
                elements.diffViewer.classList.add('placeholder');
                elements.comparisonLabel.textContent = 'No comparison selected.';
            }
            state.blockedRequest = null;
            setStatus('Version decrypted successfully.');
        } catch (error) {
            console.error('Failed to load version details', error);
            const message = error && error.message ? error.message : 'Unable to decrypt version.';
            setStatus(`Failed to decrypt version: ${message}`, true);
            elements.contentTitle.textContent = 'Unable to display version';
            elements.contentView.innerHTML = `<p class="placeholder">${message}</p>`;
            elements.diffViewer.innerHTML = 'Diff unavailable.';
            elements.diffViewer.classList.add('placeholder');
            elements.comparisonLabel.textContent = 'No comparison selected.';

            if (lastPayload && lastPayload.key_name) {
                const keyName = lastPayload.key_name;
                const keyInfo = getKeyInfo(keyName);
                if (!keyInfo) {
                    loadKeys();
                }
                state.selectedKey = keyName;
                if (elements.keySelect && keyInfo) {
                    elements.keySelect.value = keyInfo.name;
                }
                if (keyInfo) {
                    storeSelectedKey(keyInfo.name);
                }
                if (!keyInfo) {
                    setKeyStatus(`Private key '${keyName}' is not available in the keyring.`, true);
                } else if (lastPayload.requires_passphrase) {
                    refreshKeyUnlockState(keyName, false);
                    state.blockedRequest = { noteId, versionId, keyName };
                    setKeyStatus(`Enter the passphrase for '${keyName}' to continue.`, true);
                }
                updateKeyStatus();
            }
        }
    }

    elements.notesList.addEventListener('click', (event) => {
        const listItem = event.target.closest('li');
        if (!listItem || !listItem.dataset.noteId) {
            return;
        }
        const noteId = Number.parseInt(listItem.dataset.noteId, 10);
        if (Number.isNaN(noteId)) {
            return;
        }
        state.selectedNoteId = noteId;
        state.selectedVersionId = null;
        state.compareTarget = '';
        state.blockedRequest = null;
        highlightSelection(elements.notesList, noteId, 'noteId');
        showPlaceholderContent('Select a version to preview.');
        loadVersions(noteId);
    });

    elements.versionsList.addEventListener('click', (event) => {
        const listItem = event.target.closest('li');
        if (!listItem || !listItem.dataset.versionId || !state.selectedNoteId) {
            return;
        }
        const versionId = Number.parseInt(listItem.dataset.versionId, 10);
        if (Number.isNaN(versionId)) {
            return;
        }
        state.selectedVersionId = versionId;
        if (!state.compareTarget) {
            elements.compareSelect.value = '';
        }
        highlightSelection(elements.versionsList, versionId, 'versionId');
        loadVersionDetails(state.selectedNoteId, versionId);
    });

    elements.compareSelect.addEventListener('change', () => {
        if (!state.selectedNoteId || !state.selectedVersionId) {
            return;
        }
        const value = elements.compareSelect.value;
        state.compareTarget = value && value !== String(state.selectedVersionId) ? value : '';
        loadVersionDetails(state.selectedNoteId, state.selectedVersionId);
    });

    if (elements.keySelect) {
        elements.keySelect.addEventListener('change', () => {
            const value = elements.keySelect.value;
            if (value && getKeyInfo(value)) {
                state.selectedKey = value;
                storeSelectedKey(value);
            } else {
                state.selectedKey = null;
                storeSelectedKey(null);
            }
            updateKeyStatus();
        });
    }

    if (elements.unlockButton) {
        elements.unlockButton.addEventListener('click', (event) => {
            event.preventDefault();
            unlockSelectedKey();
        });
    }

    if (elements.keyPassphrase) {
        elements.keyPassphrase.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                unlockSelectedKey();
            }
        });
    }

    async function initialisePanel() {
        state.token = extractToken();
        if (!state.token) {
            setStatus('Missing session token. Please log in again from the dashboard.', true);
            showPlaceholderContent('Authentication token missing. Return to the dashboard and reopen the panel.');
            return;
        }
        await loadKeys();
        await loadNotes();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialisePanel);
    } else {
        initialisePanel();
    }
})();
