"""
precios de servicios similares:
    obeter los percentiles 10, 30, 50, 70 y 90 de los precios de los servicios similares
    (similar = misma zona y categoria)

rango de precios en los que se situa el proveedor:
    por cada categoria de serivicios que brinda el proveedor:
        obtener el percentil en el que se encuentra (usando el precio promedio de los servicios de esa categoria)
        (percentil = 10, 30, 50, 70, 90)
    obtener el percentil promedio para asociarlo al vendedor

costo estimado por el proveedor:
    input dado por el proveedor

ocupación del proveedor:
    input dado por el proveedor y:
        BAJA: se quiere promover la ocupación -> ganancias de al menos el 30% sobre el costo
        MEDIA: se quiere mantener la ocupación -> ganancias de al menos el 50% sobre el costo
        ALTA: se quiere mantener la ocupación -> ganancias de al menos el 90% sobre el costo

nivel de fiabilidad:
    tomar el score promedio de las reviews del proveedor y:
        si el score es mayor a 4 -> percentil minimo 50 (no hay maximo)
        si el score es mayor a 3 -> percentil entre 30 y 70
        si el score es menor a 2 -> percentil entre 10 y 50
        si el score es menor a 1 -> percentil hasta 30 (no hay minimo)
    tomar el score promedio de las reviews del servicio (si tiene) y:
        si el score es mayor a 4 -> percentil minimo 50 (no hay maximo)
        si el score es mayor a 3 -> percentil entre 30 y 70
        si el score es menor a 2 -> percentil entre 10 y 50
        si el score es menor a 1 -> percentil hasta 30 (no hay minimo)
"""

from services_nosql import Services
from lib.sentence_similarity import SentenceComparator
import numpy as np

PERCENTILE_RANGES = {
    4: (50, 100),
    3: (30, 70),
    2: (10, 50),
    1: (0, 30)
}

OCCUPATION_OBJECTIVES = {
    "LOW": 1.3,
    "MEDIUM": 1.5,
    "HIGH": 1.9
}

RECOMMENDATION_FORMAT = {
    "MIN_PRICE": -1,
    "MAX_PRICE": -1,
    "RECOMMENDED_PRICE": -1,
}

MINIMUM_SIMILARITY = 0.5

# TODO: Test this class


class PriceRecommender:
    def __init__(self, test_client=None):
        self.services_manager = Services(test_client=test_client)
        self.sentences_comparator = SentenceComparator()

    def _get_similar_services_percentiles(self, location, category):
        services = self.services_manager.get_similar_services(
            location, category)
        if not services:
            return None
        prices = [service['price'] for service in services]
        return {10: np.percentile(prices, 10),
                30: np.percentile(prices, 30),
                50: np.percentile(prices, 50),
                70: np.percentile(prices, 70),
                90: np.percentile(prices, 90)}

    def _get_provider_avg_percentile(self, provider_id, location):
        provider_categories = self.services_manager.get_provider_categories(
            provider_id)

        percentiles = []
        for category in provider_categories:
            avg_price = self.services_manager.get_provider_category_avg_price(
                provider_id, category)
            percentiles_category = self._get_similar_services_percentiles(
                location, category)
            if not percentiles_category:
                continue
            percentiles.append(next(
                (perc for perc in percentiles_category if avg_price < percentiles_category[perc]), 90))

        return np.mean(percentiles)

    def _calculate_percentile_range(self, provider_score, service_score):
        def normalize(x): return min(4, max(1, int(round(x))))
        def avg(x, y): return (x + y) / 2

        provider_percentile = PERCENTILE_RANGES[normalize(provider_score)]
        if not service_score:
            return provider_percentile
        service_percentile = PERCENTILE_RANGES[normalize(service_score)]
        return (avg(provider_percentile[0], service_percentile[0]), avg(provider_percentile[1], service_percentile[1]))

    def _get_percentile_range(self, service_id):
        service = self.services_manager.get(service_id)
        provider_id = service['provider_id']

        provider_score = self.services_manager.get_provider_avg_score(
            provider_id)
        service_score = service['sum_rating'] / \
            service['rating_count'] if service['rating_count'] > 0 else None

        return self._calculate_percentile_range(provider_score, service_score)

    def _get_price_by_percentile(self, percentiles, percentile):
        nearest_percentile = min(
            percentiles.keys(), key=lambda x: abs(x - percentile))
        return percentiles[nearest_percentile]

    def _get_price_range(self, min_price, price_range, provider_price, similar_services_avg_price):
        def avg(x, y): return (x + y) / 2

        recommendation = RECOMMENDATION_FORMAT.copy()
        recommendation['MIN_PRICE'] = max(min_price, price_range[0])
        recommendation['MAX_PRICE'] = price_range[1]
        recommendation['MAX_PRICE'] += max(0, min_price - price_range[0])

        if similar_services_avg_price > recommendation['MAX_PRICE']:
            recommendation['MAX_PRICE'] = similar_services_avg_price
        else:
            similar_services_avg_price = max(
                similar_services_avg_price, recommendation['MIN_PRICE'])

        provider_price = min(provider_price, price_range[1])
        provider_price = max(provider_price, recommendation['MIN_PRICE'])

        recommendation['RECOMMENDED_PRICE'] = avg(
            provider_price, similar_services_avg_price)

        return recommendation

    def _get_avg_similar_services_price(self, service_id, suspended_providers):
        service = self.services_manager.get(service_id)
        location = service['location']
        location = {'longitude': location['coordinates'][0],
                    'latitude': location['coordinates'][1]}
        score = service['sum_rating'] / \
            service['rating_count'] if service['rating_count'] > 0 else None
        category = service['category']
        
        similar_services = self.services_manager.search(
            suspended_providers, location=location, category=category, min_avg_rating=score-0.5, max_avg_rating=score+0.5)
        similar_services = {
            service['service_name']: service['price'] for service in similar_services}

        similar_names = self.sentences_comparator.compare(
            service['service_name'], list(similar_services.keys()))
        similar_names = [
            name for name, similarity in similar_names if similarity > MINIMUM_SIMILARITY]
        similar_prices = [similar_services[name] for name in similar_names]

        return np.mean(similar_prices)

    def get_recommendation(self, service_id, cost, occupation, suspended_providers):
        min_price = cost * OCCUPATION_OBJECTIVES.get(occupation, 0.5)

        percentile_range = self._get_percentile_range(service_id)
        provider_percentile = self._get_provider_avg_percentile(
            service_id, percentile_range)
        similar_percentiles = self._get_similar_services_percentiles(
            service_id)

        price_range = (self._get_price_by_percentile(similar_percentiles, percentile_range[0]),
                       self._get_price_by_percentile(similar_percentiles, percentile_range[1]))
        provider_price = self._get_price_by_percentile(
            similar_percentiles, provider_percentile)
        similar_services_avg_price = self._get_avg_similar_services_price(
            service_id, suspended_providers)

        return self._get_price_range(min_price, price_range, provider_price, similar_services_avg_price)
