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
from imported_lib.ServicesService.lib.utils import get_time_past_days, get_mongo_client

HOUR = 60 * 60
MINUTE = 60
MILLISECOND = 1_000
DAY = 24 * HOUR

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

    def get_recent(self, max_delta_days: int) -> Optional[list[dict]]:
        result = self.collection.aggregate([
            {'$match': {'updated_at': {'$gte': get_time_past_days(max_delta_days)}}},
            {'$project': {'user_uuid': 1, 'service_uuid': 1, 'rating': 1}}
        ])
        if not result:
            return None
        return [dict(rating) for rating in result]