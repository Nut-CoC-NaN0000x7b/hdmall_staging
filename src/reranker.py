import cohere
from dotenv import load_dotenv
import os
import pandas as pd
load_dotenv()
#CONSTANT

COHERE_ENDPOINT = os.getenv('COHERE_ENDPOINT')
COHERE_RERANK_API_KEY = os.getenv('COHERE_RERANK_API_KEY')


class Reranker:
    def __init__(self,
                 top_k_indexes,
                 knowledge_base,
                 index_list):
        self.reranker = cohere.Client(
            base_url = COHERE_ENDPOINT,
            api_key = COHERE_RERANK_API_KEY
        )
        self.index_list = index_list
        self.knowledge_base = knowledge_base
        self.top_k_indexes = top_k_indexes
        true_indexes = [self.index_list[index]['index'] for index in self.top_k_indexes]
        self.cohere_document = [{'Title' : f"""{self.knowledge_base.iloc[true_index]['Name']}{self.knowledge_base.iloc[true_index]['Brand']} """,
        'Content' : f"""
        {self.knowledge_base.iloc[true_index]['Name']}
        {self.knowledge_base.iloc[true_index]['Brand']}
        {self.knowledge_base.iloc[true_index]['Package Details']}
        {self.knowledge_base.iloc[true_index]['General Info']}
        """
        } for true_index in true_indexes]
        
        
    def forward(self, query: str, top_n: int):
        response = self.reranker.rerank(
            documents=self.cohere_document,
            query=query,
            rank_fields=["Content"],
            top_n=top_n,
            )
        rerank_top_k_indexes = [self.top_k_indexes[i] for i in range(len(response.results))]
        print("Reranking : Complete!")
        return rerank_top_k_indexes
