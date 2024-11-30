from typing import Optional, List, Dict
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

class Additionals:
    """
    Additionals class that stores data in a MongoDB collection.
    Fields:
    - id: int (unique) [pk]
    - additional_name (str): The name of the additional
    - provider_id (str): The id of the account that provides the additional
    - description (str): The description of the additional
    - created_at (datetime): The date when the additional was created
    - price (float): The price of the additional
    - hidden (bool): If the additional is hidden or not
    """

    def __init__(self, test_client=None, test_db=None):
        self.client = test_client or get_mongo_client()
        if not self._check_connection():
            raise Exception("Failed to connect to MongoDB")
        if test_client:
            self.db = self.client[os.getenv('MONGO_TEST_DB')]
        else:
            self.db = self.client[test_db or os.getenv('MONGO_DB')]
        self.collection = self.db['additionals']
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
    
    def insert(self, name: str, provider_id: str, description: str, price: float) -> Optional[str]:
        try:
            str_uuid = str(uuid.uuid4())
            self.collection.insert_one({
                'uuid': str_uuid,
                'additional_name': name,
                'provider_id': provider_id,
                'description': description,
                'created_at': get_actual_time(),
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
    
    def get(self, additional_id: str) -> Optional[Dict]:
        result = self.collection.find_one({'uuid': additional_id})
        if result and '_id' in result:
            result['_id'] = str(result['_id'])
        return dict(result) if result else None
    
    def delete(self, additional_id: str) -> bool:
        try:
            result = self.collection.delete_one({'uuid': additional_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting additional with id '{additional_id}': {e}")
            return False
        
    def update(self, additional_id: str, data: dict) -> bool:
        try:
            result = self.collection.update_one({'uuid': additional_id}, {'$set': data})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating additional with id '{additional_id}': {e}")
            return False
    
    def get_by_provider(self, provider_id: str) -> Optional[List[Dict]]:
        results = self.collection.find({'provider_id': provider_id})
        results = [dict(result) for result in results]
        for result in results:
            if result and '_id' in result:
                result['_id'] = str(result['_id'])
        return results or None