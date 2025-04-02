from typing import List, Tuple
import networkx as nx
import operator
import random

CLIENT_INDEX = 0
SERVICE_INDEX = 1
SCORE_INDEX = 2

class TrendingAnaliser:
    def __init__(self, scores: List[Tuple[str, str, int]]):
        self.bipartite_graph = self._create_bipartite_graph(scores)
        self.services_graph = self._create_services_graph()
        self.services = {score[SERVICE_INDEX]: scores.count(score) for score in scores}
    
    def _create_bipartite_graph(self, scores: List[Tuple[str, str, int]]) -> nx.DiGraph:
        bipartite_graph = nx.DiGraph()
        for score in scores:
            bipartite_graph.add_edge(score[CLIENT_INDEX], score[SERVICE_INDEX], weight=score[SCORE_INDEX])
        return bipartite_graph
    
    def _create_services_graph(self) -> nx.DiGraph:
        services_graph = nx.DiGraph()
        clients = set()
        for edge in self.bipartite_graph.edges():
            client, service = edge
            if not services_graph.has_node(service):
                services_graph.add_node(service)
            clients.add(client)
        for client in clients:
            all_services = list(self.bipartite_graph.neighbors(client))
            for service1 in all_services:
                service1_weight = self.bipartite_graph[client][service1]["weight"]
                for service2 in all_services:
                    service2_weight = self.bipartite_graph[client][service2]["weight"]
                    if service1 == service2:
                        continue
                    if not services_graph.has_edge(service1, service2):
                        services_graph.add_edge(service1, service2, weight=service2_weight)
                    else:
                        services_graph[service1][service2]["weight"] += service2_weight
        return services_graph
    
    def get_services_rank(self) -> List[str]:
        page_rank = nx.pagerank(self.services_graph, alpha=0.85)
        return {service: {"TRENDING_SCORE": page_rank[service], "REVIEWS_COUNT": self.services[service]} for service in self.services if service in page_rank}
