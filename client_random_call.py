#!/usr/bin/env python3
"""
client_random_call.py

1) Discover instances from the registry: GET /discover/<service>
2) Choose one randomly
3) Call that instance's /hello endpoint
"""

import random
import sys
import requests


def discover_instances(registry_url: str, service_name: str):
    r = requests.get(f"{registry_url.rstrip('/')}/discover/{service_name}", timeout=5)
    if r.status_code != 200:
        raise RuntimeError(f"Discovery failed: {r.status_code} {r.text}")
    data = r.json()
    return data.get("instances", [])


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 client_random_call.py <service_name> [registry_url]")
        print("Example: python3 client_random_call.py inventory-service http://localhost:5001")
        sys.exit(1)

    service_name = sys.argv[1]
    registry_url = sys.argv[2] if len(sys.argv) >= 3 else "http://localhost:5001"

    instances = discover_instances(registry_url, service_name)
    if not instances:
        print(f"No instances found for service '{service_name}'.")
        sys.exit(2)

    choice = random.choice(instances)
    address = choice["address"].rstrip("/")

    r = requests.get(f"{address}/hello", timeout=5)
    r.raise_for_status()

    print(f"DISCOVERED {len(instances)} instance(s) for {service_name}")
    print(f"RANDOMLY SELECTED: {address}")
    print(f"RESPONSE: {r.json()}")


if __name__ == "__main__":
    main()