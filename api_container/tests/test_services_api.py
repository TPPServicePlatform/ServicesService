import pytest
from fastapi.testclient import TestClient
import os
import sys
import mongomock

# Run with the following command:
# pytest ServicesService/api_container/tests/test_services_api.py

# Set the TESTING environment variable
os.environ['TESTING'] = '1'

# Set a default MONGO_TEST_DB for testing
os.environ['MONGO_TEST_DB'] = 'test_db'

# Add the necessary paths to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from services_api import app, no_sql_manager

@pytest.fixture(scope='module')
def test_app():
    client = TestClient(app)
    yield client

def test_get_service(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = no_sql_manager.insert(
        service_name='Test Service',
        provider_id='test_user',
        description='Test Description',
        category='Test Category',
        price=100
    )
    response = test_app.get(f"/search?uuid={service_id}")
    assert response.status_code == 200
    results = response.json()['results']
    assert len(results) == 1
    assert results[0]['service_name'] == 'Test Service'

def test_create_service(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    body = {
        "service_name": "New Service",
        "provider_id": "new_user",
        "description": "New Description",
        "category": "New Category",
        "price": 150
    }
    response = test_app.post("/create", json=body)
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_delete_service(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = no_sql_manager.insert(
        service_name='Test Service',
        provider_id='test_user',
        description='Test Description',
        category='Test Category',
        price=100
    )
    response = test_app.delete(f"/{service_id}")
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_update_service(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = no_sql_manager.insert(
        service_name='Test Service',
        provider_id='test_user',
        description='Test Description',
        category='Test Category',
        price=100
    )
    update_data = {
        'service_name': 'Updated Service',
        'description': 'Updated Description'
    }
    response = test_app.put(f"/{service_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
    updated_service = no_sql_manager.get(service_id)
    assert updated_service['service_name'] == 'Updated Service'
    assert updated_service['description'] == 'Updated Description'

def test_search_by_keywords(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    no_sql_manager.insert(
        service_name='Test Service 1',
        provider_id='test_user_1',
        description='Test Description 1',
        category='Test Category 1',
        price=100
    )
    response = test_app.get("/search?keywords=Test Service 1")
    assert response.status_code == 200
    results = response.json()['results']
    assert len(results) == 1
    assert results[0]['service_name'] == 'Test Service 1'

def test_search_by_provider_id(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    no_sql_manager.insert(
        service_name='Test Service 2',
        provider_id='test_user_2',
        description='Test Description 2',
        category='Test Category 2',
        price=200
    )
    response = test_app.get("/search?provider_id=test_user_2")
    assert response.status_code == 200
    results = response.json()['results']
    assert len(results) == 1
    assert results[0]['provider_id'] == 'test_user_2'

def test_search_by_price_range(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    no_sql_manager.insert(
        service_name='Test Service 3',
        provider_id='test_user_3',
        description='Test Description 3',
        category='Test Category 3',
        price=300
    )
    response = test_app.get("/search?min_price=250&max_price=350")
    assert response.status_code == 200
    results = response.json()['results']
    assert len(results) == 1
    assert results[0]['price'] == 300

def test_search_by_hidden_status(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    uuid = no_sql_manager.insert(
        service_name='Test Service 4',
        provider_id='test_user_4',
        description='Test Description 4',
        category='Test Category 4',
        price=400
    )
    no_sql_manager.update(uuid, {'hidden': True})
    response = test_app.get("/search?hidden=true")
    assert response.status_code == 200
    results = response.json()['results']
    assert len(results) == 1
    assert results[0]['service_name'] == 'Test Service 4'

def test_search_by_uuid(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = no_sql_manager.insert(
        service_name='Test Service 5',
        provider_id='test_user_5',
        description='Test Description 5',
        category='Test Category 5',
        price=500
    )
    response = test_app.get(f"/search?uuid={service_id}")
    assert response.status_code == 200
    results = response.json()['results']
    assert len(results) == 1
    assert results[0]['service_name'] == 'Test Service 5'

def test_search_no_parameters(test_app):
    response = test_app.get("/search")
    assert response.status_code == 400
    assert response.json()['detail'] == "No search parameters provided"

def test_search_no_results(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    no_sql_manager.insert(
        service_name='Test Service 6',
        provider_id='test_user_6',
        description='Test Description 6',
        category='Test Category 6',
        price=600
    )
    response = test_app.get("/search?keywords=Nonexistent Service")
    assert response.status_code == 404
    assert response.json()['detail'] == "No results found"