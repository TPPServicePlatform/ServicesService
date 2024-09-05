import datetime
import os
import time
from typing import Optional, Union
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

HOUR = 60 * 60
MINUTE = 60
MILLISECOND = 1_000

def time_to_string(time_in_seconds: float) -> str:
    minutes = int(time_in_seconds // MINUTE)
    seconds = int(time_in_seconds % MINUTE)
    millis = int((time_in_seconds - int(time_in_seconds)) * MILLISECOND)
    return f"{minutes}m {seconds}s {millis}ms"

def get_mongo_client() -> MongoClient:
    uri = f"mongodb+srv://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASSWORD')}@{os.getenv('MONGO_HOST')}/?retryWrites=true&w=majority&appName={os.getenv('MONGO_APP_NAME')}"
    return MongoClient(uri, server_api=ServerApi('1'))

def get_actual_time() -> str:
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
