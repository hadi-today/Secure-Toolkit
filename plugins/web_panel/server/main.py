# plugins/web_panel/server/main.py

from wsgiref.simple_server import make_server
from .app_factory import create_app

def setup_server(host, port, password_verifier):

    app = create_app(password_verifier)
    httpd = make_server(host, port, app)
    print(f"Using standard Python WSGI server (wsgiref) on http://{host}:{port}")
    return httpd
def closeEvent(self, event):
       
        print("Main window closing. Stopping all background services...")
        
        for service_name, service_data in self.background_services.items():
            if 'process' in service_data:
                print(f"Terminating service: {service_name}...")
                service_data['process'].terminate()
                service_data['process'].wait() 
                print(f"Service {service_name} terminated.")
        
        super().closeEvent(event)