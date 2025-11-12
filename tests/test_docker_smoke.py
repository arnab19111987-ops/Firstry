import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from firsttry.docker_smoke import build_compose_cmds, check_health


def test_build_compose_cmds_default():
    up, down = build_compose_cmds()
    assert up == "docker compose -f docker-compose.yml up -d"
    assert down == "docker compose -f docker-compose.yml down"


def test_check_health_with_local_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/healthz":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, fmt, *args):
            # silence stderr noise in tests
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    host, port = server.server_address

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        good_url = f"http://{host}:{port}/healthz"
        assert check_health(url=good_url, timeout=2.0) is True

        bad_url = f"http://{host}:{port}/nope"
        assert check_health(url=bad_url, timeout=1.0) is False
    finally:
        server.shutdown()
        thread.join()
