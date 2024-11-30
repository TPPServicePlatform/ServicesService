from pymongo import ASCENDING
import logging as logger
import os

from ServicesService.export_lib.lib.utils import get_mongo_client

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
    - provider_id (str): The uuid of the provider user
    - client_id (str): The uuid of the client user
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
        self.collection.create_index([('provider_id', ASCENDING)])
        self.collection.create_index([('client_id', ASCENDING)])
    
    def total_rentals(self, provider_id: str) -> int:
        return self.collection.count_documents({'provider_id': provider_id})
    
    def finished_rentals(self, provider_id: str) -> int:
        return self.collection.count_documents({'provider_id': provider_id, 'status': 'FINISHED'})