from wsgiref.simple_server import make_server

from .app_factory import create_app


def setup_server(host, port, password_verifier):
    """Create a WSGI server instance for the web panel."""

    app = create_app(password_verifier)
    httpd = make_server(host, port, app)
    print(f'Using standard Python WSGI server (wsgiref) on http://{host}:{port}')
    return httpd
