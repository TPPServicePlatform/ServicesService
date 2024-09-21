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
    Services class that stores data in a MongoDB collection.
    Fields:
    - id: int (unique) [pk]
    - service_name (str): The name of the service
    - provider_id (str): The id of the account that provides the service
    - description (str): The description of the service
    - created_at (datetime): The date when the service was created
    - category (str): The category of the service
    - price (float): The price of the service
    - hidden (bool): If the service is hidden or not
    - sum_rating (int): The sum of all ratings
    - num_ratings (int): The number of ratings
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
    
    def insert(self, service_name: str, provider_id: str, description: Optional[str], category: str, price: str) -> Optional[str]:
        try:
            str_uuid = str(uuid.uuid4())
            self.collection.insert_one({
                'uuid': str_uuid,
                'service_name': service_name,
                'provider_id': provider_id,
                'description': description,
                'created_at': get_actual_time(),
                'category': category,
                'price': price,
                'hidden': False,
                'sum_rating': 0,
                'num_ratings': 0
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
        if result and '_id' in result:
            result['_id'] = str(result['_id'])
        return dict(result) if result else None
    
    def delete(self, uuid: str) -> bool:
        result = self.collection.delete_one({'uuid': uuid})
        return result.deleted_count > 0

    def get(self, uuid: str) -> Optional[dict]:
        result = self.collection.find_one({'uuid': uuid})
        if result and '_id' in result:
            result['_id'] = str(result['_id'])
        return result
    
    def update(self, uuid: str, data: dict) -> bool:
        try:
            result = self.collection.update_one({'uuid': uuid}, {'$set': data})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating service with uuid '{uuid}': {e}")
            return False
        
    def search(self, keywords: List[str] = None, provider_id: str = None, min_price: float = None, max_price: float = None, uuid: str = None, hidden: bool = None, min_rating: float = None) -> Optional[List[dict]]:
        query = {}
        
        if keywords and len(keywords) > 0:
            query['$or'] = [
                {'service_name': {'$in': keywords}},
                {'description': {'$in': keywords}}
            ]
        
        if provider_id:
            query['provider_id'] = provider_id
        
        if min_price or max_price:
            query['price'] = {}
            if min_price:
                query['price']['$gte'] = min_price
            if max_price:
                query['price']['$lte'] = max_price
        
        if uuid:
            query['uuid'] = uuid
        
        if hidden is not None:
            query['hidden'] = hidden

        if min_rating:
            query['$expr'] = {'$gte': [{'$divide': ['$sum_rating', '$num_ratings']}, min_rating]}
        
        results = [dict(result) for result in self.collection.find(query)]
        for result in results:
            if '_id' in result:
                result['_id'] = str(result['_id'])
        return results or None

    def update_rating(self, service_uuid: str, rating: int, sum: bool) -> bool:
        service = self.get(service_uuid)
        if not service:
            return False
        sum_rating = service['sum_rating'] + rating * (1 if sum else -1)
        num_ratings = service['num_ratings'] + (1 if sum else -1)
        return self.update(service_uuid, {'sum_rating': sum_rating, 'num_ratings': num_ratings})
            
