from typing import Optional, List, Dict
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, OperationFailure
import logging as logger
import os
import sys
import uuid
from lib.utils import get_actual_time, get_mongo_client, get_time_past_days

HOUR = 60 * 60
MINUTE = 60
MILLISECOND = 1_000

# TODO: (General) -> Create tests for each method && add the required checks in each method

class Ratings:
    """
    Ratings class that stores data in a MongoDB collection.
    Fields:
    - id: int (unique) [pk]
    - service_uuid (str): The uuid of the service
    - rating (int): The rating of the service (1-5)
    - comment (str): The comment of the rating
    - updated_at (datetime): The date when the rating was updated
    - user_uuid (str): The uuid of the user that rated the service
    """

    def __init__(self, test_client=None):
        self.client = test_client or get_mongo_client()
        if not self._check_connection():
            raise Exception("Failed to connect to MongoDB")
        if test_client:
            self.db = self.client[os.getenv('MONGO_TEST_DB')]
        else:
            self.db = self.client[os.getenv('MONGO_DB')]
        self.collection = self.db['ratings']
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
    
    def insert(self, service_uuid: str, rating: int, comment: Optional[str], user_uuid: str) -> Optional[str]:
        try:
            str_uuid = str(uuid.uuid4())
            self.collection.insert_one({
                'uuid': str_uuid,
                'service_uuid': service_uuid,
                'rating': rating,
                'comment': comment,
                'updated_at': get_actual_time(),
                'user_uuid': user_uuid
            })
            return str_uuid
        except DuplicateKeyError as e:
            logger.error(f"DuplicateKeyError: {e}")
            return None
        except OperationFailure as e:
            logger.error(f"OperationFailure: {e}")
            return None
    
    def get(self, service_uuid: str, user_uuid: str) -> Optional[Dict]:
        result = self.collection.find_one({'service_uuid': service_uuid, 'user_uuid': user_uuid})
        if result and '_id' in result:
            result['_id'] = str(result['_id'])
        return result
    
    def get_all(self, service_uuid: str) -> Optional[List[Dict]]:
        result = self.collection.find({'service_uuid': service_uuid})
        result = [{**r, '_id': str(r['_id'])} if '_id' in r else r for r in result]
        return list(dict(r) for r in result) if result else None

    def delete(self, uuid: str) -> bool:
        result = self.collection.delete_one({'uuid': uuid})
        return result.deleted_count > 0
    
    def update(self, uuid: str, rating: int, comment: Optional[str]) -> bool:
        result = self.collection.update_one({'uuid': uuid}, 
                                            {'$set': {
                                                'rating': rating,
                                                'comment': comment,
                                                'updated_at': get_actual_time()
                                            }})
        return result.modified_count > 0
    
    def get_recent(self, max_delta_days: int, available_services: List[str]) -> Optional[list[dict]]:
        query = {'updated_at': {'$gte': get_time_past_days(max_delta_days)},
             'service_uuid': {'$in': available_services},
             'rating': {'$gte': 2.9}}
        projection = {'user_uuid': 1, 'service_uuid': 1, 'rating': 1}
        
        result = self.collection.find(query, projection)
        if not result:
            return None
        
        return [dict(rating) for rating in result]
    
    def get_recent_comments_by_service(self, max_delta_days: int, service_uuid: str) -> Optional[list[str]]:
        query = {'updated_at': {'$gte': get_time_past_days(max_delta_days)},
                 'service_uuid': service_uuid}
        projection = {'comment': 1}
        
        result = self.collection.find(query, projection)
        if not result:
            return None
        
        return [rating['comment'] for rating in result if (rating['comment'] is not None) and (len(rating['comment'])) > 0]
    
    def get_stars_count(self) -> Optional[Dict[int, int]]:
        query = [{'$group': {'_id': '$rating', 'count': {'$sum': 1}}}]
        result = self.collection.aggregate(query)
        if not result:
            return None
        
        return {rating['_id']: rating['count'] for rating in result}