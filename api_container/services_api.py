import datetime
from mobile_token_nosql import MobileToken, send_notification
from lib.price_recommender import PriceRecommender
from lib.review_summarizer import ReviewSummarizer
from lib.interest_prediction import InterestPredictor
from lib.trending import TrendingAnaliser
from lib.utils import sentry_init, time_to_string, validate_location, verify_fields, create_repetitions_list, validate_date, get_actual_time
import operator
import re
from typing import Optional, Tuple
from services_nosql import Services
from rentals_nosql import Rentals
from ratings_nosql import Ratings
from additionals_nosql import Additionals
from reminders_nosql import Reminders, save_reminders, daily_notification_sender
import mongomock
import logging as logger
import time
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from imported_lib.SupportService.support_lib import SupportLib
from dotenv import load_dotenv
import sys
import os
from multiprocessing import Process

time_start = time.time()

logger.basicConfig(format='%(levelname)s: %(asctime)s - %(message)s',
                   stream=sys.stdout, level=logger.INFO)
logger.info("Starting the app")
load_dotenv()

DEBUG_MODE = os.getenv("DEBUG_MODE", "False").title() == "True"
if DEBUG_MODE:
    logger.getLogger().setLevel(logger.DEBUG)
logger.info("DEBUG_MODE: " + str(DEBUG_MODE))

sentry_init()

app = FastAPI(
    title="Services API",
    description="API for services management",
    version="1.0.0",
    root_path=os.getenv("ROOT_PATH")
)

if not os.getenv('TESTING'):
    daily_notification_sender_process = Process(
        target=daily_notification_sender)
    daily_notification_sender_process.start()

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
    rentals_manager = Rentals(test_client=client)
    additionals_manager = Additionals(test_client=client)
    review_summarizer = ReviewSummarizer(test_client=client)
    price_recommender = PriceRecommender(test_client=client)
    support_lib = SupportLib(test_client=client)
    reminders_manager = Reminders(test_client=client)
    mobile_token_manager = MobileToken(test_client=client)
else:
    services_manager = Services()
    ratings_manager = Ratings()
    rentals_manager = Rentals()
    additionals_manager = Additionals()
    review_summarizer = ReviewSummarizer()
    price_recommender = PriceRecommender()
    support_lib = SupportLib()
    reminders_manager = Reminders()
    mobile_token_manager = MobileToken()

REQUIRED_CREATE_FIELDS = {"service_name", "provider_id",
                          "category", "price", "location", "max_distance"}
REQUIRED_LOCATION_FIELDS = {"longitude", "latitude"}
OPTIONAL_CREATE_FIELDS = {"description", "estimated_duration", "images"}
VALID_UPDATE_FIELDS = {"service_name",
                       "description", "category", "price", "hidden", "max_distance", "estimated_duration"}
REQUIRED_REVIEW_FIELDS = {"rating", "user_uuid"}
OPTIONAL_REVIEW_FIELDS = {"comment"}

REQUIRED_RENTAL_FIELDS = {"provider_id", "client_id",
                          "date", "location"}
OPTIONAL_RENTAL_FIELDS = {"additionals", "repeat", "max_repeats"}
VALID_RENTAL_STATUS = {"PENDING", "ACCEPTED",
                       "REJECTED", "CANCELLED", "FINISHED"}

DEFAULT_RENTAL_STATUS = "PENDING"
REQUIRED_ADDITIONAL_FIELDS = {"name", "provider_id", "description", "price"}
VALID_UPDATE_ADDITIONAL_FIELDS = {"name", "description", "price"}
REQUIRED_PAYMENT_FIELDS = {"amount", "currency", "description"}
MIN_RATING = 1  # stars
MAX_RATING = 5  # stars

VALID_REPETITIONS = {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}

TRENDING_TIME = 30  # days
TRENDING_MIN_REVIEWS = 0.1  # 10% of the average reviews
TRENDING_SERVICES = "trending_services"
TRENDING_LAST_UPDATE = "last_update"

PERSONALIZED_TIME = 30 * 3  # days (3 months)

AVAILABLE_OCCUPATIONS = {"LOW", "MEDIUM", "HIGH"}

VALID_CATEGORIES = ["Repair", "Cleaning", "Cooking", "Childcare", "Petcare",
                    "Gardening", "Stilist", "Healthcare", "Education", "Entertainment", "Other"]

starting_duration = time_to_string(time.time() - time_start)
logger.info(f"Services API started in {starting_duration}")

# TODO: (General) -> Create tests for each endpoint && add the required checks in each endpoint


@app.post("/create")
def create(body: dict):
    data = {key: value for key, value in body.items(
    ) if key in REQUIRED_CREATE_FIELDS or key in OPTIONAL_CREATE_FIELDS}
    verify_fields(REQUIRED_CREATE_FIELDS, OPTIONAL_CREATE_FIELDS, data)

    if not isinstance(data["location"], dict):
        raise HTTPException(
            status_code=400, detail="Location must be a dictionary")
    verify_fields(REQUIRED_LOCATION_FIELDS, set(), data["location"])

    data.update(
        {field: None for field in OPTIONAL_CREATE_FIELDS if field not in data})

    if data["category"] not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400, detail=f"Invalid category, must be one of: {', '.join(VALID_CATEGORIES)}")

    uuid = services_manager.insert(data["service_name"], data["provider_id"], data["description"],
                                   data["category"], data["price"], data["location"], data["max_distance"], data["estimated_duration"], data["images"])
    if not uuid:
        raise HTTPException(status_code=400, detail="Error creating service")
    return {"status": "ok", "service_id": uuid}


@app.get("/categories")
def get_categories():
    return {"status": "ok", "categories": VALID_CATEGORIES}

@app.get("/hiring_report/{provider_id}")
def get_hiring_report(provider_id: str):
    report = rentals_manager.get_hiring_report(provider_id)
    if not report:
        raise HTTPException(status_code=404, detail="No report found")
    return {"status": "ok", "report": report}

@app.put("/certification/add/{service_id}/{certification_id}")
def add_certification(service_id: str, certification_id: str):
    if not services_manager.get(service_id):
        raise HTTPException(status_code=404, detail="Service not found")

    if not services_manager.add_certification(service_id, certification_id):
        raise HTTPException(
            status_code=400, detail="Error adding certification to service")
    return {"status": "ok"}


@app.delete("/certification/delete/{service_id}/{certification_id}")
def remove_certification(service_id: str, certification_id: str):
    if not services_manager.get(service_id):
        raise HTTPException(status_code=404, detail="Service not found")

    if not services_manager.remove_certification(service_id, certification_id):
        raise HTTPException(
            status_code=400, detail="Error removing certification from service")
    return {"status": "ok"}


@app.delete("/{id}")
def delete(id: str):
    if not services_manager.delete(id):
        raise HTTPException(status_code=404, detail="Service not found")
    return {"status": "ok"}


@app.delete("/delete_all/{provider_id}")
def delete_all(provider_id: str):
    if not services_manager.delete_all(provider_id):
        raise HTTPException(status_code=404, detail="Services not found")
    return {"status": "ok"}


@app.put("/{id}")
def update(id: str, body: dict):
    logger.info(f"body: {body}")
    update = {key: value for key,
              value in body.items() if key in VALID_UPDATE_FIELDS}
    verify_fields(set(), VALID_UPDATE_FIELDS, body)

    if not services_manager.get(id):
        raise HTTPException(status_code=404, detail="Service not found")

    if "category" in update and update["category"] not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400, detail=f"Invalid category, must be one of: {', '.join(VALID_CATEGORIES)}")

    if not services_manager.update(id, update):
        raise HTTPException(status_code=400, detail="Error updating service")
    return {"status": "ok"}


@app.get("/provider/{provider_id}")
def get_by_provider(provider_id: str):
    results = services_manager.get_by_provider(provider_id)
    if not results:
        raise HTTPException(status_code=404, detail="No results found")
    return {"status": "ok", "results": results}


@app.get("/search")
def search(
    client_location: str = Query(...),
    keywords: Optional[str] = Query(None),
    provider_id: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    hidden: Optional[bool] = Query(None),
    uuid: Optional[str] = Query(None),
    min_avg_rating: Optional[float] = Query(0.0),
    category: Optional[str] = Query(None)
):
    if keywords:
        keywords = keywords.split(",")

    if not client_location:
        raise HTTPException(
            status_code=400, detail="Client location is required")
    client_location = validate_location(
        client_location, REQUIRED_LOCATION_FIELDS)

    suspended_providers = support_lib.get_all_users_suspended()
    results = services_manager.search(suspended_providers,
                                      client_location, keywords, provider_id, min_price, max_price, uuid, hidden, min_avg_rating, category)
    if not results:
        raise HTTPException(status_code=404, detail="No results found")
    return {"status": "ok", "results": results}


@app.put("/{id}/reviews")
def review(id: str, body: dict):
    data = {key: value for key, value in body.items(
    ) if key in REQUIRED_REVIEW_FIELDS or key in OPTIONAL_REVIEW_FIELDS}
    verify_fields(REQUIRED_REVIEW_FIELDS, OPTIONAL_REVIEW_FIELDS, data)

    data.update(
        {field: None for field in OPTIONAL_REVIEW_FIELDS if field not in data})

    service = services_manager.get(id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    older_review = ratings_manager.get(id, data["user_uuid"])
    older_review_uuid = older_review.get(
        "uuid", None) if older_review else None
    if older_review_uuid is not None:
        if not ratings_manager.update(older_review_uuid, data["rating"], data["comment"]):
            raise HTTPException(
                status_code=400, detail="Error updating review")
        return {"status": "ok", "review_id": older_review_uuid}

    if not MIN_RATING <= data["rating"] <= MAX_RATING:
        raise HTTPException(
            status_code=400, detail=f"Rating must be between {MIN_RATING} and {MAX_RATING}")

    review_uuid = ratings_manager.insert(
        id, data["rating"], data["comment"], data["user_uuid"])
    if not review_uuid:
        raise HTTPException(status_code=400, detail="Error creating review")

    if not services_manager.update_rating(id, data["rating"], True):
        ratings_manager.delete(review_uuid)

        raise HTTPException(
            status_code=400, detail="Error updating service rating")

    if not os.getenv('TESTING'):
        review_summarizer.add_service(id)

    service_name = service["service_name"]
    provider_id = service["provider_id"]
    send_notification(mobile_token_manager, provider_id, f"New review!",
                      f"Go and check your service {service_name} to see the new review!")

    return {"status": "ok", "review_id": review_uuid}


@app.delete("/{id}/reviews")
def delete_review(id: str, user_uuid: str):
    review = ratings_manager.get(id, user_uuid)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if not ratings_manager.delete(review["uuid"]):
        raise HTTPException(status_code=400, detail="Error deleting review")

    services_manager.update_rating(id, review["rating"], False)
    if not os.getenv('TESTING'):
        review_summarizer.add_service(id)
    return {"status": "ok"}


@app.get("/{id}/reviews")
def get_reviews(id: str):
    reviews = ratings_manager.get_all(id)
    if not reviews:
        raise HTTPException(status_code=404, detail="Reviews not found")
    return {"status": "ok", "reviews": reviews}


@app.post("/{id}/book")
def book(id: str, body: dict):
    data = {key: value for key, value in body.items(
    ) if key in REQUIRED_RENTAL_FIELDS or key in OPTIONAL_RENTAL_FIELDS}
    verify_fields(REQUIRED_RENTAL_FIELDS, OPTIONAL_RENTAL_FIELDS, data)

    service = services_manager.get(id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    date = validate_date(data["date"])
    if date < datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'):
        raise HTTPException(
            status_code=400, detail="Date must be greater than current date")

    client_location = validate_location(
        data["location"], REQUIRED_LOCATION_FIELDS)
    additionals = data.get("additionals", [])

    if ("repeat" in data) != ("max_repeats" in data):
        raise HTTPException(
            status_code=400, detail="Both repeat and max_repeats must be provided")

    if "repeat" in data and data["repeat"] not in VALID_REPETITIONS:
        raise HTTPException(
            status_code=400, detail=f"Invalid repetition, must be one of: {', '.join(VALID_REPETITIONS)}")
    if "max_repeats" in data and data["max_repeats"] < 2:
        raise HTTPException(
            status_code=400, detail="Max repeats must be greater than 1")

    if "repeat" in data:
        repetitions = create_repetitions_list(
            data["repeat"], data["max_repeats"], data["date"])
        info_key = "rental_ids"
    else:
        repetitions = [date]
        info_key = "rental_id"

    rental_uuids = []
    estimated_duration = service["estimated_duration"]
    for repetition_date in repetitions:
        rental_uuid = rentals_manager.insert(
            id, data["provider_id"], data["client_id"], repetition_date, estimated_duration, client_location, DEFAULT_RENTAL_STATUS, additionals)
        if not rental_uuid:
            for uuid in rental_uuids:
                rentals_manager.delete(uuid)
            raise HTTPException(
                status_code=400, detail="Error creating rentals")
        rental_uuids.append(rental_uuid)
        
        rental_date = repetition_date.split(" ")[0]
        service_name = service["service_name"]
        save_reminders(reminders_manager, rental_date,
                       data["provider_id"], service_name, rental_uuid)
        save_reminders(reminders_manager, rental_date,
                       data["client_id"], service_name, rental_uuid)

    provider_id = services_manager.get(id)["provider_id"]
    service_name = services_manager.get(id)["service_name"]
    send_notification(mobile_token_manager, provider_id, f"New booking!",
                      f"Go and check your calendar to see the new booking for your service {service_name}!")

    return {"status": "ok", info_key: rental_uuids if len(rental_uuids) > 1 else rental_uuids[0]}


@app.put("/{id}/book/{rental_id}")
def update_booking(id: str, rental_id: str, body: dict):
    if "status" not in body:
        raise HTTPException(status_code=400, detail="Missing status field")
    new_status = body["status"]
    if new_status not in VALID_RENTAL_STATUS:
        raise HTTPException(status_code=400, detail="Invalid status")

    if new_status == DEFAULT_RENTAL_STATUS:
        raise HTTPException(
            status_code=400, detail="Status must be different from the default")

    if not services_manager.get(id):
        raise HTTPException(status_code=404, detail="Service not found")

    if not rentals_manager.get(rental_id):
        raise HTTPException(status_code=404, detail="Rental not found")

    if not rentals_manager.update_status(rental_id, new_status):
        raise HTTPException(status_code=400, detail="Error updating rental")

    service_name = services_manager.get(id)["service_name"]
    provider_id = services_manager.get(id)["provider_id"]
    client_id = rentals_manager.get(rental_id)["client_id"]
    send_notification(mobile_token_manager, client_id, f"Booking status update!",
                      f"The status of your booking for the service {service_name} has been updated to {new_status}!")
    send_notification(mobile_token_manager, provider_id, f"Booking status update!",
                      f"The status of the booking for your service {service_name} has been updated to {new_status}!")

    if new_status in {"rejected", "cancelled"}:
        rentals_manager.delete_rental_reminders(rental_id)
    return {"status": "ok"}

@app.put("/{id}/book/{rental_id}/estimated_duration")
def update_estimated_duration(id: str, rental_id: str, body: dict):
    if "estimated_duration" not in body:
        raise HTTPException(status_code=400, detail="Missing estimated_duration field")
    new_duration = body["estimated_duration"]

    if not services_manager.get(id):
        raise HTTPException(status_code=404, detail="Service not found")

    if not rentals_manager.get(rental_id):
        raise HTTPException(status_code=404, detail="Rental not found")

    if not rentals_manager.update_estimated_duration(rental_id, new_duration):
        raise HTTPException(status_code=400, detail="Error updating rental")

    return {"status": "ok"}


@app.get("/bookings")
def search_bookings(
    rental_id: Optional[str] = Query(None),
    service_id: Optional[str] = Query(None),
    provider_id: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_date: Optional[str] = Query(None),
    max_date: Optional[str] = Query(None)
):
    results = rentals_manager.search(
        rental_id, service_id, provider_id, client_id, status, min_date, max_date)
    if not results:
        raise HTTPException(status_code=404, detail="No results found")

    for result in results:
        if "additionals" in result:
            additionals = [additionals_manager.get(
                additional_id)["additional_name"] for additional_id in result["additionals"]]
            result["additionals"] = additionals
    return {"status": "ok", "results": results}


@app.post("/additionals/create")
def create_additional(body: dict):
    data = {key: value for key, value in body.items(
    ) if key in REQUIRED_ADDITIONAL_FIELDS}
    verify_fields(REQUIRED_ADDITIONAL_FIELDS, set(), data)

    uuid = additionals_manager.insert(
        data["name"], data["provider_id"], data["description"], data["price"])
    if not uuid:
        raise HTTPException(
            status_code=400, detail="Error creating additional")
    return {"status": "ok", "additional_id": uuid}


@app.get("/{id}")
def getbyId(id: str):
    result = services_manager.get(id)
    if not result:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"status": "ok", "result": result}


@app.put("/additionals/{additional_id}")
def update_additional(additional_id: str, body: dict):
    update = {key: value for key, value in body.items(
    ) if key in VALID_UPDATE_ADDITIONAL_FIELDS}
    verify_fields(set(), VALID_UPDATE_ADDITIONAL_FIELDS, body)

    if not additionals_manager.get(additional_id):
        raise HTTPException(status_code=404, detail="Additional not found")

    if not additionals_manager.update(additional_id, update):
        raise HTTPException(
            status_code=400, detail="Error updating additional")
    return {"status": "ok"}


@app.delete("/additionals/{additional_id}")
def delete_additional(additional_id: str):
    if not additionals_manager.delete(additional_id):
        raise HTTPException(status_code=404, detail="Additional not found")
    return {"status": "ok"}


@app.get("/additionals/provider/{provider_id}")
def get_additionals_by_provider(provider_id: str):
    results = additionals_manager.get_by_provider(provider_id)
    if not results:
        raise HTTPException(status_code=404, detail="No results found")
    return {"status": "ok", "results": results}


@app.put("/additionals/{additional_id}/add/{service_id}")
def add_additional_to_service(service_id: str, additional_id: str):
    if not services_manager.get(service_id):
        raise HTTPException(status_code=404, detail="Service not found")

    if not additionals_manager.get(additional_id):
        raise HTTPException(status_code=404, detail="Additional not found")

    if not services_manager.add_additional(service_id, additional_id):
        raise HTTPException(
            status_code=400, detail="Error adding additional to service")
    return {"status": "ok"}


@app.delete("/additionals/{additional_id}/delete/{service_id}")
def remove_additional_from_service(service_id: str, additional_id: str):
    if not services_manager.get(service_id):
        raise HTTPException(status_code=404, detail="Service not found")

    if not additionals_manager.get(additional_id):
        raise HTTPException(status_code=404, detail="Additional not found")

    if not services_manager.remove_additional(service_id, additional_id):
        raise HTTPException(
            status_code=400, detail="Error removing additional from service")
    return {"status": "ok"}


@app.get("/additionals/service/{service_id}")
def get_service_additionals(service_id: str):
    results = services_manager.get_additionals(service_id)
    if not results:
        raise HTTPException(status_code=404, detail="No results found")
    additionals = [additionals_manager.get(
        additional_id) for additional_id in results]
    return {"status": "ok", "results": additionals}


@app.get("/trending")
def get_trending_services(
    max_services: int,
    offset: int = 0,
    client_location: str = Query(...),
):
    recent_ratings = _fetch_recent_ratings(client_location, TRENDING_TIME)
    ratings_list = [(f"U{r['user_uuid']}", f"S{r['service_uuid']}", float(
        r['rating'])) for r in recent_ratings]

    trending_data = _get_trending_data(ratings_list)
    trending_services = trending_data[offset:offset+max_services]
    remaining_services = max(len(trending_data) - (offset + max_services), 0)
    return {"status": "ok", "results": trending_services, "remaining_services": remaining_services}


@app.get("/recommendations/{user_id}")
def get_personalized_recommendations(
    user_id: str,
    max_services: int,
    offset: int = 0,
    client_location: str = Query(...),
):
    recent_ratings = _fetch_recent_ratings(client_location, PERSONALIZED_TIME)
    ratings_list = [(f"U{r['user_uuid']}", f"S{r['service_uuid']}")
                    for r in recent_ratings]

    predictor = InterestPredictor(ratings_list, user_id)
    predictions = predictor.get_interest_prediction()
    predictions = sorted(predictions.items(),
                         key=operator.itemgetter(1), reverse=True)
    recommendations = predictions[offset:offset+max_services]
    remaining_services = max(len(predictions) - (offset + max_services), 0)
    return {"status": "ok", "results": recommendations, "remaining_services": remaining_services}


@app.get("/services/{service_id}/price_recommendation")
def get_price_recommendation(service_id: str, cost: float, occupation: str):
    if not services_manager.get(service_id):
        raise HTTPException(status_code=404, detail="Service not found")
    if not occupation in AVAILABLE_OCCUPATIONS:
        raise HTTPException(
            status_code=400, detail="Invalid occupation, must be one of: " + ", ".join(AVAILABLE_OCCUPATIONS))

    suspended_providers = support_lib.get_all_users_suspended()
    return price_recommender.get_recommendation(service_id, cost, occupation, suspended_providers)


def _fetch_recent_ratings(client_location, max_time):
    if not client_location:
        raise HTTPException(
            status_code=400, detail="Client location is required")
    client_location = validate_location(
        client_location, REQUIRED_LOCATION_FIELDS)
    suspended_providers = support_lib.get_all_users_suspended()
    all_available_services = [service["uuid"] for service in services_manager.search(
        suspended_providers, client_location, hidden=False)]
    if not all_available_services:
        raise HTTPException(status_code=404, detail="No services found")

    recent_ratings = ratings_manager.get_recent(
        max_time, all_available_services)
    return recent_ratings


def _get_trending_data(reviews_list):
    trending_services = TrendingAnaliser(reviews_list).get_services_rank()
    avg_reviews = sum([service["REVIEWS_COUNT"]
                      for service in trending_services.values()]) / len(trending_services)
    min_reviews = avg_reviews * TRENDING_MIN_REVIEWS

    filtered_services = {service: data for service, data in trending_services.items(
    ) if data["REVIEWS_COUNT"] >= min_reviews}
    return sorted(filtered_services.items(), key=lambda x: x[1]["TRENDING_SCORE"], reverse=True)
