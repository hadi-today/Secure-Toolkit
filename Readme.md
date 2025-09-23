# Secure Toolkit v1.0



A modular and secure desktop application built with Python and PyQt6 for performing various cryptographic operations. This toolkit provides a user-friendly graphical interface for managing cryptographic keys, encrypting/decrypting files, creating digital signatures, and securing text messages.

## Features

This application features a powerful plugin-based architecture, allowing for easy expansion and addition of new security tools. The current version includes:

*   **Secure Core**: The application is protected by a master password. All sensitive data, including the user's private keys, is stored in an encrypted format on disk using AES-GCM.
*   **Keyring Manager**: A comprehensive tool to generate, import, and manage personal RSA key pairs and the public keys of contacts.
*   **File Encryptor**: An advanced tool for file encryption and decryption that supports:
    *   **Symmetric Encryption**: Using a strong password (AES-256).
    *   **Asymmetric (Hybrid) Encryption**: Using RSA public keys from the keyring.
    *   **Encrypted Filenames**: The original filename is encrypted and stored within the output file to protect metadata.
    *   **File Chunking**: Ability to encrypt and split very large files into smaller, manageable parts, with integrity checks via a `manifest.json` file.
*   **Digital Signature Tool**: A standard tool to create and verify digital signatures for files, ensuring authenticity and integrity.
*   **Secure Text Tool**: A quick and easy utility to encrypt, decrypt, and manage short text snippets for secure communication over insecure channels.
*   **Internal Tools**: Includes plugins to securely change the master password.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine.

### Prerequisites

*   Python 3.8 or higher
*   pip (Python package installer)

### Installation & Running

The application is designed to be self-contained and easy to run. It uses a smart launcher that automatically creates a virtual environment and installs all necessary dependencies.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/hadi-today/Secure-Toolkit
    cd secure-toolkit
    ```

2.  **Run the launcher:**
    The `launcher.py` script handles everything. On its first run, it will:
    a. Create a local Python virtual environment in a `venv` folder.
    b. Install all required packages (like PyQt6 and cryptography) from `requirements.txt` into this environment.
    c. Launch the main application.

    To run the application, simply execute:
    ```bash
    python3 launcher.py
    ```
    or on Windows:
    ```bash
    python launcher.py
    ```

3.  **First-time Setup:**
    On the first run, the application will prompt you to create a strong master password. This password is used to encrypt your keyring and secure the entire application. **Do not forget this password, as there is no way to recover it.**

## Built With

*   **Python 3**: The core programming language.
*   **PyQt6**: For the graphical user interface.
*   **Cryptography**: A powerful library for all cryptographic primitives (AES, RSA, etc.).

## Project Architecture

The application is built on a plugin-based architecture. The `main.py` file acts as a core controller that discovers and loads plugins from the `plugins/` directory. Each plugin is a self-contained module with its own UI (`plugin.py`) and a `manifest.json` file that describes it to the core application.

This design allows for easy maintenance and the addition of new features without modifying the core codebase.
