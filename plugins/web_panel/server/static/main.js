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

    const redirectToDashboard = () => {
        window.location.href = '/dashboard';
    };

    const verifyStoredToken = async (token) => {
        try {
            const response = await fetch('/api/core/registered_plugins', {
                headers: { Authorization: `Bearer ${token}` },
                cache: 'no-store',
            });

            if (response.status === 401) {
                clearStoredCredentials();
                return;
            }

            if (!response.ok) {
                throw new Error(`Token verification failed with status ${response.status}`);
            }

            redirectToDashboard();
        } catch (error) {
            console.warn('Unable to verify stored auth token:', error);
        }
    };

    const token = localStorage.getItem('authToken');
    if (token) {
        verifyStoredToken(token);
    }

    const loginForm = document.getElementById('login-form');
    const passwordInput = document.getElementById('password');
    const errorMessageDiv = document.getElementById('error-message');
    const successMessageDiv = document.getElementById('success-message');

    loginForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const password = passwordInput.value;
        errorMessageDiv.textContent = '';
        successMessageDiv.textContent = '';

        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Login failed.');
            }

            localStorage.setItem('authToken', data.token);

            successMessageDiv.textContent = 'Login successful! Redirecting...';
            passwordInput.value = '';

            setTimeout(() => {
                redirectToDashboard();
            }, 1000);
        } catch (error) {
            errorMessageDiv.textContent = error.message;
            if (error.message === 'Unauthorized' || error.message === 'Invalid credentials') {
                clearStoredCredentials();
            }
        }
    });
});

