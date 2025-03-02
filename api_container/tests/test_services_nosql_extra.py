import pytest
from pymongo import MongoClient
from unittest.mock import patch
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from services_nosql import Services

# Run with the following command:
# pytest ServicesService/api_container/tests/test_services_nosql_extra.py

# Set the TESTING environment variable
os.environ['TESTING'] = '1'

# Set a default MONGO_TEST_DB for testing
os.environ['MONGO_TEST_DB'] = 'test_db'

load_dotenv()

@pytest.fixture(scope='function')
def mongo_client():
    client = MongoClient()
    yield client
    client.drop_database(os.getenv('MONGO_TEST_DB'))
    client.close()

@pytest.fixture(scope='function')
def services(mongo_client):
    return Services(test_client=mongo_client, test_db=os.getenv('MONGO_TEST_DB'))


def test_search_by_location(services, mocker):
    mocker.patch('services_nosql.get_actual_time', return_value='2023-01-01 00:00:00')

    # Insert documents with different locations
    services.insert(
        service_name='Service 1',
        provider_id='provider_1',
        description='Description 1',
        category='Category 1',
        price=100,
        location={'longitude': -58.368449, 'latitude': -34.617605}, # @FIUBA
        max_distance=10
    )
    services.insert(
        service_name='Service 2',
        provider_id='provider_2',
        description='Description 2',
        category='Category 2',
        price=200,
        location={'longitude': -58.373215, 'latitude': -34.608167}, # @Plaza de Mayo
        max_distance=10
    )
    services.insert(
        service_name='Service 3',
        provider_id='provider_3',
        description='Description 3',
        category='Category 3',
        price=300,
        location={'longitude': -59.130102, 'latitude': -37.343270}, # @Tandil
        max_distance=10
    )

    # Perform a search based on a location
    results = services.search(set(), client_location={'latitude': -34.676567, 'longitude': -58.368461}) # @Avellaneda
   
    # Verify the search results
    assert len(results) == 2
    names = [result['service_name'] for result in results]
    assert 'Service 1' in names
    assert 'Service 2' in names