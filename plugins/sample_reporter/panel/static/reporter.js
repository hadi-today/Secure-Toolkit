document.addEventListener('DOMContentLoaded', () => {
    const messageBox = document.getElementById('api-message');
    const listsContainer = document.getElementById('lists-container');
    const refreshButton = document.getElementById('refresh-lists');

    const setMessage = (text, type = 'info') => {
        if (!messageBox) {
            return;
        }
        messageBox.textContent = text;
        messageBox.style.color = type === 'error' ? '#b91c1c' : '#047857';
    };

    const loadLists = async () => {
        if (!listsContainer) {
            return;
        }
        listsContainer.innerHTML = '<p>Loading lists…</p>';
        try {
            const lists = await window.ReporterHelpers.fetchLists();
            const detailed = await Promise.all(
                lists.map(async (list) => {
                    try {
                        return await window.ReporterHelpers.fetchListDetails(list.id);
                    } catch (error) {
                        return { ...list, items: [] };
                    }
                })
            );
            window.ReporterHelpers.renderLists(detailed, listsContainer);
            setMessage('Lists refreshed successfully.');
        } catch (error) {
            listsContainer.innerHTML =
                '<p style="color:#b91c1c;">Could not load lists.</p>';
            setMessage(`Failed to load lists: ${error.message}`, 'error');
        }
    };

    if (refreshButton) {
        refreshButton.addEventListener('click', (event) => {
            event.preventDefault();
            loadLists();
        });
    }

    window.ReporterForms.init({ setMessage, refreshLists: loadLists });
    loadLists();
});

