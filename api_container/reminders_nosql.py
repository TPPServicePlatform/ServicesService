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

class Reminders:
    """
    Reminders class that stores data in a MongoDB collection.
    Reminders:
    - date: str (unique) [pk] The date that the reminders are set for
    - reminders (List[Dict]): The list of reminders for the date

    reminder structure:
    - rental_id (str): The uuid of the reminder
    - user_id (str): The uuid of the user that the reminder is for
    - title (str): The title of the reminder
    - description (str): The description of the reminder
    """

    def __init__(self, test_client=None):
        self.client = test_client or get_mongo_client()
        if not self._check_connection():
            raise Exception("Failed to connect to MongoDB")
        if test_client:
            self.db = self.client[os.getenv('MONGO_TEST_DB')]
        else:
            self.db = self.client[os.getenv('MONGO_DB')]
        self.collection = self.db['reminders']
        self._create_collection()
    
    def _check_connection(self):
        try:
            self.client.admin.command('ping')
        except Exception as e:
            logger.error(e)
            return False
        return True

    def _create_collection(self):
        self.collection.create_index([('date', ASCENDING)], unique=True)

    def get_reminders(self, date: str) -> Optional[Dict]:
        doc = self.collection.find_one({'date': date})
        return (doc['reminders'] or None) if doc else None
    
    def _create_date(self, date: str):
        self.collection.insert_one({'date': date, 'reminders': []})
    
    def add_reminder(self, date: str, user_id: str, title: str, description: str, rental_id: str) -> bool:
        if not self.collection.find_one({'date': date}):
            self._create_date(date)
        reminder = {
            'rental_id': rental_id,
            'user_id': user_id,
            'title': title,
            'description': description
        }
        try:
            self.collection.update_one({'date': date}, {'$push': {'reminders': reminder}})
            return True
        except Exception as e:
            logger.error(e)
            return False
        
    def delete_rental_reminders(self, rental_id: str) -> bool:
        result = self.collection.update_many({}, {'$pull': {'reminders': {'rental_id': rental_id}}})
        return result.modified_count > 0
    
    def delete_date(self, date: str) -> bool:
        result = self.collection.delete_one({'date': date})
        return result.deleted_count > 0