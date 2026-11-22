import socket
import webbrowser

from werkzeug.serving import make_server

from app import app


def network_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        try:
            connection.connect(("192.0.2.1", 80))
            return connection.getsockname()[0]
        except OSError:
            return "127.0.0.1"


if __name__ == "__main__":
    port = 5013
    server = make_server("0.0.0.0", port, app, threaded=True)
    url = f"http://{network_address()}:{port}"
    print(f"Open {url}. Keep this window open while you play.", flush=True)
    webbrowser.open(url)
    server.serve_forever()
