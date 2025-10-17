(() => {
    const withToken = (token, url) => {
        const separator = url.includes('?') ? '&' : '?';
        return `${url}${separator}token=${encodeURIComponent(token)}`;
    };

    const buildDownloadUrl = (originalUrl, token) => {
        try {
            const parsed = new URL(originalUrl, window.location.origin);

            if (parsed.origin === window.location.origin) {
                parsed.searchParams.set('token', token);

                if (originalUrl.startsWith('http://') || originalUrl.startsWith('https://')) {
                    return parsed.toString();
                }

                return `${parsed.pathname}${parsed.search}${parsed.hash}`;
            }

            return originalUrl;
        } catch (error) {
            console.warn('Failed to build download URL for gadget', error);
            return originalUrl;
        }
    };

    const fetchPlugins = async (token) => {
        const response = await fetch('/api/core/registered_plugins', {
            headers: { Authorization: `Bearer ${token}` },
        });

        if (response.status === 401) {
            const error = new Error('Unauthorized');
            error.code = 'unauthorized';
            throw error;
        }

        return response.json();
    };

    const fetchGadgets = async (token) => {
        const response = await fetch('/api/core/gadgets', {
            headers: { Authorization: `Bearer ${token}` },
        });

        if (response.status === 401) {
            const error = new Error('Unauthorized');
            error.code = 'unauthorized';
            throw error;
        }

        return response.json();
    };

    const initializeKeyringGadgets = (contentRoot, token) => {
        if (!contentRoot) {
            return;
        }

        const widgets = contentRoot.querySelectorAll('[data-gadget-type="keyring-summary"]');
        widgets.forEach((widget) => {
            if (widget.dataset.initialized === 'true') {
                return;
            }

            widget.dataset.initialized = 'true';

            const endpoint = widget.dataset.endpoint;
            const statusEl = widget.querySelector('[data-role="status"]');
            const countsEl = widget.querySelector('.keyring-gadget__counts');
            const myEl = widget.querySelector('[data-role="my-count"]');
            const contactEl = widget.querySelector('[data-role="contact-count"]');
            const totalEl = widget.querySelector('[data-role="total-count"]');
            const linkEl = widget.querySelector('.keyring-gadget__link');

            if (!endpoint) {
                if (statusEl) {
                    statusEl.textContent = 'Missing data endpoint.';
                }
                return;
            }

            if (linkEl && linkEl.getAttribute('href')) {
                linkEl.href = withToken(token, linkEl.getAttribute('href'));
            }

            const refresh = async () => {
                try {
                    if (statusEl) {
                        statusEl.textContent = 'Loading key totals…';
                    }

                    const response = await fetch(withToken(token, endpoint), {
                        headers: { Authorization: `Bearer ${token}` },
                    });

                    if (response.status === 401) {
                        const error = new Error('unauthorized');
                        error.code = 'unauthorized';
                        throw error;
                    }

                    let payload;
                    try {
                        payload = await response.json();
                    } catch (parseError) {
                        payload = {};
                    }

                    if (!response.ok) {
                        const message =
                            payload.error ||
                            (response.status === 503
                                ? 'Keyring locked or unavailable.'
                                : 'Unable to load key totals.');
                        const error = new Error(message);
                        error.code = response.status === 503 ? 'locked' : 'error';
                        throw error;
                    }

                    if (myEl) {
                        myEl.textContent = payload.my_public_keys ?? '0';
                    }
                    if (contactEl) {
                        contactEl.textContent = payload.contact_public_keys ?? '0';
                    }
                    if (totalEl) {
                        const total = payload.total_public_keys;
                        totalEl.textContent =
                            total !== undefined
                                ? total
                                : (payload.my_public_keys || 0) + (payload.contact_public_keys || 0);
                    }
                    if (countsEl) {
                        countsEl.hidden = false;
                    }
                    if (statusEl) {
                        statusEl.textContent = 'Key totals updated.';
                    }
                } catch (error) {
                    if (statusEl) {
                        if (error.message === 'unauthorized' || error.code === 'unauthorized') {
                            statusEl.textContent = 'Sign in again to view key totals.';
                        } else if (error.code === 'locked') {
                            statusEl.textContent = error.message;
                        } else {
                            statusEl.textContent = error.message || 'Keyring locked or unavailable.';
                        }
                    }
                }
            };

            refresh();
        });
    };

    const renderGadgets = (gadgets, gadgetsSection, gadgetsGrid, token) => {
        if (!gadgetsSection || !gadgetsGrid) {
            return;
        }

        if (!Array.isArray(gadgets) || gadgets.length === 0) {
            gadgetsSection.classList.add('hidden');
            gadgetsSection.dataset.hasGadgets = 'false';
            return;
        }

        gadgetsGrid.innerHTML = '';

        gadgets.forEach((gadget) => {
            const card = document.createElement('article');
            card.className = 'gadget-card';

            const title = document.createElement('h3');
            title.textContent = gadget.title;
            card.appendChild(title);

            if (gadget.description) {
                const description = document.createElement('p');
                description.textContent = gadget.description;
                card.appendChild(description);
            }

            const content = document.createElement('div');
            content.className = 'gadget-content';
            content.innerHTML = gadget.content_html;
            card.appendChild(content);

            initializeKeyringGadgets(content, token);

            if (gadget.download && gadget.download.url) {
                const downloadWrapper = document.createElement('div');
                downloadWrapper.className = 'gadget-download';

                const link = document.createElement('a');
                link.href = buildDownloadUrl(gadget.download.url, token);
                link.textContent = gadget.download.label || 'Download';
                link.target = '_blank';
                link.rel = 'noopener';

                const icon = document.createElement('i');
                icon.className = 'fas fa-download';
                link.prepend(icon);

                downloadWrapper.appendChild(link);
                card.appendChild(downloadWrapper);
            }

            gadgetsGrid.appendChild(card);
        });

        gadgetsSection.classList.remove('hidden');
        gadgetsSection.dataset.hasGadgets = 'true';
    };

    window.DashboardHelpers = {
        withToken,
        buildDownloadUrl,
        fetchPlugins,
        fetchGadgets,
        renderGadgets,
    };
})();
