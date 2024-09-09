import pytest
from fastapi.testclient import TestClient
import os
import sys

# Run with the following command:
# pytest ServicesService/api_container/tests/test_services_api.py

# Set the TESTING environment variable
os.environ['TESTING'] = '1'

# Set a default DATABASE_URL for testing
os.environ['DATABASE_URL'] = 'sqlite:///test.db'

# Add the necessary paths to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))

from services_api import app, services_manager


client = TestClient(app)

@pytest.fixture(scope='module', autouse=True)
def setup_database():
    # Setup the database before running tests
    services_manager.create_table()
    yield
    # Teardown the database after running tests
    services_manager.engine.dispose()

def test_create_service():
    response = client.post("/create", json={
        "service_name": "Test Service",
        "provider_username": "test_user",
        "category": "Test Category",
        "price": "100.00"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "service_id" in response.json()

def test_get_service():
    # First, create a service
    create_response = client.post("/create", json={
        "service_name": "Test Service",
        "provider_username": "test_user",
        "category": "Test Category",
        "price": "100.00"
    })
    service_id = create_response.json()["service_id"]

    # Now, get the service
    response = client.get(f"/{service_id}")
    assert response.status_code == 200
    service = response.json()
    assert service["service_name"] == "Test Service"
    assert service["provider_username"] == "test_user"

def test_update_service():
    # First, create a service
    create_response = client.post("/create", json={
        "service_name": "Test Service",
        "provider_username": "test_user",
        "category": "Test Category",
        "price": "100.00"
    })
    service_id = create_response.json()["service_id"]

    # Now, update the service
    response = client.put(f"/{service_id}", json={
        "service_name": "Updated Service",
        "description": "Updated Description"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify the update
    get_response = client.get(f"/{service_id}")
    service = get_response.json()
    assert service["service_name"] == "Updated Service"
    assert service["description"] == "Updated Description"

def test_delete_service():
    # First, create a service
    create_response = client.post("/create", json={
        "service_name": "Test Service",
        "provider_username": "test_user",
        "category": "Test Category",
        "price": "100.00"
    })
    service_id = create_response.json()["service_id"]

    # Now, delete the service
    response = client.delete(f"/{service_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify the deletion
    get_response = client.get(f"/{service_id}")
    assert get_response.status_code == 404
    assert get_response.json()["detail"] == f"Service with uuid '{service_id}' not found"