# Secure Toolkit v1.1


Secure Toolkit is a modular desktop suite built with Python and PyQt6 for secure key
management, encrypted document workflows, and everyday cryptography. Launch any tool
from a single hub, keep secrets protected with a master password, and extend the
experience with custom plugins.

## What’s new in v1.1

- **Dedicated plugin windows** keep each workflow focused while exposing real-time
  service status.
- **Revamped in-app copy** clarifies guidance and task flows throughout the suite.
- **At-a-glance key and notes summaries** highlight key health and version history
  before you open a module.
- **Unified launcher bootstrap** eliminates layout collisions and stabilizes startup
  across platforms.

## Core features

- **Secure core** backed by an AES-GCM vault locked by the master password.
- **Key manager** for generating, importing, and organizing RSA key pairs and trusted
  public keys.
- **File encryptor** supporting symmetric (password) and hybrid (RSA) encryption plus
  filename protection and chunked uploads.
- **Digital signature tool** to sign files and verify integrity and authenticity.
- **Secure text tool** for quick encrypt/decrypt/sign/verify cycles in a streamlined
  editor.
- **Versioned secure editor** with key-aware context and master-password access
  controls.
- **Web panel plugin** to monitor remote services, perform secure logins, and view
  dashboards.
- **Sample plugin scaffold** demonstrating how to build responsive web-powered
  extensions.

## Quick start

### Prerequisites
- Python 3.8 or later
- `pip` package manager

### Installation and launch

1. Clone the repository:
   ```bash
   git clone [your-repository-url]
   cd secure-toolkit
   ```
2. Run `launcher.py` to create a virtual environment, install dependencies, and
   launch the app:
   ```bash
   python3 launcher.py
   ```
   On Windows:
   ```bash
   python launcher.py
   ```
3. On first run, define the master password. It encrypts every sensitive item and
   cannot be recovered, so store it securely.

## Technology stack

- **Python 3** for application logic
- **PyQt6** for the desktop UI
- **cryptography** for encryption and signature primitives

## Project architecture

The launcher discovers plugins from the `plugins/` directory. Each plugin provides a
module (`plugin.py`) and a `manifest.json` that describe its entry point and metadata.
This separation keeps the core lightweight, encourages new capabilities, and simplifies
maintenance without touching the central logic in `main.py`.
