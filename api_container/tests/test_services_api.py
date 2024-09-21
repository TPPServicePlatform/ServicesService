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
from services_api import app, services_manager, ratings_manager

@pytest.fixture(scope='module')
def test_app():
    client = TestClient(app)
    yield client

def test_get_service(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services_manager.insert(
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
    service_id = services_manager.insert(
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
    service_id = services_manager.insert(
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
    updated_service = services_manager.get(service_id)
    assert updated_service['service_name'] == 'Updated Service'
    assert updated_service['description'] == 'Updated Description'

def test_search_by_keywords(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    services_manager.insert(
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
    services_manager.insert(
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
    services_manager.insert(
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
    uuid = services_manager.insert(
        service_name='Test Service 4',
        provider_id='test_user_4',
        description='Test Description 4',
        category='Test Category 4',
        price=400
    )
    services_manager.update(uuid, {'hidden': True})
    response = test_app.get("/search?hidden=true")
    assert response.status_code == 200
    results = response.json()['results']
    assert len(results) == 1
    assert results[0]['service_name'] == 'Test Service 4'

def test_search_by_uuid(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services_manager.insert(
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
    services_manager.insert(
        service_name='Test Service 6',
        provider_id='test_user_6',
        description='Test Description 6',
        category='Test Category 6',
        price=600
    )
    response = test_app.get("/search?keywords=Nonexistent Service")
    assert response.status_code == 404
    assert response.json()['detail'] == "No results found"

def test_create_review(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services_manager.insert(
        service_name='Test Service 7',
        provider_id='test_user_7',
        description='Test Description 7',
        category='Test Category 7',
        price=700
    )
    response = test_app.put(f"/{service_id}/reviews", json={
        'rating': 5,
        'comment': 'Test Comment',
        'user_uuid': 'test_user'
    })
    print(response.json())
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
    assert 'review_id' in response.json()

def test_update_review(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services_manager.insert(
        service_name='Test Service 8',
        provider_id='test_user_8',
        description='Test Description 8',
        category='Test Category 8',
        price=800
    )
    review_id = ratings_manager.insert(service_id, 5, 'Test Comment', 'test_user')
    response = test_app.put(f"/{service_id}/reviews", json={
        'rating': 4,
        'comment': 'Updated Comment',
        'user_uuid': 'test_user'
    })
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
    updated_review = ratings_manager.get(service_id, 'test_user')
    assert updated_review['rating'] == 4
    assert updated_review['comment'] == 'Updated Comment'

def test_create_review_no_service(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = 'nonexistent_service'
    response = test_app.put(f"/{service_id}/reviews", json={
        'rating': 4,
        'comment': 'Updated Comment',
        'user_uuid': 'test_user'
    })
    assert response.status_code == 404
    assert response.json()['detail'] == "Service not found"

def test_delete_review(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services_manager.insert(
        service_name='Test Service 9',
        provider_id='test_user_9',
        description='Test Description 9',
        category='Test Category 9',
        price=900
    )
    _ = ratings_manager.insert(service_id, 5, 'Test Comment', 'test_user')
    response = test_app.delete(f"/{service_id}/reviews", params={'user_uuid': 'test_user'})
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_delete_review_no_service(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = 'nonexistent_service'
    response = test_app.delete(f"/{service_id}/reviews", params={'user_uuid': 'test_user'})
    assert response.status_code == 404
    assert response.json()['detail'] == "Review not found"

def test_get_all_reviews(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services_manager.insert(
        service_name='Test Service 10',
        provider_id='test_user_10',
        description='Test Description 10',
        category='Test Category 10',
        price=1000
    )
    _ = ratings_manager.insert(service_id, 5, 'Test Comment 1', 'test_user_1')
    _ = ratings_manager.insert(service_id, 4, 'Test Comment 2', 'test_user_2')
    response = test_app.get(f"/{service_id}/reviews")
    assert response.status_code == 200
    results = response.json()['reviews']
    assert len(results) == 2
    assert results[0]['comment'] == 'Test Comment 1'
    assert results[1]['comment'] == 'Test Comment 2'

def test_create_review_updates_sum_rating_and_num_ratings(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services_manager.insert(
        service_name='Test Service 12',
        provider_id='test_user_12',
        description='Test Description 12',
        category='Test Category 12',
        price=1200
    )
    response = test_app.put(f"/{service_id}/reviews", json={
        'rating': 5,
        'comment': 'Test Comment',
        'user_uuid': 'test_user'
    })
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
    service = services_manager.get(service_id)
    assert service['sum_rating'] == 5
    assert service['num_ratings'] == 1

def test_create_multiple_reviews_updates_sum_rating_and_num_ratings(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services_manager.insert(
        service_name='Test Service 14',
        provider_id='test_user_14',
        description='Test Description 14',
        category='Test Category 14',
        price=1400
    )
    response1 = test_app.put(f"/{service_id}/reviews", json={
        'rating': 5,
        'comment': 'Test Comment 1',
        'user_uuid': 'test_user_1'
    })
    assert response1.status_code == 200
    assert response1.json()['status'] == 'ok'
    
    response2 = test_app.put(f"/{service_id}/reviews", json={
        'rating': 3,
        'comment': 'Test Comment 2',
        'user_uuid': 'test_user_2'
    })
    assert response2.status_code == 200
    assert response2.json()['status'] == 'ok'
    
    service = services_manager.get(service_id)
    assert service['sum_rating'] == 8
    assert service['num_ratings'] == 2

def test_delete_review_updates_sum_rating_and_num_ratings(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services_manager.insert(
        service_name='Test Service 16',
        provider_id='test_user_16',
        description='Test Description 16',
        category='Test Category 16',
        price=1600
    )
    review_id = ratings_manager.insert(service_id, 5, 'Test Comment', 'test_user')
    services_manager.update_rating(service_id, 5, True)
    
    response = test_app.delete(f"/{service_id}/reviews", params={'user_uuid': 'test_user'})
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
    
    service = services_manager.get(service_id)
    assert service['sum_rating'] == 0
    assert service['num_ratings'] == 0

def test_delete_nonexistent_review(test_app, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services_manager.insert(
        service_name='Test Service 17',
        provider_id='test_user_17',
        description='Test Description 17',
        category='Test Category 17',
        price=1700
    )
    
    response = test_app.delete(f"/{service_id}/reviews", params={'user_uuid': 'nonexistent_user'})
    assert response.status_code == 404
    assert response.json()['detail'] == "Review not found"