#!/usr/bin/env python3
"""
discovered_service.py

A tiny HTTP service that:
- exposes /health and /hello
- registers itself to the service registry
- sends periodic heartbeats
- deregisters on shutdown

Pure Python: uses http.server (no Flask).
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import signal
import sys
import threading
from urllib.parse import urlparse

import requests


HEARTBEAT_INTERVAL_SECONDS = 10


class ServiceState:
    def __init__(self, service_name: str, port: int, instance_id: str, registry_url: str):
        self.service_name = service_name
        self.port = port
        self.instance_id = instance_id
        self.registry_url = registry_url.rstrip("/")
        self.address = f"http://localhost:{port}"
        self._stop = threading.Event()

    def register(self) -> None:
        r = requests.post(
            f"{self.registry_url}/register",
            json={"service": self.service_name, "address": self.address},
            timeout=5,
        )
        r.raise_for_status()
        print(f"[service:{self.instance_id}] registered {self.service_name} -> {self.address}")

    def heartbeat_loop(self) -> None:
        while not self._stop.wait(HEARTBEAT_INTERVAL_SECONDS):
            try:
                r = requests.post(
                    f"{self.registry_url}/heartbeat",
                    json={"service": self.service_name, "address": self.address},
                    timeout=5,
                )
                if r.status_code == 200:
                    print(f"[service:{self.instance_id}] heartbeat ok")
                else:
                    print(f"[service:{self.instance_id}] heartbeat non-200: {r.status_code} {r.text}")
            except Exception as e:
                print(f"[service:{self.instance_id}] heartbeat error: {e}")

    def start_heartbeats(self) -> None:
        t = threading.Thread(target=self.heartbeat_loop, daemon=True)
        t.start()

    def deregister(self) -> None:
        try:
            r = requests.post(
                f"{self.registry_url}/deregister",
                json={"service": self.service_name, "address": self.address},
                timeout=5,
            )
            print(f"[service:{self.instance_id}] deregister status={r.status_code}")
        except Exception as e:
            print(f"[service:{self.instance_id}] deregister error: {e}")

    def stop(self) -> None:
        self._stop.set()


def make_handler(state: ServiceState):
    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, code: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path

            if path == "/health":
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "service": state.service_name,
                        "instance_id": state.instance_id,
                        "address": state.address,
                    },
                )
                return

            if path == "/hello":
                self._send_json(
                    200,
                    {
                        "message": f"hello from {state.service_name}",
                        "instance_id": state.instance_id,
                        "address": state.address,
                    },
                )
                return

            self._send_json(
                404,
                {
                    "error": "not_found",
                    "available_paths": ["/health", "/hello"],
                    "instance_id": state.instance_id,
                },
            )

        def log_message(self, fmt, *args):
            return

    return Handler


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 discovered_service.py <service_name> <port> <instance_id> [registry_url]")
        print("Example:")
        print("  python3 discovered_service.py inventory-service 8001 a http://localhost:5001")
        sys.exit(1)

    service_name = sys.argv[1]
    port = int(sys.argv[2])
    instance_id = sys.argv[3]
    registry_url = sys.argv[4] if len(sys.argv) >= 5 else "http://localhost:5001"

    state = ServiceState(service_name=service_name, port=port, instance_id=instance_id, registry_url=registry_url)

    state.register()
    state.start_heartbeats()

    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(state))
    print(f"[service:{instance_id}] listening on http://localhost:{port}")

    def shutdown(*_):
        print(f"\n[service:{instance_id}] shutting down...")
        state.stop()
        state.deregister()
        server.shutdown()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    server.serve_forever()


if __name__ == "__main__":
    main()
