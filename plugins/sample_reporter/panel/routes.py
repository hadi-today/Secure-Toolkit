# plugins/sample_reporter/panel/routes.py

from flask import Blueprint, Response

from plugins.web_panel.server.database import db
from plugins.web_panel.server.database import ManagedList, ListItem
from plugins.web_panel.server.web_auth import token_required

reporter_bp = Blueprint('reporter', __name__)


@reporter_bp.route('/')
@token_required
def report_page():
    """Generates a web page to display and manage lists."""
    list_name_to_find = "Monitored Sites"
    html_parts = [
        """
        <html>
        <head>
            <meta charset='utf-8'>
            <title>Sample Reporter</title>
            <style>
                body { font-family: sans-serif; padding: 20px; background: #f5f7fa; }
                h1 { color: #1f4f82; }
                h2 { margin-top: 32px; color: #294c60; }
                h3 { color: #3d627a; margin-bottom: 8px; }
                section { background: #ffffff; padding: 16px 20px; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); margin-bottom: 24px; }
                .list-card { border: 1px solid #d4dce3; border-radius: 10px; padding: 12px 16px; margin-bottom: 16px; background: #fbfdff; }
                .list-card h4 { margin: 0 0 8px; color: #0f3d5c; }
                .list-card ul { padding-left: 20px; }
                form { display: grid; gap: 12px; margin-bottom: 20px; }
                label { font-weight: 600; color: #233746; }
                input[type='text'], input[type='number'], textarea, select { padding: 8px 10px; border: 1px solid #c0c7d0; border-radius: 8px; font-size: 14px; }
                textarea { resize: vertical; min-height: 70px; }
                button { width: fit-content; padding: 8px 16px; border-radius: 8px; border: none; background: #1f7a8c; color: white; font-weight: 600; cursor: pointer; }
                button:hover { background: #136273; }
                #api-message { min-height: 20px; font-weight: 600; }
                .inline { display: flex; gap: 12px; align-items: center; }
                .inline label { font-weight: 500; }
                .help { font-size: 13px; color: #5a6a75; }
            </style>
        </head>
        <body>
            <h1>Sample Reporter &amp; List Manager</h1>
            <p>
                This page demonstrates the consistency between reading directly from the database and using the REST APIs available in the
                <code>web_panel</code> plugin. The first section reads the data from the database, and the second section
                allows you to modify the data through Create, Update, and Delete requests.
            </p>
        """
    ]

    try:
        target_list = ManagedList.query.filter_by(name=list_name_to_find).first()

        created_list = False
        if not target_list:
            target_list, created_list = _create_sample_list(list_name_to_find)

        if target_list:
            html_parts.append("<section>")
            html_parts.append(f"<h2>Server-side snapshot for '{list_name_to_find}'</h2>")
            if created_list:
                html_parts.append(
                    "<p style='color: green;'>Sample data was missing, so it has now been created automatically.</p>"
                )

            html_parts.append(f"<p>Found {len(target_list.items)} item(s):</p>")
            html_parts.append("<ul style='list-style-type: square;'>")
            for item in target_list.items:
                status = "Enabled" if item.is_enabled else "Disabled"
                html_parts.append(
                    f"<li><b>{item.key}</b>: {item.value or '<i>No value</i>'} <i>({status})</i></li>"
                )
            html_parts.append("</ul>")
            html_parts.append("</section>")
        else:
            html_parts.append("<section>")
            html_parts.append(
                f"<p style='color: red;'>The list '{list_name_to_find}' could not be created automatically.</p>"
            )
            html_parts.append("</section>")

    except Exception as e:
        html_parts.append("<section>")
        html_parts.append(f"<p style='color: red;'>An error occurred: {e}</p>")
        html_parts.append("</section>")

    html_parts.append(
        """
        <section>
            <h2>Manage lists via REST API</h2>
            <p class='help'>
                The authentication token is automatically passed via the Query String. The forms below use
                Fetch and the internal web_panel APIs to create, update, or delete the data.
            </p>
            <div id="api-message"></div>
            <button id="refresh-lists" type="button">Refresh lists</button>
            <div id="lists-container" style="margin-top: 16px;"></div>

            <h3>Create a new list</h3>
            <form id="create-list-form">
                <label>
                    List name
                    <input type="text" name="name" required placeholder="e.g. New Monitoring Targets">
                </label>
                <label>
                    Description (optional)
                    <textarea name="description" placeholder="Describe what this list contains"></textarea>
                </label>
                <button type="submit">Create list</button>
            </form>

            <h3>Add an item to a list</h3>
            <form id="add-item-form">
                <label>
                    List ID
                    <input type="number" name="list_id" min="1" required>
                </label>
                <label>
                    Item key
                    <input type="text" name="key" required placeholder="e.g. example.com">
                </label>
                <label>
                    Item value (optional)
                    <input type="text" name="value" placeholder="e.g. Uptime OK">
                </label>
                <label>
                    Is enabled?
                    <select name="is_enabled">
                        <option value="true" selected>Enabled</option>
                        <option value="false">Disabled</option>
                    </select>
                </label>
                <button type="submit">Add item</button>
            </form>

            <h3>Update an existing item</h3>
            <form id="update-item-form">
                <label>
                    Item ID
                    <input type="number" name="item_id" min="1" required>
                </label>
                <label>
                    New key (optional)
                    <input type="text" name="key" placeholder="Leave empty to keep current key">
                </label>
                <label>
                    New value (optional)
                    <input type="text" name="value" placeholder="Leave empty to keep current value">
                </label>
                <label>
                    Enabled state
                    <select name="is_enabled">
                        <option value="">No change</option>
                        <option value="true">Enabled</option>
                        <option value="false">Disabled</option>
                    </select>
                </label>
                <button type="submit">Update item</button>
            </form>

            <h3>Delete an item</h3>
            <form id="delete-item-form">
                <label class="inline">
                    <span>Item ID</span>
                    <input type="number" name="item_id" min="1" required>
                </label>
                <button type="submit">Delete item</button>
            </form>

            <h3>Delete a list</h3>
            <form id="delete-list-form">
                <label class="inline">
                    <span>List ID</span>
                    <input type="number" name="list_id" min="1" required>
                </label>
                <button type="submit">Delete list</button>
            </form>
        </section>

        <script>
        (function () {
            const messageBox = document.getElementById('api-message');
            const listsContainer = document.getElementById('lists-container');
            const refreshButton = document.getElementById('refresh-lists');

            const setMessage = (text, type = 'info') => {
                if (!messageBox) { return; }
                messageBox.textContent = text;
                messageBox.style.color = type === 'error' ? '#b20020' : '#0a7a0a';
            };

            const getToken = () => {
                const params = new URLSearchParams(window.location.search);
                return params.get('token');
            };

            const withToken = (url) => {
                const token = getToken();
                if (!token) { return url; }
                return `${url}${url.includes('?') ? '&' : '?'}token=${encodeURIComponent(token)}`;
            };

            const escapeHtml = (unsafe) => {
                if (unsafe === null || unsafe === undefined) { return ''; }
                return String(unsafe)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#39;');
            };

            const renderLists = (lists) => {
                if (!listsContainer) { return; }
                if (!lists.length) {
                    listsContainer.innerHTML = '<p>No lists available yet.</p>';
                    return;
                }

                const html = lists.map((list) => {
                    const items = Array.isArray(list.items) ? list.items : [];
                    const itemsHtml = items.length
                        ? items.map((item) => {
                            const status = item.is_enabled ? 'Enabled' : 'Disabled';
                            const valueContent = item.value ? escapeHtml(item.value) : '<i>No value</i>';
                            return `<li><strong>${escapeHtml(item.key)}</strong>: ${valueContent} <span class="help">(ID ${item.id} – ${status})</span></li>`;
                          }).join('')
                        : '<li><i>No items</i></li>';

                    const description = list.description
                        ? `<p>${escapeHtml(list.description)}</p>`
                        : '<p><i>No description</i></p>';

                    return `
                        <div class="list-card">
                            <h4>${escapeHtml(list.name)} (ID ${list.id})</h4>
                            ${description}
                            <p>Total items: ${items.length}</p>
                            <ul>${itemsHtml}</ul>
                        </div>
                    `;
                }).join('');

                listsContainer.innerHTML = html;
            };

            const fetchLists = async () => {
                if (!listsContainer) { return; }
                listsContainer.innerHTML = '<p>Loading lists…</p>';
                try {
                    const response = await fetch(withToken('/api/lists/'));
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    const lists = await response.json();
                    const detailed = await Promise.all(lists.map(async (list) => {
                        try {
                            const detailResp = await fetch(withToken(`/api/lists/${list.id}`));
                            if (!detailResp.ok) {
                                throw new Error('detail request failed');
                            }
                            return await detailResp.json();
                        } catch (error) {
                            return { ...list, items: [] };
                        }
                    }));
                    renderLists(detailed);
                    setMessage('Lists refreshed successfully.');
                } catch (error) {
                    listsContainer.innerHTML = '<p style="color:#b20020;">Could not load lists.</p>';
                    setMessage(`Failed to load lists: ${error.message}`, 'error');
                }
            };

            if (refreshButton) {
                refreshButton.addEventListener('click', (event) => {
                    event.preventDefault();
                    fetchLists();
                });
            }

            const handleSubmit = (formId, handler) => {
                const form = document.getElementById(formId);
                if (!form) { return; }
                form.addEventListener('submit', async (event) => {
                    event.preventDefault();
                    const formData = new FormData(form);
                    await handler(formData, form);
                });
            };

            handleSubmit('create-list-form', async (formData, form) => {
                const name = formData.get('name') ? formData.get('name').trim() : '';
                const descriptionRaw = formData.get('description');
                const description = descriptionRaw && descriptionRaw.trim() ? descriptionRaw.trim() : null;
                if (!name) {
                    setMessage('List name is required.', 'error');
                    return;
                }

                try {
                    const response = await fetch(withToken('/api/lists/'), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name, description }),
                    });
                    if (!response.ok) {
                        const data = await response.json().catch(() => ({}));
                        throw new Error(data.error || `HTTP ${response.status}`);
                    }
                    form.reset();
                    setMessage('List created successfully.');
                    fetchLists();
                } catch (error) {
                    setMessage(`Failed to create list: ${error.message}`, 'error');
                }
            });

            handleSubmit('add-item-form', async (formData, form) => {
                const listIdRaw = formData.get('list_id');
                const listId = listIdRaw ? listIdRaw.trim() : '';
                const keyRaw = formData.get('key');
                const key = keyRaw ? keyRaw.trim() : '';
                const valueRaw = formData.get('value');
                const value = valueRaw && valueRaw.trim() ? valueRaw.trim() : null;
                const isEnabled = formData.get('is_enabled') === 'true';

                if (!listId) {
                    setMessage('List ID is required to add an item.', 'error');
                    return;
                }
                if (!key) {
                    setMessage('Item key is required.', 'error');
                    return;
                }

                try {
                    const response = await fetch(withToken(`/api/items/${encodeURIComponent(listId)}`), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ key, value, is_enabled: isEnabled }),
                    });
                    if (!response.ok) {
                        const data = await response.json().catch(() => ({}));
                        throw new Error(data.error || `HTTP ${response.status}`);
                    }
                    form.reset();
                    setMessage('Item added successfully.');
                    fetchLists();
                } catch (error) {
                    setMessage(`Failed to add item: ${error.message}`, 'error');
                }
            });

            handleSubmit('update-item-form', async (formData, form) => {
                const itemIdRaw = formData.get('item_id');
                const itemId = itemIdRaw ? itemIdRaw.trim() : '';
                const keyRaw = formData.get('key');
                const valueRaw = formData.get('value');
                const stateRaw = formData.get('is_enabled');

                if (!itemId) {
                    setMessage('Item ID is required for updates.', 'error');
                    return;
                }

                const payload = {};
                if (keyRaw && keyRaw.trim()) {
                    payload.key = keyRaw.trim();
                }
                if (valueRaw && valueRaw.trim()) {
                    payload.value = valueRaw.trim();
                }
                if (stateRaw === 'true') {
                    payload.is_enabled = true;
                } else if (stateRaw === 'false') {
                    payload.is_enabled = false;
                }

                if (Object.keys(payload).length == 0) {
                    setMessage('Please provide at least one field to update.', 'error');
                    return;
                }

                try {
                    const response = await fetch(withToken(`/api/items/${encodeURIComponent(itemId)}`), {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    });
                    if (!response.ok) {
                        const data = await response.json().catch(() => ({}));
                        throw new Error(data.error || `HTTP ${response.status}`);
                    }
                    form.reset();
                    setMessage('Item updated successfully.');
                    fetchLists();
                } catch (error) {
                    setMessage(`Failed to update item: ${error.message}`, 'error');
                }
            });

            handleSubmit('delete-item-form', async (formData, form) => {
                const itemIdRaw = formData.get('item_id');
                const itemId = itemIdRaw ? itemIdRaw.trim() : '';
                if (!itemId) {
                    setMessage('Item ID is required for deletion.', 'error');
                    return;
                }

                try {
                    const response = await fetch(withToken(`/api/items/${encodeURIComponent(itemId)}`), {
                        method: 'DELETE',
                    });
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    form.reset();
                    setMessage('Item deleted successfully.');
                    fetchLists();
                } catch (error) {
                    setMessage(`Failed to delete item: ${error.message}`, 'error');
                }
            });

            handleSubmit('delete-list-form', async (formData, form) => {
                const listIdRaw = formData.get('list_id');
                const listId = listIdRaw ? listIdRaw.trim() : '';
                if (!listId) {
                    setMessage('List ID is required for deletion.', 'error');
                    return;
                }

                try {
                    const response = await fetch(withToken(`/api/lists/${encodeURIComponent(listId)}`), {
                        method: 'DELETE',
                    });
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    form.reset();
                    setMessage('List deleted successfully.');
                    fetchLists();
                } catch (error) {
                    setMessage(`Failed to delete list: ${error.message}`, 'error');
                }
            });

            fetchLists();
        })();
        </script>
        """
    )

    html_parts.append("</body></html>")

    return "".join(html_parts)


def _create_sample_list(list_name: str):
    """Ensure sample data for the report exists in the database."""
    try:
        sample_list = ManagedList(
            name=list_name,
            description="Sample list created by Sample Reporter",
        )
        db.session.add(sample_list)
        db.session.flush()

        sample_items = [
            ListItem(managed_list=sample_list, key="example.com", value="Uptime OK", is_enabled=True),
            ListItem(managed_list=sample_list, key="contoso.net", value="SSL expires soon", is_enabled=True),
            ListItem(managed_list=sample_list, key="fabrikam.org", value="Disabled for maintenance", is_enabled=False),
        ]
        db.session.add_all(sample_items)
        db.session.commit()
        return sample_list, True
    except Exception:
        db.session.rollback()
        return None, False


@reporter_bp.route('/sample-report')
@token_required
def download_sample_report():
    """Generates a sample CSV report for download."""

    csv_content = "label,value\nexample.com,Uptime OK\ncontoso.net,SSL expires soon\nfabrikam.org,Disabled"
    response = Response(csv_content, mimetype='text/csv; charset=utf-8')
    response.headers['Content-Disposition'] = 'attachment; filename="sample_report.csv"'
    return response