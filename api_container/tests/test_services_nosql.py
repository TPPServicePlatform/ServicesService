import pytest
import mongomock
from unittest.mock import patch
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from services_nosql import Services

# Load environment variables from .env file
load_dotenv()

# Run with the following command:
# pytest ServicesService/api_container/tests/test_services_nosql.py

# Set the TESTING environment variable
os.environ['TESTING'] = '1'

# Set a default MONGO_TEST_DB for testing
os.environ['MONGO_TEST_DB'] = 'test_db'

@pytest.fixture(scope='function')
def mongo_client():
    client = mongomock.MongoClient()
    yield client
    client.drop_database(os.getenv('MONGO_TEST_DB'))
    client.close()

@pytest.fixture(scope='function')
def services(mongo_client):
    return Services(test_client=mongo_client)

def test_insert_service(services, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services.insert(
        service_name='Test Service',
        provider_id='test_user',
        description='Test Description',
        category='Test Category',
        price=100
    )
    assert service_id is not None

def test_get_service(services, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services.insert(
        service_name='Test Service',
        provider_id='test_user',
        description='Test Description',
        category='Test Category',
        price=100
    )
    service = services.get(service_id)
    assert service is not None
    assert service['service_name'] == 'Test Service'
    assert service['provider_id'] == 'test_user'

def test_delete_service(services, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services.insert(
        service_name='Test Service',
        provider_id='test_user',
        description='Test Description',
        category='Test Category',
        price=100
    )
    result = services.delete(service_id)
    assert result is True
    service = services.get(service_id)
    assert service is None

def test_update_service(services, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services.insert(
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
    result = services.update(service_id, update_data)
    assert result is True
    service = services.get(service_id)
    assert service['service_name'] == 'Updated Service'
    assert service['description'] == 'Updated Description'
    assert service['provider_id'] == 'test_user'

def test_search_by_keywords(services, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    services.insert(
        service_name='Test Service 1',
        provider_id='test_user_1',
        description='Test Description 1',
        category='Test Category 1',
        price=100
    )
    services.insert(
        service_name='Test Service 2',
        provider_id='test_user_2',
        description='Test Description 2',
        category='Test Category 2',
        price=200
    )
    results = services.search(keywords=['Test Service 1'], provider_id=None, min_price=None, max_price=None, hidden=False)
    assert len(results) == 1
    assert results[0]['service_name'] == 'Test Service 1'

def test_search_by_provider_id(services, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    services.insert(
        service_name='Test Service 1',
        provider_id='test_user_1',
        description='Test Description 1',
        category='Test Category 1',
        price=100
    )
    services.insert(
        service_name='Test Service 2',
        provider_id='test_user_2',
        description='Test Description 2',
        category='Test Category 2',
        price=200
    )
    results = services.search(keywords=None, provider_id='test_user_1', min_price=None, max_price=None, hidden=False)
    assert len(results) == 1
    assert results[0]['provider_id'] == 'test_user_1'
 
def test_search_by_price_range(services, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    services.insert(
        service_name='Test Service 1',
        provider_id='test_user_1',
        description='Test Description 1',
        category='Test Category 1',
        price=100
    )
    services.insert(
        service_name='Test Service 2',
        provider_id='test_user_2',
        description='Test Description 2',
        category='Test Category 2',
        price=200
    )
    results = services.search(keywords=[], provider_id=None, min_price=150, max_price=250, hidden=False)
    assert len(results) == 1
    assert results[0]['price'] == 200

def test_search_by_hidden_status(services, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    uuid = services.insert(
        service_name='Test Service 1',
        provider_id='test_user_1',
        description='Test Description 1',
        category='Test Category 1',
        price=100,
    )
    assert uuid is not None
    services.update(uuid, {'hidden': True})
    services.insert(
        service_name='Test Service 2',
        provider_id='test_user_2',
        description='Test Description 2',
        category='Test Category 2',
        price=200,
    )
    results = services.search(keywords=[], provider_id=None, min_price=None, max_price=None, hidden=False)
    assert len(results) == 1
    assert results[0]['service_name'] == 'Test Service 2'