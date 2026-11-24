import socket
import webbrowser
from threading import Timer

from app import create_app


app = create_app()


def find_available_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    host = "127.0.0.1"
    port = find_available_port()
    Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}/")).start()

    try:
        from waitress import serve
        serve(app, host=host, port=port, threads=4)
    except ImportError:
        app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
