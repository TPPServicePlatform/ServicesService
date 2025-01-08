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
        self.services = {score[SERVICE_INDEX]: scores.count(score) for score in scores}
    
    def _create_bipartite_graph(self, scores: List[Tuple[str, str, int]]) -> nx.DiGraph:
        bipartite_graph = nx.DiGraph()
        for score in scores:
            bipartite_graph.add_edge(score[CLIENT_INDEX], score[SERVICE_INDEX], weight=score[SCORE_INDEX])
        return bipartite_graph
    
    def get_services_rank(self) -> List[str]:
        page_rank = nx.pagerank(self.bipartite_graph)
        return {service: (page_rank[service], self.services[service]) for service in page_rank}
        