(() => {
    const attachForm = (formId, handler) => {
        const form = document.getElementById(formId);
        if (!form) return;
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            await handler(new FormData(form), form);
        });
    };

    const sendRequest = async (path, method, payload) => {
        const options = payload === undefined
            ? { method }
            : {
                  method,
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(payload),
              };
        const response = await fetch(window.ReporterHelpers.withToken(path), options);
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || `HTTP ${response.status}`);
        }
    };

    const init = ({ setMessage, refreshLists }) => {
        const handle = (formId, buildConfig) => {
            attachForm(formId, async (formData, form) => {
                const config = buildConfig(formData);
                if (!config) {
                    return;
                }
                const {
                    path,
                    method,
                    payload,
                    successMessage,
                    reset = true,
                } = config;
                try {
                    await sendRequest(path, method, payload);
                    if (reset) form.reset();
                    setMessage(successMessage);
                    refreshLists();
                } catch (error) {
                    const message = error.message.startsWith('HTTP')
                        ? `Request failed: ${error.message}`
                        : error.message;
                    setMessage(message, 'error');
                }
            });
        };

        handle('create-list-form', (formData) => {
            const name = (formData.get('name') || '').trim();
            const descriptionValue = (formData.get('description') || '').trim();
            if (!name) {
                setMessage('List name is required.', 'error');
                return null;
            }
            return {
                path: '/api/lists/',
                method: 'POST',
                payload: { name, description: descriptionValue || null },
                successMessage: 'List created successfully.',
            };
        });

        handle('add-item-form', (formData) => {
            const listId = (formData.get('list_id') || '').trim();
            const key = (formData.get('key') || '').trim();
            const value = (formData.get('value') || '').trim() || null;
            const isEnabled = formData.get('is_enabled') === 'true';
            if (!listId) {
                setMessage('List ID is required to add an item.', 'error');
                return null;
            }
            if (!key) {
                setMessage('Item key is required.', 'error');
                return null;
            }
            return {
                path: `/api/items/${encodeURIComponent(listId)}`,
                method: 'POST',
                payload: { key, value, is_enabled: isEnabled },
                successMessage: 'Item added successfully.',
            };
        });

        handle('update-item-form', (formData) => {
            const itemId = (formData.get('item_id') || '').trim();
            if (!itemId) {
                setMessage('Item ID is required for updates.', 'error');
                return null;
            }
            const payload = {};
            const key = (formData.get('key') || '').trim();
            const value = (formData.get('value') || '').trim();
            const state = formData.get('is_enabled');
            if (key) payload.key = key;
            if (value) payload.value = value;
            if (state === 'true') payload.is_enabled = true;
            if (state === 'false') payload.is_enabled = false;
            if (!Object.keys(payload).length) {
                setMessage('Please provide at least one field to update.', 'error');
                return null;
            }
            return {
                path: `/api/items/${encodeURIComponent(itemId)}`,
                method: 'PUT',
                payload,
                successMessage: 'Item updated successfully.',
            };
        });

        handle('delete-item-form', (formData) => {
            const itemId = (formData.get('item_id') || '').trim();
            if (!itemId) {
                setMessage('Item ID is required for deletion.', 'error');
                return null;
            }
            return {
                path: `/api/items/${encodeURIComponent(itemId)}`,
                method: 'DELETE',
                payload: undefined,
                successMessage: 'Item deleted successfully.',
            };
        });

        handle('delete-list-form', (formData) => {
            const listId = (formData.get('list_id') || '').trim();
            if (!listId) {
                setMessage('List ID is required for deletion.', 'error');
                return null;
            }
            return {
                path: `/api/lists/${encodeURIComponent(listId)}`,
                method: 'DELETE',
                payload: undefined,
                successMessage: 'List deleted successfully.',
            };
        });
    };

    window.ReporterForms = { init };
})();

