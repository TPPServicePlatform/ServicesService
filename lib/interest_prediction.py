from typing import List, Tuple
import networkx as nx
import operator
import random

CLIENT_INDEX = 0
SERVICE_INDEX = 1

class InterestPredictor:
    def __init__(self, reviews: List[Tuple[str, str]], user_id: str):
        self.bipartite_graph = self._create_bipartite_graph(reviews)
        self.services = {r[SERVICE_INDEX]: reviews.count(r) for r in reviews}
        self.user_id = user_id
        self._ebunch = self._get_ebunch(self.bipartite_graph, self.user_id)

    def _create_bipartite_graph(self, reviews: List[Tuple[str, str]]) -> nx.Graph:
        bipartite_graph = nx.Graph()
        # for r in reviews:
        #     bipartite_graph.add_edge(r[CLIENT_INDEX], r[SERVICE_INDEX])
        bipartite_graph.add_edges_from((r[CLIENT_INDEX], r[SERVICE_INDEX]) for r in reviews)
        return bipartite_graph
    
    def _get_ebunch(self, graph: nx.Graph, user_id: str) -> List[Tuple[str, str]]:
        # ebunch = []
        # for service in self.services:
        #     if not graph.has_edge(user_id, service):
        #         ebunch.append((user_id, service))
        # return ebunch
        return [(user_id, service) for service in self.services if not graph.has_edge(user_id, service)]
    
    def get_interest_prediction(self) -> List[str]:
        predictions = nx.preferential_attachment(self.bipartite_graph, ebunch=self._ebunch)
        return {service: score for (user, service, score) in predictions}
