import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import logging as logger

def get_mongo_client() -> MongoClient:
    uri = f"mongodb+srv://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASSWORD')}@{os.getenv('MONGO_HOST')}/?retryWrites=true&w=majority&appName={os.getenv('MONGO_APP_NAME')}"
    print(f"Connecting to MongoDB: {uri}")
    logger.getLogger('pymongo').setLevel(logger.WARNING)
    return MongoClient(uri, server_api=ServerApi('1'))