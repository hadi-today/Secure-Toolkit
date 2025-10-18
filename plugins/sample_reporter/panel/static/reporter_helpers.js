(() => {
    const getToken = () => {
        const params = new URLSearchParams(window.location.search);
        return params.get('token');
    };

    const withToken = (url) => {
        const token = getToken();
        if (!token) {
            return url;
        }
        const separator = url.includes('?') ? '&' : '?';
        return `${url}${separator}token=${encodeURIComponent(token)}`;
    };

    const escapeHtml = (value) => {
        if (value === null || value === undefined) {
            return '';
        }
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    };

    const renderLists = (lists, container) => {
        if (!container) {
            return;
        }

        if (!lists.length) {
            container.innerHTML = '<p>No lists available yet.</p>';
            return;
        }

        const html = lists
            .map((list) => {
                const items = Array.isArray(list.items) ? list.items : [];
                const itemsHtml = items.length
                    ? items
                          .map((item) => {
                              const status = item.is_enabled ? 'Enabled' : 'Disabled';
                              const valueContent = item.value
                                  ? escapeHtml(item.value)
                                  : '<i>No value</i>';
                              return `
                                <li>
                                    <strong>${escapeHtml(item.key)}</strong>:
                                    ${valueContent}
                                    <span class="status">(ID ${item.id} – ${status})</span>
                                </li>
                              `;
                          })
                          .join('')
                    : '<li><i>No items</i></li>';

                const description = list.description
                    ? `<p>${escapeHtml(list.description)}</p>`
                    : '<p><i>No description</i></p>';

                return `
                    <article class="list-card">
                        <h4>${escapeHtml(list.name)} (ID ${list.id})</h4>
                        ${description}
                        <p>Total items: ${items.length}</p>
                        <ul>${itemsHtml}</ul>
                    </article>
                `;
            })
            .join('');

        container.innerHTML = html;
    };

    const fetchLists = async () => {
        const response = await fetch(withToken('/api/lists/'));
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    };

    const fetchListDetails = async (listId) => {
        const response = await fetch(withToken(`/api/lists/${listId}`));
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    };

    window.ReporterHelpers = {
        getToken,
        withToken,
        escapeHtml,
        renderLists,
        fetchLists,
        fetchListDetails,
    };
})();

