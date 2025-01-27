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

from api_container.services_nosql import Services
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

class PriceRecommender:
    def __init__(self):
        self.services_manager = Services()

    def _get_similar_services_percentiles(self, location, category):
        services = self.services_manager.get_similar_services(location, category)
        if not services:
            return None
        prices = [service['price'] for service in services]
        return {10: np.percentile(prices, 10),
                30: np.percentile(prices, 30),
                50: np.percentile(prices, 50),
                70: np.percentile(prices, 70),
                90: np.percentile(prices, 90)}
    
    def _get_provider_avg_percentile(self, provider_id, location):
        provider_categories = self.services_manager.get_provider_categories(provider_id)
        
        percentiles = []
        for category in provider_categories:
            avg_price = self.services_manager.get_provider_category_avg_price(provider_id, category)
            percentiles_category = self._get_similar_services_percentiles(location, category)
            if not percentiles_category:
                continue
            percentiles.append(next((perc for perc in percentiles_category if avg_price < percentiles_category[perc]), 90))
        
        return np.mean(percentiles)
    
    def _calculate_percentile_range(self, provider_score, service_score):
        normalize = lambda x: min(4, max(1, int(round(x))))
        avg = lambda x, y: (x + y) / 2

        provider_percentile = PERCENTILE_RANGES[normalize(provider_score)]
        if not service_score:
            return provider_percentile
        service_percentile = PERCENTILE_RANGES[normalize(service_score)]
        return (avg(provider_percentile[0], service_percentile[0]), avg(provider_percentile[1], service_percentile[1]))

    def _get_percentile_range(self, service_id):
        service = self.services_manager.get(service_id)
        provider_id = service['provider_id']

        provider_score = self.services_manager.get_provider_avg_score(provider_id)
        service_score = service['sum_rating'] / service['rating_count'] if service['rating_count'] > 0 else None

        return self._get_percentile_range(provider_score, service_score)
    
    def _get_price_by_percentile(self, percentiles, percentile):
        nearest_percentile = min(percentiles.keys(), key=lambda x: abs(x - percentile))
        return percentiles[nearest_percentile]
    
    def _get_price_range(self, min_price, price_range, provider_price):
        recommendation = RECOMMENDATION_FORMAT.copy()
        recommendation['MIN_PRICE'] = max(min_price, price_range[0])
        recommendation['MAX_PRICE'] = price_range[1]
        recommendation['MAX_PRICE'] += max(0, min_price - price_range[0])
        
        provider_price = min(provider_price, price_range[1])
        provider_price = max(provider_price, recommendation['MIN_PRICE'])
        recommendation['RECOMMENDED_PRICE'] = provider_price

        return recommendation
    
    def get_recommendation(self, service_id, cost, occupation):
        min_price = cost * OCCUPATION_OBJECTIVES.get(occupation, 0.5)
        
        percentile_range = self._get_percentile_range(service_id)
        provider_percentile = self._get_provider_avg_percentile(service_id, percentile_range)
        similar_percentiles = self._get_similar_services_percentiles(service_id)
        
        price_range = (self._get_price_by_percentile(similar_percentiles, percentile_range[0]),
                       self._get_price_by_percentile(similar_percentiles, percentile_range[1]))
        provider_price = self._get_price_by_percentile(similar_percentiles, provider_percentile)

        return self._get_price_range(min_price, price_range, provider_price)

        



                    


            
    

