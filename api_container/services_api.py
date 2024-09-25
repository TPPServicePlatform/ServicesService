from typing import Optional, Tuple
from services_nosql import Services
from ratings_nosql import Ratings
import mongomock
import logging as logger
import time
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from lib.utils import time_to_string

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
    client = mongomock.MongoClient()
    services_manager = Services(test_client=client)
    ratings_manager = Ratings(test_client=client)
else:
    services_manager = Services()
    ratings_manager = Ratings()

REQUIRED_CREATE_FIELDS = {"service_name", "provider_id", "category", "price", "location", "max_distance"}
REQUIRED_LOCATION_FIELDS = {"longitude", "latitude"}
OPTIONAL_CREATE_FIELDS = {"description"}
VALID_UPDATE_FIELDS = {"service_name", "description", "category", "price", "hidden"}
REQUIRED_REVIEW_FIELDS = {"rating", "user_uuid"}
OPTIONAL_REVIEW_FIELDS = {"comment"}

starting_duration = time_to_string(time.time() - time_start)
logger.info(f"Services API started in {starting_duration}")

# TODO: (General) -> Create tests for each endpoint && add the required checks in each endpoint

@app.post("/create")
def create(body: dict):
    data = {key: value for key, value in body.items() if key in REQUIRED_CREATE_FIELDS or key in OPTIONAL_CREATE_FIELDS}

    if not all([field in data for field in REQUIRED_CREATE_FIELDS]):
        missing_fields = REQUIRED_CREATE_FIELDS - set(data.keys())
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")

    if not isinstance(data["location"], dict):
        raise HTTPException(status_code=400, detail="Location must be a dictionary")

    if not all([field in data["location"] for field in REQUIRED_LOCATION_FIELDS]):
        missing_fields = REQUIRED_LOCATION_FIELDS - set(data["location"].keys())
        raise HTTPException(status_code=400, detail=f"Missing location fields: {', '.join(missing_fields)}")

    extra_fields = set(data["location"].keys()) - REQUIRED_LOCATION_FIELDS
    if extra_fields:
        raise HTTPException(status_code=400, detail=f"Extra location fields: {', '.join(extra_fields)}")

    data.update({field: None for field in OPTIONAL_CREATE_FIELDS if field not in data})

    uuid = services_manager.insert(data["service_name"], data["provider_id"], data["description"], data["category"], data["price"], data["location"], data["max_distance"])
    if not uuid:
        raise HTTPException(status_code=400, detail="Error creating service")
    return {"status": "ok", "service_id": uuid}

@app.delete("/{id}")
def delete(id: str):
    if not services_manager.delete(id):
        raise HTTPException(status_code=404, detail="Service not found")
    return {"status": "ok"}

@app.put("/{id}")
def update(id: str, body: dict):
    logger.info(f"body: {body}")
    update = {key: value for key, value in body.items() if key in VALID_UPDATE_FIELDS}
    logger.info(f"update: {update}")
    not_valid_fields = set(body.keys()) - VALID_UPDATE_FIELDS
    logger.info(f"not_valid_fields: {not_valid_fields}")
    if not_valid_fields:
        raise HTTPException(status_code=400, detail=f"Invalid fields: {', '.join(not_valid_fields)}")

    if not services_manager.get(id):
        raise HTTPException(status_code=404, detail="Service not found")

    if not services_manager.update(id, update):
        raise HTTPException(status_code=400, detail="Error updating service")
    return {"status": "ok"}

@app.get("/search")
def search(
    client_location: str = Query(...),
    keywords: Optional[str] = Query(None),
    provider_id: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    hidden: Optional[bool] = Query(None),
    uuid: Optional[str] = Query(None)
):
    if keywords:
        keywords = keywords.split(",")
    if not any([keywords, provider_id, min_price, max_price, hidden, uuid]):
        raise HTTPException(status_code=400, detail="No search parameters provided")

    if not client_location:
        raise HTTPException(status_code=400, detail="Client location is required")
    if client_location.count(",") != 1:
        raise HTTPException(status_code=400, detail="Invalid client location (must be in the format 'longitude,latitude')")
    client_location = client_location.split(",")
    if not all([is_float(value) for value in client_location]):
        raise HTTPException(status_code=400, detail="Invalid client location (must be in the format 'longitude,latitude')")
    client_location = {"longitude": float(client_location[0]), "latitude": float(client_location[1])}

    results = services_manager.search(client_location, keywords, provider_id, min_price, max_price, uuid, hidden)
    if not results:
        raise HTTPException(status_code=404, detail="No results found")
    return {"status": "ok", "results": results}

def is_float(value):
    return value.replace('.','',1).isdigit()

@app.put("/{id}/reviews")
def review(id: str, body: dict):
    data = {key: value for key, value in body.items() if key in REQUIRED_REVIEW_FIELDS or key in OPTIONAL_REVIEW_FIELDS}

    if not all([field in data for field in REQUIRED_REVIEW_FIELDS]):
        missing_fields = REQUIRED_REVIEW_FIELDS - set(data.keys())
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")

    data.update({field: None for field in OPTIONAL_REVIEW_FIELDS if field not in data})

    if not services_manager.get(id):
        raise HTTPException(status_code=404, detail="Service not found")

    older_review = ratings_manager.get(id, data["user_uuid"])
    older_review_uuid = older_review.get("uuid", None) if older_review else None
    if older_review_uuid is not None:
        if not ratings_manager.update(older_review_uuid, data["rating"], data["comment"]):
            raise HTTPException(status_code=400, detail="Error updating review")
        return {"status": "ok", "review_id": older_review_uuid}

    review_uuid = ratings_manager.insert(id, data["rating"], data["comment"], data["user_uuid"])
    if not review_uuid:
        raise HTTPException(status_code=400, detail="Error creating review")

    if not services_manager.update_rating(id, data["rating"], True):
        ratings_manager.delete(review_uuid)
        raise HTTPException(status_code=400, detail="Error updating service rating")

    return {"status": "ok", "review_id": review_uuid}

@app.delete("/{id}/reviews")
def delete_review(id: str, user_uuid: str):
    review = ratings_manager.get(id, user_uuid)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if not ratings_manager.delete(review["uuid"]):
        raise HTTPException(status_code=400, detail="Error deleting review")

    services_manager.update_rating(id, review["rating"], False)
    return {"status": "ok"}

@app.get("/{id}/reviews")
def get_reviews(id: str):
    reviews = ratings_manager.get_all(id)
    if not reviews:
        raise HTTPException(status_code=404, detail="Reviews not found")
    return {"status": "ok", "reviews": reviews}
