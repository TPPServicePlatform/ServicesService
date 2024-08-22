import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from services_sql import Services

# Set the TESTING environment variable
os.environ['TESTING'] = '1'

# Set a default DATABASE_URL for testing
os.environ['DATABASE_URL'] = 'sqlite:///test.db'

@pytest.fixture(scope='module')
def test_engine():
    engine = create_engine('sqlite:///:memory:', echo=True)
    yield engine
    engine.dispose()

@pytest.fixture(scope='module')
def services(test_engine):
    return Services(engine=test_engine)

def test_insert_service(services, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services.insert(
        service_name='Test Service',
        provider_username='test_user',
        description='Test Description',
        category='Test Category',
        price='100.00'
    )
    assert service_id is not None

def test_get_service(services, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services.insert(
        service_name='Test Service',
        provider_username='test_user',
        description='Test Description',
        category='Test Category',
        price='100.00'
    )
    service = services.get(service_id)
    assert service is not None
    assert service['service_name'] == 'Test Service'
    assert service['provider_username'] == 'test_user'

def test_delete_service(services, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services.insert(
        service_name='Test Service',
        provider_username='test_user',
        description='Test Description',
        category='Test Category',
        price='100.00'
    )
    result = services.delete(service_id)
    assert result is True
    service = services.get(service_id)
    assert service is None

def test_update_service(services, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    service_id = services.insert(
        service_name='Test Service',
        provider_username='test_user',
        description='Test Description',
        category='Test Category',
        price='100.00'
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