(() => {
    const qs = (selector) => document.querySelector(selector);
    const myList = qs('#my-keys-list');
    const myEmpty = qs('#my-keys-empty');
    const contactList = qs('#contact-keys-list');
    const contactEmpty = qs('#contact-keys-empty');
    const myCountBadge = qs('[data-role="my-count-badge"]');
    const contactCountBadge = qs('[data-role="contact-count-badge"]');
    const messageArea = qs('#message-area');
    const addForm = qs('#add-contact-form');
    const nameInput = qs('#contact-name');
    const keyInput = qs('#contact-key');

    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const basePath = window.location.pathname.replace(/\/$/, '');

    const withAuth = (init = {}) => {
        const headers = new Headers(init.headers || undefined);
        headers.set('Authorization', `Bearer ${token}`);
        return {
            ...init,
            headers,
        };
    };

    const requestJson = async (endpoint, init) => {
        const response = await fetch(`${basePath}${endpoint}`, withAuth(init));
        let payload = null;

        try {
            payload = await response.json();
        } catch (error) {
            payload = null;
        }

        if (response.status === 401) {
            const authError = new Error('Session expired. Please log in again from the desktop application.');
            authError.code = 'unauthorized';
            throw authError;
        }

        if (response.status === 503) {
            const lockedError = new Error(
                (payload && payload.error) ||
                    'The keyring is locked. Start the desktop app and log in to unlock it.',
            );
            lockedError.code = 'locked';
            throw lockedError;
        }

        if (!response.ok) {
            const genericError = new Error(
                (payload && payload.error) || 'Unable to complete the requested action.',
            );
            genericError.code = 'error';
            throw genericError;
        }

        return payload || {};
    };

    const showMessage = (kind, text) => {
        if (!messageArea) {
            return;
        }
        messageArea.textContent = text;
        messageArea.className = `message ${kind}`;
        messageArea.hidden = false;
    };

    const clearMessage = () => {
        if (!messageArea) {
            return;
        }
        messageArea.textContent = '';
        messageArea.className = 'message';
        messageArea.hidden = true;
    };

    const handleAuthError = () => {
        showMessage('error', 'Session expired. Please log in again from the desktop application.');
    };

    const renderKeyList = (container, emptyLabel, items) => {
        if (!container || !emptyLabel) {
            return;
        }
        container.innerHTML = '';
        if (!items || items.length === 0) {
            emptyLabel.hidden = false;
            return;
        }

        emptyLabel.hidden = true;
        items.forEach((item) => {
            const card = document.createElement('article');
            card.className = 'key-card';
            card.setAttribute('role', 'listitem');

            const heading = document.createElement('h3');
            heading.textContent = item.name || 'Unnamed key';
            card.appendChild(heading);

            const preview = document.createElement('pre');
            preview.textContent = item.public_key || '';
            card.appendChild(preview);

            const download = document.createElement('button');
            download.type = 'button';
            download.innerHTML = '<i class="fas fa-download"></i> Download';
            download.addEventListener('click', () => {
                const url = `${basePath}/api/public-keys/${encodeURIComponent(item.id)}/download?token=${encodeURIComponent(token)}`;
                const newWindow = window.open(url, '_blank');
                if (newWindow) {
                    newWindow.opener = null;
                }
            });
            card.appendChild(download);

            container.appendChild(card);
        });
    };

    const fetchKeys = () => requestJson('/api/public-keys');

    const updateBadges = (myTotal, contactTotal) => {
        const assign = (element, value) => {
            if (element) {
                element.textContent = String(value);
            }
        };

        assign(myCountBadge, myTotal);
        assign(contactCountBadge, contactTotal);
    };

    const refreshView = async () => {
        clearMessage();
        try {
            const keys = await fetchKeys();
            const myKeys = Array.isArray(keys.my_keys) ? keys.my_keys : [];
            const contactKeys = Array.isArray(keys.contact_keys) ? keys.contact_keys : [];
            updateBadges(myKeys.length, contactKeys.length);
            renderKeyList(myList, myEmpty, myKeys);
            renderKeyList(contactList, contactEmpty, contactKeys);
        } catch (error) {
            if (error.code === 'unauthorized') {
                handleAuthError();
            } else if (error.code === 'locked') {
                showMessage('error', error.message);
            } else {
                showMessage('error', error.message || 'Unable to load keyring data.');
            }
        }
    };

    const submitForm = async (event) => {
        event.preventDefault();
        clearMessage();

        const name = nameInput.value.trim();
        const publicKey = keyInput.value.trim();

        if (!name || !publicKey) {
            showMessage('error', 'Please provide both a contact name and the public key.');
            return;
        }

        try {
            const payload = await requestJson('/api/public-keys', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, public_key: publicKey }),
            });

            nameInput.value = '';
            keyInput.value = '';
            showMessage('success', payload.message || 'Key saved successfully.');
            await refreshView();
        } catch (error) {
            if (error.code === 'unauthorized') {
                handleAuthError();
            } else if (error.code === 'locked') {
                showMessage('error', error.message);
            } else {
                showMessage('error', error.message || 'Failed to save the key.');
            }
        }
    };

    document.addEventListener('DOMContentLoaded', () => {
        if (!token) {
            showMessage('error', 'Missing access token. Open this page through the dashboard.');
            return;
        }

        refreshView();
        if (addForm) {
            addForm.addEventListener('submit', submitForm);
        }
    });
})();