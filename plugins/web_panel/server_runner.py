import os
import sys
from urllib.parse import unquote_plus
from wsgiref.simple_server import make_server


RUNNER_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(RUNNER_DIR, '..', '..'))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from plugins.web_panel.server.app_factory import create_app  # noqa: E402
from plugins.web_panel.server.web_auth import verify_password_with_hash  # noqa: E402


def _build_password_verifier(password_hash_b64, salt_b64, iterations, key_length):
    def _verifier(password_attempt):
        return verify_password_with_hash(
            password_attempt,
            password_hash_b64,
            salt_b64,
            iterations,
            key_length,
        )

    return _verifier


def run():
    if len(sys.argv) < 7:
        print(f'Error: Expected 6 arguments, received {len(sys.argv) - 1}')
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    password_hash_b64 = unquote_plus(sys.argv[3])
    salt_b64 = unquote_plus(sys.argv[4])
    iterations = int(sys.argv[5])
    key_length = int(sys.argv[6])

    password_verifier = _build_password_verifier(
        password_hash_b64,
        salt_b64,
        iterations,
        key_length,
    )

    app = create_app(password_verifier=password_verifier)
    print(f'Server process started. Listening on http://{host}:{port}', flush=True)
    httpd = make_server(host, port, app)
    httpd.serve_forever()


if __name__ == '__main__':
    run()

