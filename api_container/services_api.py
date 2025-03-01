from lib.price_recommender import PriceRecommender
from lib.review_summarizer import ReviewSummarizer
from lib.interest_prediction import InterestPredictor
from lib.trending import TrendingAnaliser
from lib.utils import time_to_string, validate_location, verify_fields
import operator
import re
from typing import Optional, Tuple
from services_nosql import Services
from rentals_nosql import Rentals
from ratings_nosql import Ratings
from additionals_nosql import Additionals
import mongomock
import logging as logger
import time
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys
import os
import stripe

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'lib')))

time_start = time.time()

logger.basicConfig(format='%(levelname)s: %(asctime)s - %(message)s',
                   stream=sys.stdout, level=logger.INFO)
logger.info("Starting the app")
load_dotenv()

DEBUG_MODE = os.getenv("DEBUG_MODE", "False").title() == "True"
if DEBUG_MODE:
    logger.getLogger().setLevel(logger.DEBUG)
logger.info("DEBUG_MODE: " + str(DEBUG_MODE))

app = FastAPI(
    title="Services API",
    description="API for services management",
    version="1.0.0",
    root_path=os.getenv("ROOT_PATH")
)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET")

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
    review_summarizer = ReviewSummarizer()
    price_recommender = PriceRecommender()
else:
    services_manager = Services()
    ratings_manager = Ratings()
    rentals_manager = Rentals()
    additionals_manager = Additionals()
    review_summarizer = ReviewSummarizer()
    price_recommender = PriceRecommender()

REQUIRED_CREATE_FIELDS = {"service_name", "provider_id",
                          "category", "price", "location", "max_distance"}
REQUIRED_LOCATION_FIELDS = {"longitude", "latitude"}
OPTIONAL_CREATE_FIELDS = {"description"}
VALID_UPDATE_FIELDS = {"service_name",
                       "description", "category", "price", "hidden"}
REQUIRED_REVIEW_FIELDS = {"rating", "user_uuid"}
OPTIONAL_REVIEW_FIELDS = {"comment"}
REQUIRED_RENTAL_FIELDS = {"provider_id", "client_id",
                          "start_date", "end_date", "location"}
OPTIONAL_RENTAL_FIELDS = {"additionals"}
VALID_RENTAL_STATUS = {"PENDING", "ACCEPTED",
                       "REJECTED", "CANCELLED", "FINISHED"}
DEFAULT_RENTAL_STATUS = "PENDING"
REQUIRED_ADDITIONAL_FIELDS = {"name", "provider_id", "description", "price"}
VALID_UPDATE_ADDITIONAL_FIELDS = {"name", "description", "price"}
REQUIRED_PAYMENT_FIELDS = {"amount", "currency", "description"}
MIN_RATING = 1  # stars
MAX_RATING = 5  # stars

TRENDING_TIME = 30  # days
TRENDING_MIN_REVIEWS = 0.1  # 10% of the average reviews
TRENDING_SERVICES = "trending_services"
TRENDING_LAST_UPDATE = "last_update"

PERSONALIZED_TIME = 30 * 3  # days (3 months)

AVAILABLE_OCCUPATIONS = {"LOW", "MEDIUM", "HIGH"}

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

    uuid = services_manager.insert(data["service_name"], data["provider_id"], data["description"],
                                   data["category"], data["price"], data["location"], data["max_distance"])
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
    update = {key: value for key,
              value in body.items() if key in VALID_UPDATE_FIELDS}
    verify_fields(set(), VALID_UPDATE_FIELDS, body)

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
    uuid: Optional[str] = Query(None),
    min_avg_rating: Optional[float] = Query(0.0)
):
    if keywords:
        keywords = keywords.split(",")

    if not client_location:
        raise HTTPException(
            status_code=400, detail="Client location is required")
    client_location = validate_location(
        client_location, REQUIRED_LOCATION_FIELDS)

    results = services_manager.search(
        client_location, keywords, provider_id, min_price, max_price, uuid, hidden, min_avg_rating)
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

    if not services_manager.get(id):
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

    review_summarizer.update_service(id)

    return {"status": "ok", "review_id": review_uuid}


@app.delete("/{id}/reviews")
def delete_review(id: str, user_uuid: str):
    review = ratings_manager.get(id, user_uuid)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if not ratings_manager.delete(review["uuid"]):
        raise HTTPException(status_code=400, detail="Error deleting review")

    services_manager.update_rating(id, review["rating"], False)
    review_summarizer.update_service(id)
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

    if not services_manager.get(id):
        raise HTTPException(status_code=404, detail="Service not found")

    if not data["end_date"] > data["start_date"]:
        raise HTTPException(
            status_code=400, detail="End date must be greater than start date")

    client_location = validate_location(
        data["location"], REQUIRED_LOCATION_FIELDS)
    additionals = data.get("additionals", [])
    rental_uuid = rentals_manager.insert(id, data["provider_id"], data["client_id"],
                                         data["start_date"], data["end_date"], client_location, DEFAULT_RENTAL_STATUS, additionals)
    if not rental_uuid:
        raise HTTPException(status_code=400, detail="Error creating rental")
    return {"status": "ok", "rental_id": rental_uuid}


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
    return {"status": "ok"}


@app.get("{id}/paymentlink/{rental_id}")
async def create_payment_link(id: str, rental_id: str, body: dict):
    data = {key: value for key, value in body.items(
    ) if key in REQUIRED_PAYMENT_FIELDS}

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "T-Shirt",
                            "description": "Comfortable cotton T-shirt",
                        },
                        "unit_amount": 1000,
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
        )
        return {"url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bookings")
def search_bookings(
    rental_id: Optional[str] = Query(None),
    service_id: Optional[str] = Query(None),
    provider_id: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_start_date: Optional[str] = Query(None),
    max_start_date: Optional[str] = Query(None),
    min_end_date: Optional[str] = Query(None),
    max_end_date: Optional[str] = Query(None)
):
    start_date = {"MIN": min_start_date, "MAX": max_start_date}
    end_date = {"MIN": min_end_date, "MAX": max_end_date}
    results = rentals_manager.search(
        rental_id, service_id, provider_id, client_id, status, start_date, end_date)
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

    return price_recommender.get_recommendation(service_id, cost, occupation)


def _fetch_recent_ratings(client_location, max_time):
    if not client_location:
        raise HTTPException(
            status_code=400, detail="Client location is required")
    client_location = validate_location(
        client_location, REQUIRED_LOCATION_FIELDS)
    all_available_services = [service["uuid"] for service in services_manager.search(
        client_location, hidden=False)]
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
