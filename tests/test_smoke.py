import subprocess
import time
import socket
import requests
import os


def _find_free_port():
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_registry_and_discovery_smoke():
    registry_proc = subprocess.Popen(["python3", "service_registry_improved.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # wait for registry to be up
        registry_url = "http://localhost:5001"
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                r = requests.get(f"{registry_url}/health", timeout=1)
                if r.status_code == 200:
                    break
            except Exception:
                time.sleep(0.2)
        else:
            raise RuntimeError("Registry did not start in time")

        port = _find_free_port()
        svc_proc = subprocess.Popen(["python3", "discovered_service.py", "test-service", str(port), "t1", registry_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            # wait for service to register
            deadline = time.time() + 10
            while time.time() < deadline:
                try:
                    r = requests.get(f"{registry_url}/discover/test-service", timeout=1)
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("instances"):
                            addresses = [i.get("address", "") for i in data.get("instances", [])]
                            if any(f":{port}" in a for a in addresses):
                                return
                    time.sleep(0.2)
                except Exception:
                    time.sleep(0.2)
            raise AssertionError("Service did not register and appear in discovery in time")
        finally:
            svc_proc.terminate()
            svc_proc.wait(timeout=5)
    finally:
        registry_proc.terminate()
        registry_proc.wait(timeout=5)
