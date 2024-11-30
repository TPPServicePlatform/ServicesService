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
    - location (longitude and latitude): The address of the service
    - max_distance (int): The maximum distance from the location (kilometers)
    - additional_ids (list): The ids of the additional services
    """

    def __init__(self, test_client=None, test_db=None):
        self.client = test_client or get_mongo_client()
        if not self._check_connection():
            raise Exception("Failed to connect to MongoDB")
        if test_client:
            self.db = self.client[os.getenv('MONGO_TEST_DB')]
        else:
            self.db = self.client[test_db or os.getenv('MONGO_DB')]
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
        self.collection.create_index([('location', '2dsphere')])
    
    def insert(self, service_name: str, provider_id: str, description: Optional[str], category: str, price: str, location: dict, max_distance: int) -> Optional[str]:
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
                'num_ratings': 0,
                'location': {'type': 'Point', 'coordinates': [location['longitude'], location['latitude']]},
                'max_distance': max_distance,
                'additional_ids': []
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
    
    def update(self, uuid: str, data: dict) -> bool:
        try:
            result = self.collection.update_one({'uuid': uuid}, {'$set': data})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating service with uuid '{uuid}': {e}")
            return False

    def search(self, client_location: dict, keywords: List[str] = None, provider_id: str = None, min_price: float = None, max_price: float = None, uuid: str = None, hidden: bool = None, min_avg_rating: float = None) -> Optional[List[dict]]:
        pipeline = []

        if not os.environ.get('MONGOMOCK'):
            geo_near_stage = {
                '$geoNear': {
                    'near': {
                        'type': 'Point',
                        'coordinates': [client_location['longitude'], client_location['latitude']]
                    },
                    'distanceField': 'distance',
                    'spherical': True
                }
            }
            pipeline.append(geo_near_stage)

            match_stage = {
                '$match': {
                    '$expr': {
                        '$lte': [
                            '$distance',
                            {'$multiply': ['$max_distance', 1000]} # Convert kilometers to meters
                        ]
                    }
                }
            }
            pipeline.append(match_stage)

        if keywords and len(keywords) > 0:
            keyword_stage = {
            '$match': {
                '$or': [
                {'service_name': {'$regex': '|'.join(keywords), '$options': 'i'}},
                {'description': {'$regex': '|'.join(keywords), '$options': 'i'}}
                ]
            }
            }
            pipeline.append(keyword_stage)

        if provider_id:
            pipeline.append({'$match': {'provider_id': provider_id}})

        if min_price or max_price:
            price_query = {}
            if min_price:
                price_query['$gte'] = min_price
            if max_price:
                price_query['$lte'] = max_price
            pipeline.append({'$match': {'price': price_query}})

        if uuid:
            pipeline.append({'$match': {'uuid': uuid}})

        if hidden is not None:
            pipeline.append({'$match': {'hidden': hidden}})

        if min_avg_rating:
            # query['$expr'] = {'$gte': [{'$cond': [{'$eq': ['$num_ratings', 0]}, 0, {'$divide': ['$sum_rating', '$num_ratings']}]}, min_avg_rating]}
            pipeline.append({'$match': {'$expr': {'$gte': [{'$cond': [{'$eq': ['$num_ratings', 0]}, 0, {'$divide': ['$sum_rating', '$num_ratings']}]}, min_avg_rating]}}})


        results = [dict(result) for result in self.collection.aggregate(pipeline)]

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
            
    def get_additionals(self, service_uuid: str) -> List[str]:
        service = self.get(service_uuid)
        if not service:
            return []
        return service.get('additional_ids', [])
    
    def add_additional(self, service_uuid: str, additional_id: str) -> bool:
        service = self.get(service_uuid)
        if not service:
            return False
        additional_ids = self.get_additionals(service_uuid)
        if additional_id in set(additional_ids):
            return True
        return self.update(service_uuid, {'additional_ids': additional_ids + [additional_id]})
    
    def remove_additional(self, service_uuid: str, additional_id: str) -> bool:
        service = self.get(service_uuid)
        if not service:
            return False
        additional_ids = set(self.get_additionals(service_uuid))
        if additional_id not in additional_ids:
            return True
        return self.update(service_uuid, {'additional_ids': list(additional_ids - {additional_id})})