# plugins/web_panel/server_runner.py

import sys
import os
from wsgiref.simple_server import make_server
from urllib.parse import unquote_plus


runner_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(runner_dir, '..', '..'))


if project_root not in sys.path:
    sys.path.insert(0, project_root)


from plugins.web_panel.server.app_factory import create_app
from plugins.web_panel.server.web_auth import verify_password_with_hash

def run():

    if len(sys.argv) < 7:  
        print(f"Error: Expected 6 arguments, but got {len(sys.argv) - 1}")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2])
    safe_hash_from_arg = sys.argv[3]
    safe_salt_from_arg = sys.argv[4]
    iterations_from_arg = int(sys.argv[5])
    key_length_from_arg = int(sys.argv[6])

    password_hash_b64 = unquote_plus(safe_hash_from_arg)
    salt_b64 = unquote_plus(safe_salt_from_arg)
    
    def local_password_verifier(password_attempt):
        return verify_password_with_hash(
            password_attempt, 
            password_hash_b64, 
            salt_b64, 
            iterations_from_arg, 
            key_length_from_arg
        )

    app = create_app(password_verifier=local_password_verifier)
    
    print(f"Server process started. Listening on http://{host}:{port}", flush=True)
    
    httpd = make_server(host, port, app)
    httpd.serve_forever()

if __name__ == "__main__":
    run()