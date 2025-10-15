document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('authToken');
    if (!token) {
        window.location.href = '/'; // اگر توکن وجود ندارد، به صفحه لاگین برگرد
        return;
    }

    const pluginMenu = document.getElementById('plugin-menu');
    const pageTitle = document.getElementById('page-title');
    const contentFrame = document.getElementById('content-frame');
    const welcomeMessage = document.getElementById('welcome-message');
    const logoutButton = document.getElementById('logout-button');
    const gadgetsSection = document.getElementById('gadgets-section');
    const gadgetsGrid = document.getElementById('gadgets-grid');

    if (gadgetsSection) {
        gadgetsSection.dataset.hasGadgets = 'false';
    }

    // تابع برای دریافت لیست پلاگین ها از API
    async function fetchAndBuildMenu() {
        try {
            const response = await fetch('/api/core/registered_plugins', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.status === 401) throw new Error('Unauthorized');
            const plugins = await response.json();

            // ساخت آیتم های منو
            plugins.forEach(plugin => {
                const li = document.createElement('li');
                li.innerHTML = `<a href="#" data-url="${plugin.base_path}" data-name="${plugin.display_name}">
                                    <i class="fas ${plugin.icon}"></i> ${plugin.display_name}
                                </a>`;
                pluginMenu.appendChild(li);
            });
        } catch (error) {
            console.error('Failed to fetch plugins:', error);
            window.location.href = '/'; // در صورت خطا، به صفحه لاگین برگرد
        }
    }

    async function fetchAndRenderGadgets() {
        if (!gadgetsSection || !gadgetsGrid) {
            return;
        }

        try {
            const response = await fetch('/api/core/gadgets', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.status === 401) {
                throw new Error('Unauthorized');
            }

            const gadgets = await response.json();

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

                if (gadget.download && gadget.download.url) {
                    const downloadWrapper = document.createElement('div');
                    downloadWrapper.className = 'gadget-download';

                    const link = document.createElement('a');
                    link.href = buildDownloadUrl(gadget.download.url);
                    link.href = gadget.download.url;
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
        } catch (error) {
            console.error('Failed to fetch gadgets:', error);
            gadgetsSection.classList.add('hidden');
            gadgetsSection.dataset.hasGadgets = 'false';
        }
    }

    // Event listener برای کلیک روی آیتم های منو
    pluginMenu.addEventListener('click', (event) => {
        event.preventDefault();
        const link = event.target.closest('a');
        if (link) {
            if (link.dataset.dashboard) {
                pageTitle.textContent = 'Welcome';
                welcomeMessage.style.display = 'block';
                contentFrame.style.display = 'none';
                contentFrame.src = 'about:blank';
                if (gadgetsSection && gadgetsSection.dataset.hasGadgets === 'true') {
                    gadgetsSection.classList.remove('hidden');
                }
                return;
            }

            const url = link.dataset.url;
            const name = link.dataset.name;

            pageTitle.textContent = name;
            welcomeMessage.style.display = 'none';
            contentFrame.style.display = 'block';
            if (gadgetsSection) {
                gadgetsSection.classList.add('hidden');
            }
            const tokenParam = encodeURIComponent(token);
            const separator = url.includes('?') ? '&' : '?';
            contentFrame.src = `${url}${separator}token=${tokenParam}`;
        }
    });

    // Event listener برای دکمه خروج
    logoutButton.addEventListener('click', (event) => {
        event.preventDefault();
        localStorage.removeItem('authToken');
        document.cookie = 'authToken=; Max-Age=0; path=/';
        window.location.href = '/';
    });

    fetchAndBuildMenu();
    fetchAndRenderGadgets();

    function buildDownloadUrl(originalUrl) {
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
    }
});