import requests
import random

REGISTRY_URL = 'http://localhost:5001'

def get_services():
    response = requests.get(REGISTRY_URL + '/services')
    return response.json()  # Assuming the response is a JSON list of services

if __name__ == '__main__':
    services = get_services()
    if services:
        service = random.choice(services)
        instance_id = service['instance_id']
        port = service['port']
        health_check_url = f'http://{instance_id}:{port}/health'
        health_response = requests.get(health_check_url)
        print(f'Selected instance: {instance_id}:{port}, Health: {health_response.text}')