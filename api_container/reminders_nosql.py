import datetime
import time
from typing import Optional, List, Dict, Tuple
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, OperationFailure
import logging as logger
import os
import sys
import uuid

from mobile_token_nosql import send_notification
from lib.utils import get_mongo_client

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
    
def save_reminders(reminders_manager: Reminders, rental_date: str, user_id: str, service_name: str, rental_id: str):
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    week_before = datetime.datetime.strptime(rental_date, '%Y-%m-%d') - datetime.timedelta(days=7)
    week_before = week_before.strftime('%Y-%m-%d')
    day_before = datetime.datetime.strptime(rental_date, '%Y-%m-%d') - datetime.timedelta(days=1)
    day_before = day_before.strftime('%Y-%m-%d')
    title = f"Upcoming rental: {service_name}"
    if week_before > today:
        body = f"Your rental of {service_name} is in a week"
        reminders_manager.add_reminder(week_before, user_id, title, body, rental_id)
    if day_before > today:
        body = f"Your rental of {service_name} is tomorrow"
        reminders_manager.add_reminder(day_before, user_id, title, body, rental_id)
    body = f"Your rental of {service_name} is today"
    reminders_manager.add_reminder(rental_date, user_id, title, body, rental_id)

def daily_notification_sender():
    reminders_manager = Reminders()
    while True:
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        reminders = reminders_manager.get_reminders(today)
        if reminders:
            for reminder in reminders:
                send_notification(reminder['user_id'], reminder['title'], reminder['description'])
            reminders_manager.delete_date(today)
        time_until_midnight = (datetime.datetime.strptime(today, '%Y-%m-%d') + datetime.timedelta(days=1) - datetime.datetime.now()).total_seconds()
        time.sleep(time_until_midnight)