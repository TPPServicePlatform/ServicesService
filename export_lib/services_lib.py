from typing import Optional
from api_container.rentals_nosql import Rentals
from api_container.services_nosql import Services

class ServicesLib:
    def __init__(self, test_client=None):
        self.rentals = Rentals(test_client)
        self.services = Services(test_client)

    def total_rentals(self, provider_id: str) -> int:
        return self.rentals.total_rentals(provider_id)
    
    def finished_rentals(self, provider_id: str) -> int:
        return self.rentals.finished_rentals(provider_id)
    
    def avg_rating(self, provider_id: str) -> Optional[dict]:
        ratings = self.services.avg_rating(provider_id)
        if not ratings:
            return None
        
        sum_rating = sum(rating['sum_rating'] for rating in ratings)
        num_ratings = sum(rating['num_ratings'] for rating in ratings)
        return {'avg_rating': sum_rating / num_ratings, 'num_ratings': num_ratings}