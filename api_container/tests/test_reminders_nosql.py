import pytest
import mongomock
from unittest.mock import patch
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from reminders_nosql import Reminders

# Run with the following command:
# pytest ServicesService/api_container/tests/test_reminders_nosql.py

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
def reminders(mongo_client):
    return Reminders(test_client=mongo_client)

def test_create_date(reminders):
    reminders._create_date('2021-01-01')
    assert reminders.collection.find_one({'date': '2021-01-01'}) is not None

def test_add_reminder(reminders):
    reminders.add_reminder('2021-01-01', 'user_1', 'Test Title', 'Test Description', 'rental_1')
    doc = reminders.collection.find_one({'date': '2021-01-01'})
    assert doc is not None
    assert len(doc['reminders']) == 1
    assert doc['reminders'][0]['user_id'] == 'user_1'
    assert doc['reminders'][0]['title'] == 'Test Title'
    assert doc['reminders'][0]['description'] == 'Test Description'
    assert doc['reminders'][0]['rental_id'] == 'rental_1'

def test_get_reminders(reminders):
    reminders.add_reminder('2021-01-01', 'user_1', 'Test Title', 'Test Description', 'rental_1')
    reminders.add_reminder('2021-01-01', 'user_2', 'Test Title 2', 'Test Description 2', 'rental_2')
    reminders.add_reminder('2021-01-02', 'user_3', 'Test Title 3', 'Test Description 3', 'rental_3')
    reminders.add_reminder('2021-01-02', 'user_4', 'Test Title 4', 'Test Description 4', 'rental_4')
    assert len(reminders.get_reminders('2021-01-01')) == 2
    assert len(reminders.get_reminders('2021-01-02')) == 2
    assert reminders.get_reminders('2021-01-03') is None

def test_delete_date(reminders):
    reminders.add_reminder('2021-01-01', 'user_1', 'Test Title', 'Test Description', 'rental_1')
    reminders.add_reminder('2021-01-01', 'user_2', 'Test Title 2', 'Test Description 2', 'rental_2')
    reminders.add_reminder('2021-01-02', 'user_3', 'Test Title 3', 'Test Description 3', 'rental_3')
    reminders.add_reminder('2021-01-02', 'user_4', 'Test Title 4', 'Test Description 4', 'rental_4')
    reminders.delete_date('2021-01-01')
    assert reminders.get_reminders('2021-01-01') is None
    assert reminders.get_reminders('2021-01-02') is not None
    reminders.delete_date('2021-01-02')
    assert reminders.get_reminders('2021-01-02') is None

def test_delete_rental_reminders(reminders):
    reminders.add_reminder('2021-01-01', 'user_1', 'Test Title', 'Test Description', 'rental_1')
    reminders.add_reminder('2021-01-01', 'user_2', 'Test Title 2', 'Test Description 2', 'rental_2')
    reminders.add_reminder('2021-01-02', 'user_3', 'Test Title 3', 'Test Description 3', 'rental_3')
    reminders.add_reminder('2021-01-02', 'user_1', 'Test Title 4', 'Test Description 4', 'rental_1')
    reminders.delete_rental_reminders('rental_1')
    assert len(reminders.get_reminders('2021-01-01')) == 1
    assert len(reminders.get_reminders('2021-01-02')) == 1
    reminders.delete_rental_reminders('rental_3')
    assert len(reminders.get_reminders('2021-01-01')) == 1
    assert reminders.get_reminders('2021-01-02') is None