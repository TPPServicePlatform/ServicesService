from services_sql import Services
import logging as logger
import time
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from lib.utils import *
import sys
time_start = time.time()

logger.basicConfig(format='%(levelname)s: %(asctime)s - %(message)s',
                   stream=sys.stdout, level=logger.INFO)
logger.info("Starting the app")
load_dotenv()

DEBUG_MODE = os.getenv("DEBUG_MODE").title() == "True"
if DEBUG_MODE:
    logger.getLogger().setLevel(logger.DEBUG)
logger.info("DEBUG_MODE: " + str(DEBUG_MODE))

app = FastAPI(
    title="Services API",
    description="API for services management",
    version="1.0.0",
    root_path=os.getenv("ROOT_PATH")
)

origins = [
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sql_manager = Services()

REQUIRED_CREATE_FIELDS = ["username", "service_name"]

starting_duration = time_to_string(time.time() - time_start)
logger.info(f"Services API started in {starting_duration}")

@app.get("/{username}")
def get_services(username: str):
    """
    curl example to get the list of services for an account:
    sin nginx -> curl -X 'GET' 'http://localhost:8001/api/services/marco' --header 'Content-Type: application/json'
    con nginx -> curl -X 'GET' 'http://localhost/api/services/marco' --header 'Content-Type: application/json'
    """
    services = sql_manager.get(username)
    if not services:
        raise HTTPException(status_code=404, detail="Services not found")
    return services

@app.post("/create_service")
def create_services(body: dict):
    """
    curl example to create a service:
    sin nginx -> curl -X 'POST' 'http://localhost:8001/api/services/create_service' --header 'Content-Type: application/json' --data-raw '{"username": "marco", "service_name": "Travel with Marco"}'
    con nginx -> curl -X 'POST' 'http://localhost/api/services/create_service' --header 'Content-Type: application/json' --data-raw '{"username": "marco", "service_name": "Travel with Marco"}'
    """
    username = body.get("username")
    service_name = body.get("service_name")
    if None in [username, service_name]:
        missing_fields = [field for field in REQUIRED_CREATE_FIELDS if body.get(field) is None]
        raise HTTPException(status_code=400, detail=f"Missing fields: {missing_fields}")
    if not sql_manager.insert(username, service_name):
        raise HTTPException(status_code=400, detail="Service already exists for this account")
    return {"status": "ok"}
