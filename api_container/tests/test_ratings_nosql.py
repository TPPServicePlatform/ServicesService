import pytest
import mongomock
from unittest.mock import patch
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from ratings_nosql import Ratings

# Run with the following command:
# pytest ServicesService/api_container/tests/test_ratings_nosql.py

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
def ratings(mongo_client):
    return Ratings(test_client=mongo_client)

def test_insert_rating(ratings, mocker):
    mocker.patch('ratings_nosql.get_actual_time', return_value='2023-01-01 00:00:00')
    rating_id = ratings.insert(
        service_uuid='service-uuid',
        rating=5,
        comment='Great service!',
        user_uuid='user-uuid'
    )
    assert rating_id is not None

def test_get_rating(ratings, mocker):
    mocker.patch('ratings_nosql.get_actual_time', return_value='2023-01-01 00:00:00')
    _ = ratings.insert(
        service_uuid='service-uuid',
        rating=5,
        comment='Great service!',
        user_uuid='user-uuid'
    )
    rating = ratings.get('service-uuid', 'user-uuid')
    assert rating is not None
    assert rating['service_uuid'] == 'service-uuid'
    assert rating['user_uuid'] == 'user-uuid'

def test_get_all_ratings(ratings, mocker):
    mocker.patch('ratings_nosql.get_actual_time', return_value='2023-01-01 00:00:00')
    ratings.insert(
        service_uuid='service-uuid',
        rating=5,
        comment='Great service!',
        user_uuid='user-uuid'
    )
    ratings.insert(
        service_uuid='service-uuid',
        rating=4,
        comment='Good service!',
        user_uuid='user-uuid-2'
    )
    all_ratings = ratings.get_all('service-uuid')
    assert all_ratings is not None
    assert len(all_ratings) == 2

def test_delete_rating(ratings, mocker):
    mocker.patch('ratings_nosql.get_actual_time', return_value='2023-01-01 00:00:00')
    rating_id = ratings.insert(
        service_uuid='service-uuid',
        rating=5,
        comment='Great service!',
        user_uuid='user-uuid'
    )
    result = ratings.delete(rating_id)
    assert result is True
    rating = ratings.get('service-uuid', 'user-uuid')
    assert rating is None

def test_update_rating(ratings, mocker):
    mocker.patch('ratings_nosql.get_actual_time', return_value='2023-01-01 00:00:00')
    rating_id = ratings.insert(
        service_uuid='service-uuid',
        rating=5,
        comment='Great service!',
        user_uuid='user-uuid'
    )
    result = ratings.update(rating_id, rating=4, comment='Good service!')
    assert result is True
    rating = ratings.get('service-uuid', 'user-uuid')
    assert rating['rating'] == 4
    assert rating['comment'] == 'Good service!'
    assert rating['service_uuid'] == 'service-uuid'