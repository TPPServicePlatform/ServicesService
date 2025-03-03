import datetime
import os
import time
from typing import Optional, Union
from fastapi import HTTPException
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import logging as logger
import re
import sentry_sdk

DAY = 24 * 60 * 60
HOUR = 60 * 60
MINUTE = 60
MILLISECOND = 1_000

def time_to_string(time_in_seconds: float) -> str:
    minutes = int(time_in_seconds // MINUTE)
    seconds = int(time_in_seconds % MINUTE)
    millis = int((time_in_seconds - int(time_in_seconds)) * MILLISECOND)
    return f"{minutes}m {seconds}s {millis}ms"

def get_mongo_client() -> MongoClient:
    if not all([os.getenv('MONGO_USER'), os.getenv('MONGO_PASSWORD'), os.getenv('MONGO_HOST'), os.getenv('MONGO_APP_NAME')]):
        raise HTTPException(status_code=500, detail="MongoDB environment variables are not set properly")
    uri = f"mongodb+srv://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASSWORD')}@{os.getenv('MONGO_HOST')}/?retryWrites=true&w=majority&appName={os.getenv('MONGO_APP_NAME')}"
    print(f"Connecting to MongoDB: {uri}")
    logger.getLogger('pymongo').setLevel(logger.WARNING)
    return MongoClient(uri)

def get_actual_time() -> str:
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

def is_float(value):
    float_pattern = re.compile(r'^-?\d+(\.\d+)?$')
    return bool(float_pattern.match(value))

def validate_location(client_location, required_fields):
    if type(client_location) == str:
        if client_location.count(",") != 1:
            raise HTTPException(status_code=400, detail="Invalid client location (must be in the format 'longitude,latitude')")
        client_location = client_location.split(",")
        client_location = {"longitude": client_location[0], "latitude": client_location[1]}
    elif type(client_location) == dict:
        if not all([field in client_location for field in required_fields]):
            missing_fields = required_fields - set(client_location.keys())
            raise HTTPException(status_code=400, detail=f"Missing location fields: {', '.join(missing_fields)}")
    else:
        raise HTTPException(status_code=400, detail="Invalid client location (must be a string or a dictionary)")
    if not all([type(value) in [int, float] or is_float(value) for value in client_location.values()]):
        raise HTTPException(status_code=400, detail="Invalid client location (each value must be a float)")
    client_location = {key: float(value) for key, value in client_location.items()}
    return client_location

def verify_fields(required_fields: set, optional_fields: set, data: dict):
    if not all(field in data for field in required_fields):
        missing_fields = required_fields - set(data.keys())
        raise Exception(f"Missing required fields: {', '.join(missing_fields)}")
    
    if not all(field in required_fields.union(optional_fields) for field in data.keys()):
        invalid_fields = set(data.keys()) - required_fields.union(optional_fields)
        raise Exception(f"Invalid fields: {', '.join(invalid_fields)}")
    
def get_time_past_days(days: int) -> str:
    return datetime.datetime.fromtimestamp(time.time() - days * DAY).strftime('%Y-%m-%d %H:%M:%S')

def validate_date(date: str) -> str:
    try:
        datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        return date
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format (must be 'YYYY-MM-DD HH:MM:SS')")
    
def create_repetitions_list(interval: str, max_repetitions: int, starting_time: str, ending_time: str) -> list:
    def get_month_days(month: int) -> int:
        if month == 2:
            return 28
        if month in {4, 6, 9, 11}:
            return 30
        return 31

    DELTAS = {
        "DAILY": datetime.timedelta(days=1), 
        "WEEKLY": datetime.timedelta(weeks=1), 
        "MONTHLY": datetime.timedelta(days= get_month_days(int(starting_time[5:7]))),
        "YEARLY": datetime.timedelta(days=365)
        }
    
    repetitions = []
    starting_time = datetime.datetime.strptime(starting_time, '%Y-%m-%d %H:%M:%S')
    ending_time = datetime.datetime.strptime(ending_time, '%Y-%m-%d %H:%M:%S')

    interval = DELTAS.get(interval)
    if interval is None:
        raise HTTPException(status_code=400, detail="Invalid interval (must be 'DAILY', 'WEEKLY', 'MONTHLY' or 'YEARLY')")
    
    while len(repetitions) < max_repetitions:
        repetitions.append((starting_time.strftime('%Y-%m-%d %H:%M:%S'), ending_time.strftime('%Y-%m-%d %H:%M:%S')))
        starting_time += interval
        ending_time += interval
        # starting_time += DELTAS[interval]
        # ending_time += DELTAS[interval]

    return repetitions

def sentry_init():
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        # Add data like request headers and IP for users,
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        send_default_pii=True,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=1.0,
        _experiments={
            # Set continuous_profiling_auto_start to True
            # to automatically start the profiler on when
            # possible.
            "continuous_profiling_auto_start": True,
        },
    )
    
