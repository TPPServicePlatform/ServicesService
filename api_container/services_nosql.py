from typing import Optional, List, Dict
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, OperationFailure
import logging as logger
import os
import sys
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from lib.utils import get_actual_time, get_mongo_client

HOUR = 60 * 60
MINUTE = 60
MILLISECOND = 1_000

# TODO: (General) -> Create tests for each method && add the required checks in each method

class Services:
    """
    Services class that stores data in a db through sqlalchemy
    Fields:
    - id: int (unique) [pk]
    - service_name (str): The name of the service
    - provider_username (str): The username of the account that provides the service
    - description (str): The description of the service
    - created_at (datetime): The date when the service was created
    - category (str): The category of the service
    - price (float): The price of the service
    - hidden (bool): If the service is hidden or not
    """

    def __init__(self, test_client=None):
        self.client = test_client or get_mongo_client()
        if not self._check_connection():
            raise Exception("Failed to connect to MongoDB")
        if test_client:
            self.db = self.client[os.getenv('MONGO_TEST_DB')]
        else:
            self.db = self.client[os.getenv('MONGO_DB')]
        self.collection = self.db['services']
        self._create_collection()
    
    def _check_connection(self):
        try:
            self.client.admin.command('ping')
        except Exception as e:
            logger.error(e)
            return False
        return True

    def _create_collection(self):
        self.collection.create_index([('uuid', ASCENDING)], unique=True)
    
    def insert(self, service_name: str, provider_username: str, description: Optional[str], category: str, price: str) -> Optional[str]:
        try:
            str_uuid = str(uuid.uuid4())
            self.collection.insert_one({
                'uuid': str_uuid,
                'service_name': service_name,
                'provider_username': provider_username,
                'description': description,
                'created_at': get_actual_time(),
                'category': category,
                'price': price,
                'hidden': False
            })
            return str_uuid
        except DuplicateKeyError as e:
            logger.error(f"DuplicateKeyError: {e}")
            return None
        except OperationFailure as e:
            logger.error(f"OperationFailure: {e}")
            return None
    
    def get(self, uuid: str) -> Optional[dict]:
        result = self.collection.find_one({'uuid': uuid})
        if result:
            result['_id'] = str(result['_id'])
        return result
    
    def delete(self, uuid: str) -> bool:
        result = self.collection.delete_one({'uuid': uuid})
        return result.deleted_count > 0
    
    def update(self, uuid: str, data: dict) -> bool:
        try:
            logger.info(f"Updating service with uuid '{uuid}'")
            logger.info(f"Data to update: {data}")
            result = self.collection.update_one({'uuid': uuid}, {'$set': data})
            logger.info(f"Modified count: {result.modified_count}")
            logger.info(f"Matched count: {result.matched_count}")
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating service with uuid '{uuid}': {e}")
            return False
    