import datetime
from typing import Optional, List, Dict
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, OperationFailure
import logging as logger
import os
import sys
import uuid
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
    - images (list): The images of the service (list of strings)
    - estimated_duration (int): The estimated duration of the service in minutes
    - description (str): The description of the service
    - related_certifications (list): The certifications related to the service
    - created_at (datetime): The date when the service was created
    - category (str): The category of the service
    - price (float): The price of the service
    - hidden (bool): If the service is hidden or not
    - sum_rating (int): The sum of all ratings
    - num_ratings (int): The number of ratings
    - reviews_summary (str): The summary of the reviews
    - reviews_summary_updated_at (datetime): The date when the reviews summary was updated
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
        self.collection.create_index([('provider_id', ASCENDING)])
        self.collection.create_index([('category', ASCENDING)])
    
    def insert(self, service_name: str, provider_id: str, description: Optional[str], category: str, price: float, location: dict, max_distance: float, estimated_duration: Optional[int] = None, images: Optional[List[str]] = None) -> Optional[str]:
        try:
            str_uuid = str(uuid.uuid4())
            self.collection.insert_one({
                'uuid': str_uuid,
                'service_name': service_name,
                'provider_id': provider_id,
                'estimated_duration': estimated_duration,
                'description': description,
                'related_certifications': [],
                'category': category,
                'price': price,
                'hidden': False,
                'sum_rating': 0,
                'num_ratings': 0,
                'images': images or [],
                'reviews_summary': '',
                'reviews_summary_updated_at': get_actual_time(),
                'location': {'type': 'Point', 'coordinates': [location['longitude'], location['latitude']]},
                'max_distance': max_distance,
                'additional_ids': [],
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
        
    def _update_data(self, service: dict):
        errors = []
        # ---------- #
        
        if "price" in service:
            if not isinstance(service['price'], (int, float)):
                try:
                    service['price'] = float(service['price'])
                except ValueError:
                    logger.error(f"Price is not a number: {service['service_name']}")
                    # bool_result = False
                    errors.append(f"Price is not a number ({service['price']})")
        else:
            logger.error(f"Price is not in the service: {service['service_name']}")
            # bool_result = False
            errors.append("Price is not in the service")
        # ---------- #
        
        if "max_distance" in service:
            if not isinstance(service['max_distance'], (int, float)):
                try:
                    service['max_distance'] = float(service['max_distance'])
                except ValueError:
                    logger.error(f"Max distance is not a number: {service['service_name']}")
                    # bool_result = False
                    errors.append(f"Max distance is not a number ({service['max_distance']})")
        else:
            logger.error(f"Max distance is not in the service: {service['service_name']}")
            # bool_result = False
            errors.append("Max distance is not in the service")
        # ---------- #
        
        if "location" not in service:
            logger.error(f"Location is not in the service: {service['service_name']}")
            # bool_result = False
            errors.append("Location is not in the service")
        else:
            if not isinstance(service['location'], dict):
                logger.error(f"Location is not a dictionary: {service['service_name']}")
                # bool_result = False
                errors.append(f"Location is not a dictionary ({service['location']})")
            required_keys = {'type', 'coordinates'}
            if not required_keys.issubset(service['location'].keys()):
                logger.error(f"Location does not have the required keys: {service['service_name']}")
                # bool_result = False
                errors.append(f"Location does not have the required keys ({service['location']})")
            if not service['location']['type'] == 'Point':
                logger.error(f"Location type is not 'Point': {service['service_name']}")
                # bool_result = False
                errors.append(f"Location type is not 'Point' ({service['location']['type']})")
            if not isinstance(service['location']['coordinates'], list):
                logger.error(f"Location coordinates is not a list: {service['service_name']}")
                # bool_result = False
                errors.append(f"Location coordinates is not a list ({service['location']['coordinates']})")
            if len(service['location']['coordinates']) != 2:
                logger.error(f"Location coordinates does not have 2 elements: {service['service_name']}")
                # bool_result = False
                errors.append(f"Location coordinates does not have 2 elements ({service['location']['coordinates']})")
            for i, coord in enumerate(service['location']['coordinates']):
                if not isinstance(coord, (int, float)):
                    try:
                        service['location']['coordinates'][i] = float(coord)
                    except ValueError:
                        logger.error(f"Location coordinates is not a number: {service['service_name']}")
                        # bool_result = False
                        coord = "latitude" if i == 1 else "longitude"
                        errors.append(f"Location coordinate '{coord}' is not a number ({coord})")
        # ---------- #
                
        # update the service
        self.collection.update_one({'uuid': service['uuid']}, {'$set': service})
        return errors
        
        
    def correct_data(self):
        # for each service in the collection
        # - if the price is not a int or float, convert it to float if possible (if not print the name of the service)
        # - if the location does not have the format {'type': 'Point', 'coordinates': [location['longitude'], location['latitude']]} print the name of the service
        # - if the location coordinates is not an array of 2 elements, print the name of the service
        # - if the location coordinates array has elements that are not numbers, try to convert them to float (if not print the name of the service)
        # - if the max_distance is not a int or float, convert it to float if possible (if not print the name of the service)
        erroneous_services = {}
        for service in self.collection.find():
            errors = self._update_data(service)
            if errors:
                erroneous_services[(service['uuid'], service['service_name'])] = errors
                # delete the service if it has errors
                # self.collection.delete_one({'uuid': service['uuid']})
        return erroneous_services
        
    
    def get(self, uuid: str) -> Optional[dict]:
        result = self.collection.find_one({'uuid': uuid})
        if result and '_id' in result:
            result['_id'] = str(result['_id'])
        return dict(result) if result else None
    
    def get_by_provider(self, provider_id: str) -> Optional[List[dict]]:
        results = self.collection.find({'provider_id': provider_id})
        if not results:
            return None
        results = [dict(result) for result in results]
        for result in results:
            if '_id' in result:
                result['_id'] = str(result['_id'])
        return results
    
    def delete(self, uuid: str) -> bool:
        result = self.collection.delete_one({'uuid': uuid})
        return result.deleted_count > 0
    
    def delete_provider_services(self, provider_id: str) -> bool:
        result = self.collection.delete_many({'provider_id': provider_id})
        return result.deleted_count > 0
    
    def update(self, uuid: str, data: dict) -> bool:
        data['updated_at'] = get_actual_time()
        try:
            result = self.collection.update_one({'uuid': uuid}, {'$set': data})
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating service with uuid '{uuid}': {e}")
            return False

    def search(self, suspended_providers: set[str], client_location: dict, keywords: List[str] = None, provider_id: str = None, min_price: float = None, max_price: float = None, uuid: str = None, hidden: bool = None, min_avg_rating: float = None, max_avg_rating: float = None, category: str = None) -> Optional[List[dict]]:
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

        if category:
            pipeline.append({'$match': {'category': category}})

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

        if max_avg_rating:
            pipeline.append({'$match': {'$expr': {'$lte': [{'$cond': [{'$eq': ['$num_ratings', 0]}, 0, {'$divide': ['$sum_rating', '$num_ratings']}]}, max_avg_rating]}}})

        pipeline.append({'$match': {'provider_id': {'$nin': list(suspended_providers)}}})
        
        pipeline.append({'$project': {'images': 0}})

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
        return self.update(service_uuid, {'sum_rating': sum_rating, 'num_ratings': num_ratings, 'updated_at': get_actual_time()})
            
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
        return self.update(service_uuid, {'additional_ids': additional_ids + [additional_id], 'updated_at': get_actual_time()})
    
    def remove_additional(self, service_uuid: str, additional_id: str) -> bool:
        service = self.get(service_uuid)
        if not service:
            return False
        additional_ids = set(self.get_additionals(service_uuid))
        if additional_id not in additional_ids:
            return True
        return self.update(service_uuid, {'additional_ids': list(additional_ids - {additional_id}), 'updated_at': get_actual_time()})
    
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
    
    def get_certifications(self, service_uuid: str) -> Optional[List[str]]:
        service = self.get(service_uuid)
        if not service:
            return None
        return service.get('related_certifications', None)
    
    def get_similar_services(self, client_location: dict, category: str) -> Optional[List[Dict]]:
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
        
        match_stage = {
            '$match': {'category': category}
        }
        pipeline.append(match_stage)


        results = [dict(result) for result in self.collection.aggregate(pipeline)]

        for result in results:
            if '_id' in result:
                result['_id'] = str(result['_id'])
        return results or None
    
    def get_provider_categories(self, provider_id: str) -> List[str]:
        results = self.collection.aggregate([
            {'$match': {'provider_id': provider_id}},
            {'$group': {'_id': '$category'}}
        ])
        results = [result['_id'] for result in results]
        return results or None
    
    def get_provider_category_avg_price(self, provider_id: str, category: str) -> float:
        results = self.collection.aggregate([
            {'$match': {'provider_id': provider_id, 'category': category}},
            {'$group': {'_id': category, 'avg_price': {'$avg': '$price'}}}
        ])
        results = [result['avg_price'] for result in results]
        return results[0] if results else None
    
    def get_provider_avg_score(self, provider_id: str) -> float:
        results = self.collection.aggregate([
            {'$match': {'provider_id': provider_id}},
            {'$group': {'_id': provider_id, 'total_rating_count': {'$sum': '$num_ratings'}, 'total_rating_sum': {'$sum': '$sum_rating'}}}
        ])
        avg_score = sum(result['total_rating_sum'] / result['total_rating_count'] for result in results)
        return avg_score / len(results) if results else None
    
    def add_certification(self, service_uuid: str, certification_id: str) -> bool:
        service = self.get(service_uuid)
        if not service:
            return False
        certifications = service.get('related_certifications', [])
        if certification_id in certifications:
            return True
        return self.update(service_uuid, {'related_certifications': certifications + [certification_id], 'updated_at': get_actual_time()})
    
    def delete_certification(self, service_uuid: str, certification_id: str) -> bool:
        service = self.get(service_uuid)
        if not service:
            return False
        certifications = set(service.get('related_certifications', []))
        if certification_id not in certifications:
            return True
        return self.update(service_uuid, {'related_certifications': list(certifications - {certification_id}), 'updated_at': get_actual_time()})
    
    def delete_certification(self, provider_id: str, certification_id: str) -> bool:
        result = self.collection.update_many({'provider_id': provider_id}, {'$pull': {'related_certifications': certification_id}})
        return result.modified_count > 0
    
    def get_stats_by_category(self) -> dict:
        pipeline = [
            {'$match': {'hidden': False}},
            {'$group': {'_id': '$category', 'count': {'$sum': 1}}}
        ]
        results = [dict(result) for result in self.collection.aggregate(pipeline)]
        return {result['_id']: result['count'] for result in results}