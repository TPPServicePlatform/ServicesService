import pytest
import mongomock
from unittest.mock import patch
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from rentals_nosql import Rentals

# Run with the following command:
# pytest ServicesService/api_container/tests/test_rentals_nosql.py

# Set the TESTING environment variable
os.environ['TESTING'] = '1'
os.environ['MONGOMOCK'] = '1'

# Set a default MONGO_TEST_DB for testing
os.environ['MONGO_TEST_DB'] = 'test_db'

@pytest.fixture(scope='function')
def mongo_client():
    client = mongomock.MongoClient()
    yield client
    client.drop_database(os.getenv('MONGO_TEST_DB'))
    client.close()

@pytest.fixture(scope='function')
def rentals(mongo_client):
    return Rentals(test_client=mongo_client)

def test_insert_rental(rentals, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    rental_id = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    assert rental_id is not None

def test_search_rental(rentals, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    rental_id = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    rentals = rentals.search(client_id='test_client')
    assert rentals is not None
    rental = rentals[0]
    assert rental is not None
    assert rental['uuid'] == rental_id
    assert rental['service_id'] == 'test_service'

def test_update_rental(rentals, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    rental_id = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    rentals.update_status(rental_id, status='ACCEPTED')
    rental = rentals.search(rental_uuid=rental_id)
    print("rental: ", rental)
    assert rental is not None
    assert len(rental) == 1
    rental = rental[0]
    assert rental['status'] == 'ACCEPTED'
    assert rental['uuid'] == rental_id

def test_delete_rental(rentals, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    rental_id = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    result = rentals.delete(rental_id)
    assert result is True
    rental = rentals.search(rental_uuid=rental_id)
    assert rental is None

def test_search_by_service_id(rentals, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    rental_id = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    _ = rentals.insert(
        service_id='wrong_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    rentals = rentals.search(service_id='test_service')
    assert rentals is not None
    assert len(rentals) == 1
    rental = rentals[0]
    assert rental is not None
    assert rental['uuid'] == rental_id
    assert rental['service_id'] == 'test_service'
    assert rental['uuid'] == rental_id

def test_search_by_provider_id(rentals, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    rental_id = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    _ = rentals.insert(
        service_id='test_service',
        provider_id='wrong_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    rentals = rentals.search(provider_id='test_provider')
    assert rentals is not None
    assert len(rentals) == 1
    rental = rentals[0]
    assert rental is not None
    assert rental['uuid'] == rental_id
    assert rental['provider_id'] == 'test_provider'
    assert rental['uuid'] == rental_id

def test_search_by_client_id(rentals, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    rental_id = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    _ = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='wrong_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    rentals = rentals.search(client_id='test_client')
    assert rentals is not None
    assert len(rentals) == 1
    rental = rentals[0]
    assert rental is not None
    assert rental['uuid'] == rental_id
    assert rental['client_id'] == 'test_client'
    assert rental['uuid'] == rental_id

def test_search_by_status(rentals, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    rental_id = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    _ = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='ACCEPTED'
    )
    rentals = rentals.search(status='PENDING')
    assert rentals is not None
    assert len(rentals) == 1
    rental = rentals[0]
    assert rental is not None
    assert rental['uuid'] == rental_id
    assert rental['status'] == 'PENDING'
    assert rental['uuid'] == rental_id

def test_search_by_date_range(rentals, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    rental_id = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    _ = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-02 00:00:00',
        end_date='2023-01-03 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    rentals = rentals.search(start_date={'MIN': '2023-01-01 00:00:00', 'MAX': '2023-01-01 00:00:00'}, end_date={'MIN': '2023-01-02 00:00:00'})
    assert rentals is not None
    assert len(rentals) == 1
    rental = rentals[0]
    assert rental is not None
    assert rental['uuid'] == rental_id
    assert rental['start_date'] == '2023-01-01 00:00:00'
    assert rental['uuid'] == rental_id

def test_search_by_multiple_criteria(rentals, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    rental_id = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    _ = rentals.insert(
        service_id='wrong_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-02 00:00:00',
        end_date='2023-01-03 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    _ = rentals.insert(
        service_id='test_service',
        provider_id='wrong_provider',
        client_id='test_client',
        start_date='2023-01-02 00:00:00',
        end_date='2023-01-03 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    rentals = rentals.search(service_id='test_service', provider_id='test_provider')
    assert rentals is not None
    assert len(rentals) == 1
    rental = rentals[0]
    assert rental is not None
    assert rental['uuid'] == rental_id
    assert rental['service_id'] == 'test_service'
    assert rental['provider_id'] == 'test_provider'

def test_total_rentals(rentals, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    _ = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    _ = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-02 00:00:00',
        end_date='2023-01-03 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='ACCEPTED'
    )
    total = rentals.total_rentals(provider_id='test_provider')
    assert total == 2

def test_finished_rentals(rentals, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    _ = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-01 00:00:00',
        end_date='2023-01-02 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='FINISHED'
    )
    _ = rentals.insert(
        service_id='test_service',
        provider_id='test_provider',
        client_id='test_client',
        start_date='2023-01-02 00:00:00',
        end_date='2023-01-03 00:00:00',
        location={'latitude': 0, 'longitude': 0},
        status='PENDING'
    )
    finished = rentals.finished_rentals(provider_id='test_provider')
    assert finished == 1