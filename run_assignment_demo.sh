#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="inventory-service"
REGISTRY_URL="http://localhost:5001"

echo "== Installing deps =="
python3 -m pip install -r requirements.txt >/dev/null

echo "== Starting registry on :5001 =="
python3 service_registry_improved.py > /tmp/registry.log 2>&1 &
REGISTRY_PID=$!

cleanup () {
  echo ""
  echo "== Cleaning up =="
  kill "${SVC1_PID:-}" >/dev/null 2>&1 || true
  kill "${SVC2_PID:-}" >/dev/null 2>&1 || true
  kill "${REGISTRY_PID:-}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

echo "== Starting 2 service instances (same service name, different ports) =="
python3 discovered_service.py "$SERVICE_NAME" 8001 "a" "$REGISTRY_URL" > /tmp/svc_a.log 2>&1 &
SVC1_PID=$!

python3 discovered_service.py "$SERVICE_NAME" 8002 "b" "$REGISTRY_URL" > /tmp/svc_b.log 2>&1 &
SVC2_PID=$!

sleep 2

echo "== Calling client 10 times (should randomly hit :8001 and :8002) =="
for i in $(seq 1 10); do
  echo ""
  echo "---- CALL $i ----"
  python3 client_random_call.py "$SERVICE_NAME" "$REGISTRY_URL"
  sleep 0.5
done

echo ""
echo "Done. Logs:"
echo "  registry: /tmp/registry.log"
echo "  svc a:    /tmp/svc_a.log"
echo "  svc b:    /tmp/svc_b.log"
