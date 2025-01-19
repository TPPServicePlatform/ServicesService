from typing import Optional
from imported_lib.ServicesService.lib.exportable_rentals_nosql import Rentals
from imported_lib.ServicesService.lib.exportable_services_nosql import Services
from imported_lib.ServicesService.lib.exportable_ratings_nosql import Ratings

class ServicesLib:
    def __init__(self, test_client=None):
        self.rentals = Rentals(test_client)
        self.services = Services(test_client)
        self.ratings = Ratings(test_client)

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
    
    def get_recent_ratings(self, max_delta_days: int) -> Optional[list[tuple[str, str, float]]]:
        results = self.ratings.get_recent(max_delta_days)
        if not results:
            return None
        return [(f"U{r['user_uuid']}", f"S{r['service_uuid']}", float(r['rating'])) for r in results]

    def get_available_services(self, location: str) -> Optional[list[str]]:
        return self.services.get_available_services(location)   