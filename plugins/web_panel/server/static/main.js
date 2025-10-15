document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('authToken');
    if (token) {
        window.location.href = '/dashboard';
        return; 
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
                body: JSON.stringify({ password: password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Login failed.');
            }
            
            localStorage.setItem('authToken', data.token);
            
            successMessageDiv.textContent = 'Login successful! Redirecting...';
            passwordInput.value = '';

            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1000); 

        } catch (error) {
            errorMessageDiv.textContent = error.message;
        }
    });
});