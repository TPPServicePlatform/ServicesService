from typing import Optional, List, Dict, Tuple
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

class Rentals:
    """
    Rentals class that stores data in a MongoDB collection.
    Rentals:
    - uuid: int (unique) [pk]
    - service_uuid (str): The uuid of the service
    - provider_uuid (str): The uuid of the provider user
    - client_uuid (str): The uuid of the client user
    - start_date (datetime): The start date of the rental
    - end_date (datetime): The end date of the rental
    - location (longitude and latitude): The address of where the service will be provided
    - status (str): The status of the rental (PENDING, ACCEPTED, REJECTED, CANCELLED, FINISHED)
    - created_at (datetime): The date when the rental was created
    - updated_at (datetime): The date when the rental was updated
    """

    def __init__(self, test_client=None):
        self.client = test_client or get_mongo_client()
        if not self._check_connection():
            raise Exception("Failed to connect to MongoDB")
        if test_client:
            self.db = self.client[os.getenv('MONGO_TEST_DB')]
        else:
            self.db = self.client[os.getenv('MONGO_DB')]
        self.collection = self.db['rentals']
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
        self.collection.create_index([('provider_uuid', ASCENDING)])
        self.collection.create_index([('client_uuid', ASCENDING)])
    
    def insert(self, service_uuid: str, provider_uuid: str, client_uuid: str, start_date: str, end_date: str, location: Dict, status: str) -> Optional[str]:
        try:
            str_uuid = str(uuid.uuid4())
            self.collection.insert_one({
                'uuid': str_uuid,
                'service_uuid': service_uuid,
                'provider_uuid': provider_uuid,
                'client_uuid': client_uuid,
                'start_date': start_date,
                'end_date': end_date,
                'location': location,
                'status': status,
                'created_at': get_actual_time(),
                'updated_at': get_actual_time()
            })
            return str_uuid
        except DuplicateKeyError as e:
            logger.error(f"DuplicateKeyError: {e}")
            return None
        except OperationFailure as e:
            logger.error(f"OperationFailure: {e}")
            return None
    
    def search(self, rental_uuid: str = None, service_uuid: str = None, provider_uuid: str = None, client_uuid: str = None, status: str = None, start_date: Dict = None, end_date: Dict = None) -> Optional[List[Dict]]:
        if not any([rental_uuid, service_uuid, provider_uuid, client_uuid, status, start_date, end_date]):
            return None
        
        pipeline = []
        if rental_uuid:
            # pipeline.append({'uuid': rental_uuid})
            pipeline.append({'$match': {'uuid': rental_uuid}})
        if service_uuid:
            # pipeline.append({'service_uuid': service_uuid})
            pipeline.append({'$match': {'service_uuid': service_uuid}})
        if provider_uuid:
            # pipeline.append({'provider_uuid': provider_uuid})
            pipeline.append({'$match': {'provider_uuid': provider_uuid}})
        if client_uuid:
            # pipeline.append({'client_uuid': client_uuid})
            pipeline.append({'$match': {'client_uuid': client_uuid}})
        if status:
            # pipeline.append({'status': status})
            pipeline.append({'$match': {'status': status}})

        for range_date in [('start_date', start_date), ('end_date', end_date)]:
            if range_date[1]:
                min_date = range_date[1].get('MIN')
                max_date = range_date[1].get('MAX')
                if min_date:
                    # pipeline.append({range_date[0]: {'$gte': min_date}})
                    pipeline.append({'$match': {range_date[0]: {'$gte': min_date}}})
                if max_date:
                    # pipeline.append({range_date[0]: {'$lte': max_date}})
                    pipeline.append({'$match': {range_date[0]: {'$lte': max_date}}})

        results = [dict(result) for result in self.collection.aggregate(pipeline)]
        for result in results:
            if '_id' in result:
                result['_id'] = str(result['_id'])
        return results or None

    def delete(self, uuid: str) -> bool:
        result = self.collection.delete_one({'uuid': uuid})
        return result.deleted_count > 0
    
    def update(self, uuid: str, status: str) -> bool:
        try:
            result = self.collection.update_one({'uuid': uuid}, {'$set': {'status': status, 'updated_at': get_actual_time()}})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating rental with uuid '{uuid}': {e}")
            return False