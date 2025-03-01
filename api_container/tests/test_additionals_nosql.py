import pytest
import mongomock
from unittest.mock import patch
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from additionals_nosql import Additionals

# Run with the following command:
# pytest ServicesService/api_container/tests/test_additionals_nosql.py

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
def additionals(mongo_client):
    return Additionals(test_client=mongo_client)

def test_insert_additional(additionals, mocker):
    mocker.patch('additionals_nosql.get_actual_time', return_value='2023-01-01 00:00:00')
    additional_id = additionals.insert(
        name='Test Additional',
        provider_id='test_user',
        description='Test Description',
        price=100
    )
    assert additional_id is not None

def test_get_additional(additionals, mocker):
    mocker.patch('additionals_nosql.get_actual_time', return_value='2023-01-01 00:00:00')
    additional_id = additionals.insert(
        name='Test Additional',
        provider_id='test_user',
        description='Test Description',
        price=100
    )
    additional = additionals.get(additional_id)
    assert additional is not None
    assert additional['additional_name'] == 'Test Additional'

def test_update_additional(additionals, mocker):
    mocker.patch('additionals_nosql.get_actual_time', return_value='2023-01-01 00:00:00')
    additional_id = additionals.insert(
        name='Test Additional',
        provider_id='test_user',
        description='Test Description',
        price=100
    )
    additionals.update(
        additional_id,
        { 'price': 200 }
    )
    additional = additionals.get(additional_id)
    assert additional is not None
    assert additional['price'] == 200
    assert additional['additional_name'] == 'Test Additional'

def test_delete_additional(additionals, mocker):
    mocker.patch('additionals_nosql.get_actual_time', return_value='2023-01-01 00:00:00')
    additional_id = additionals.insert(
        name='Test Additional',
        provider_id='test_user',
        description='Test Description',
        price=100
    )
    result = additionals.delete(additional_id)
    assert result is True
    additionals = additionals.get(additional_id)
    assert additionals is None

def test_get_additional_not_found(additionals):
    additional = additionals.get('non_existent_id')
    assert additional is None

def test_delete_additional_not_found(additionals):
    result = additionals.delete('non_existent_id')
    assert result is False

def test_get_additional_by_provider(additionals, mocker):
    mocker.patch('additionals_nosql.get_actual_time', return_value='2023-01-01 00:00:00')
    additional_id = additionals.insert(
        name='Test Additional',
        provider_id='test_user',
        description='Test Description',
        price=100
    )
    wrong_additional_id = additionals.insert(
        name='Test Additional',
        provider_id='wrong_user',
        description='Test Description',
        price=100
    )
    additionals = additionals.get_by_provider('test_user')
    assert additionals is not None
    assert len(additionals) == 1
    additional = additionals[0]
    assert additional is not None
    assert additional['uuid'] == additional_id


