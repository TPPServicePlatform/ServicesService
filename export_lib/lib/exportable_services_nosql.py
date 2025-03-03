from typing import Optional, List, Dict
from pymongo import ASCENDING
import logging as logger
import os
import sys
from imported_lib.ServicesService.lib.utils import get_mongo_client

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
    - related_certifications (list): The certifications related to the service
    - created_at (datetime): The date when the service was created
    - category (str): The category of the service
    - price (float): The price of the service
    - hidden (bool): If the service is hidden or not
    - sum_rating (int): The sum of all ratings
    - num_ratings (int): The number of ratings
    - location (longitude and latitude): The address of the service
    - max_distance (int): The maximum distance from the location (kilometers)
    - additional_ids (list): The ids of the additional services
    - created_at (datetime): The date when the service was created
    - updated_at (datetime): The date when the service was updated
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
    
    def ratings_by_provider(self, provider_id: str) -> Optional[List[Dict]]:
        results = self.collection.aggregate([
            {'$match': {'provider_id': provider_id}},
            {'$group': {'_id': provider_id, 'sum_rating': {'$sum': '$sum_rating'}, 'num_ratings': {'$sum': '$num_ratings'}, 'count': {'$sum': 1}, 'provider_id': {'$first': '$provider_id'}}}
        ])
        results = [dict(result) for result in results]
        for result in results:
            print(result)
            if '_id' in result:
                result['_id'] = str(result['_id'])
        return results[0] or None
    
    def get_available_services(self, client_location: dict) -> Optional[List[dict]]:
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

        pipeline.append({'$match': {'hidden': False}})

        results = [dict(result) for result in self.collection.aggregate(pipeline)]
        return [str(result["_id"]) for result in results] if results else None
    
    def delete_certification(self, provider_id: str, certification_id: str) -> bool:
        result = self.collection.update_many({'provider_id': provider_id}, {'$pull': {'related_certifications': certification_id}})
        return result.modified_count > 0