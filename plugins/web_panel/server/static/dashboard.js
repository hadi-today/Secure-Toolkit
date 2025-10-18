document.addEventListener('DOMContentLoaded', () => {
    const clearStoredCredentials = () => {
        try {
            localStorage.removeItem('authToken');
        } catch (storageError) {
            console.warn('Unable to clear stored auth token from localStorage:', storageError);
        }

        document.cookie =
            'authToken=; Max-Age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=Lax';
    };

    const redirectToLogin = () => {
        clearStoredCredentials();
        window.location.href = '/';
    };

    const token = localStorage.getItem('authToken');
    if (!token) {
        redirectToLogin();
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

    const buildMenu = (plugins) => {
        plugins.forEach((plugin) => {
            const listItem = document.createElement('li');
            listItem.innerHTML = `
                <a href="#" data-url="${plugin.base_path}" data-name="${plugin.display_name}">
                    <i class="fas ${plugin.icon}"></i> ${plugin.display_name}
                </a>
            `;
            pluginMenu.appendChild(listItem);
        });
    };

    const loadPlugins = async () => {
        try {
            const plugins = await window.DashboardHelpers.fetchPlugins(token);
            buildMenu(plugins);
        } catch (error) {
            console.error('Failed to fetch plugins:', error);
            if (error && error.code === 'unauthorized') {
                redirectToLogin();
                return;
            }
            pageTitle.textContent = 'Unable to load plugins';
            welcomeMessage.style.display = 'block';
            welcomeMessage.textContent = 'The plugin list could not be loaded. Please try refreshing the page.';
        }
    };

    const loadGadgets = async () => {
        try {
            const gadgets = await window.DashboardHelpers.fetchGadgets(token);
            window.DashboardHelpers.renderGadgets(
                gadgets,
                gadgetsSection,
                gadgetsGrid,
                token,
            );
        } catch (error) {
            console.error('Failed to fetch gadgets:', error);
            if (error && error.code === 'unauthorized') {
                redirectToLogin();
                return;
            }
            if (gadgetsSection) {
                gadgetsSection.classList.add('hidden');
                gadgetsSection.dataset.hasGadgets = 'false';
            }
        }
    };

    pluginMenu.addEventListener('click', (event) => {
        event.preventDefault();
        const link = event.target.closest('a');
        if (!link) {
            return;
        }

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
    });

    logoutButton.addEventListener('click', (event) => {
        event.preventDefault();
        redirectToLogin();
    });

    loadPlugins();
    loadGadgets();
});

