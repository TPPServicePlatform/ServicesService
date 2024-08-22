from services_sql import Services
import logging as logger
import time
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from lib.utils import time_to_string, get_test_engine

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

if os.getenv('TESTING'):
    test_engine = get_test_engine()
    sql_manager = Services(engine=test_engine)
else:
    sql_manager = Services()

REQUIRED_CREATE_FIELDS = {"service_name", "provider_username", "category", "price"}
OPTIONAL_CREATE_FIELDS = {"description"}
VALID_UPDATE_FIELDS = {"service_name", "description", "category", "price", "hidden"}

starting_duration = time_to_string(time.time() - time_start)
logger.info(f"Services API started in {starting_duration}")

# TODO: (General) -> Create tests for each endpoint && add the required checks in each endpoint

@app.get("/{uuid}")
def get(uuid: str):
    services = sql_manager.get(uuid)
    if not services:
        raise HTTPException(status_code=404, detail=f"Service with uuid '{uuid}' not found")
    return services

@app.post("/create")
def create(body: dict):
    data = {key: value for key, value in body.items() if key in REQUIRED_CREATE_FIELDS or key in OPTIONAL_CREATE_FIELDS}

    if not all([field in data for field in REQUIRED_CREATE_FIELDS]):
        missing_fields = REQUIRED_CREATE_FIELDS - set(data.keys())
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")
    
    data.update({field: None for field in OPTIONAL_CREATE_FIELDS if field not in data})

    uuid = sql_manager.insert(data["service_name"], data["provider_username"], data["description"], data["category"], data["price"])
    if not uuid:
        raise HTTPException(status_code=400, detail="Error creating service")
    return {"status": "ok", "service_id": uuid}

@app.delete("/{id}")
def delete(id: str):
    if not sql_manager.delete(id):
        raise HTTPException(status_code=404, detail="Service not found")
    return {"status": "ok"}

@app.put("/{id}")
def update(id: str, body: dict):
    update = {key: value for key, value in body.items() if key in VALID_UPDATE_FIELDS}

    not_valid_fields = set(update.keys()) - VALID_UPDATE_FIELDS
    if not_valid_fields:
        raise HTTPException(status_code=400, detail=f"Invalid fields: {', '.join(not_valid_fields)}")
    
    if not sql_manager.get(id):
        raise HTTPException(status_code=404, detail="Service not found")
    
    if not sql_manager.update(id, update):
        raise HTTPException(status_code=400, detail="Error updating service")
    return {"status": "ok"}
