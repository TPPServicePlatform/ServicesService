import datetime
from typing import Optional, List, Dict, Tuple
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, OperationFailure
import logging as logger
import os
import time
import uuid
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
    - service_id (str): The uuid of the service
    - additionals (List[str]): The list of uuids of the additionals
    - verification_code (str): The verification code of the rental
    - provider_id (str): The uuid of the provider user
    - estimated_duration (int): The estimated duration of the rental in minutes
    - client_id (str): The uuid of the client user
    - date (datetime): The start date and time of the rental
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
        self.collection.create_index([('provider_id', ASCENDING)])
        self.collection.create_index([('client_id', ASCENDING)])
    
    def insert(self, service_id: str, provider_id: str, client_id: str, date: str, estimated_duration: int, location: Dict, status: str, additionals: List[str] = []) -> Optional[str]:
        try:
            str_uuid = str(uuid.uuid4())
            self.collection.insert_one({
                'uuid': str_uuid,
                'service_id': service_id,
                'additionals': additionals,
                'estimated_duration': estimated_duration,
                'verification_code': None,
                'provider_id': provider_id,
                'client_id': client_id,
                'date': date,
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
    
    def get(self, uuid: str) -> Optional[Dict]:
        result = self.collection.find_one({'uuid': uuid})
        if result:
            return dict(result)
        return None

    def search(self, rental_uuid: str = None, service_id: str = None, provider_id: str = None, client_id: str = None, status: str = None, min_date: str = None, max_date: str = None) -> Optional[List[Dict]]:
        if not any([rental_uuid, service_id, provider_id, client_id, status, min_date, max_date]):
            return None
        
        pipeline = []
        if rental_uuid:
            pipeline.append({'$match': {'uuid': rental_uuid}})
        if service_id:
            pipeline.append({'$match': {'service_id': service_id}})
        if provider_id:
            pipeline.append({'$match': {'provider_id': provider_id}})
        if client_id:
            pipeline.append({'$match': {'client_id': client_id}})
        if status:
            pipeline.append({'$match': {'status': status}})

        if min_date:
            pipeline.append({'$match': {'date': {'$gte': min_date}}})
        if max_date:
            pipeline.append({'$match': {'date': {'$lte': max_date}}})

        results = [dict(result) for result in self.collection.aggregate(pipeline)]
        for result in results:
            if '_id' in result:
                result['_id'] = str(result['_id'])
        return results or None
    
    def print_all(self):
        for rental in self.collection.find():
            print(rental)

    def delete(self, uuid: str) -> bool:
        result = self.collection.delete_one({'uuid': uuid})
        return result.deleted_count > 0
    
    def update_status(self, uuid: str, status: str) -> bool:
        try:
            result = self.collection.update_one({'uuid': uuid}, {'$set': {'status': status, 'updated_at': get_actual_time()}})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating rental with uuid '{uuid}': {e}")
            return False
        
    def update_estimated_duration(self, uuid: str, estimated_duration: int) -> bool:
        try:
            result = self.collection.update_one({'uuid': uuid}, {'$set': {'estimated_duration': estimated_duration, 'updated_at': get_actual_time()}})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating rental with uuid '{uuid}': {e}")
            return False
    
    def total_rentals(self, provider_id: str) -> int:
        return self.collection.count_documents({'provider_id': provider_id})
    
    def finished_rentals(self, provider_id: str) -> int:
        return self.collection.count_documents({'provider_id': provider_id, 'status': 'FINISHED'})
    

    def create_verification_code(self, uuid: str) -> Optional[str]:
        rental = self.get(uuid)
        if not rental:
            return None
        if rental['verification_code']:
            return rental['verification_code']
        try:
            verification_code = str(uuid.uuid4())[:6]
            result = self.collection.update_one({'uuid': uuid}, {'$set': {'verification_code': verification_code, 'updated_at': get_actual_time()}})
            return verification_code if result.modified_count > 0 else None
        except Exception as e:
            logger.error(f"Error creating verification code for rental with uuid '{uuid}': {e}")
            return None


    def get_hiring_report(self, provider_id: str) -> Dict:
        """
        Data to obtain:
        - Total rentals
        - Breackdown of rentals by status
        - Total rentals per month (last 12 months) and the percentage of finished rentals
        - Total rentals per year and the percentage of finished rentals
        """
        total_rentals = self.total_rentals(provider_id)
        finished_rentals = self.finished_rentals(provider_id)
        
        breakdown_by_status = {}
        for status in ['PENDING', 'ACCEPTED', 'REJECTED', 'CANCELLED', 'FINISHED']:
            breakdown_by_status[status] = self.collection.count_documents({'provider_id': provider_id, 'status': status})
            
        breakdown_by_month = {}
        actual_month = (time.now().year, time.now().month)
        for i in range(12):
            month_str = f"{actual_month[0]}-{actual_month[1]}"
            month_total = self.collection.count_documents({'provider_id': provider_id, 'date': {'$regex': f'^{month_str}.*'}})
            month_finished = self.collection.count_documents({'provider_id': provider_id, 'date': {'$regex': f'^{month_str}.*'}, 'status': 'FINISHED'})
            percentage_finished = 0 if month_total == 0 else month_finished / month_total * 100
            breakdown_by_month[month_str] = {
                'total': month_total,
                'percentage_finished': f"{percentage_finished:.2f}%"
            }
            actual_month = (actual_month[0] - 1, 12) if actual_month[1] == 1 else (actual_month[0], actual_month[1] - 1)
            
        breakdown_by_year = {}
        fisrt_year = self.collection.find_one(sort=[('date', ASCENDING)])['date'].year
        actual_year = time.now().year
        for year in range(fisrt_year, actual_year + 1):
            year_str = str(year)
            year_total = self.collection.count_documents({'provider_id': provider_id, 'date': {'$regex': f'^{year_str}.*'}})
            year_finished = self.collection.count_documents({'provider_id': provider_id, 'date': {'$regex': f'^{year_str}.*'}, 'status': 'FINISHED'})
            percentage_finished = 0 if year_total == 0 else year_finished / year_total * 100
            breakdown_by_year[year_str] = {
                'total': year_total,
                'percentage_finished': f"{percentage_finished:.2f}%"
            }
            
        return {
            'total_rentals': total_rentals,
            'finished_rentals': finished_rentals,
            'breakdown_by_status': breakdown_by_status,
            'breakdown_by_month': breakdown_by_month,
            'breakdown_by_year': breakdown_by_year
        }
            

    def get_stats_by_status_last_month(self) -> dict:
        pipeline = [
            {'$match': {'date': {'$gte': datetime.datetime.now() - datetime.timedelta(days=30)}}},
            {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
        ]
        results = self.collection.aggregate(pipeline)
        return {result['_id']: result['count'] for result in results}


