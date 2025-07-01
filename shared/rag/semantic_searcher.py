from openai import AzureOpenAI
from azure.ai.inference import EmbeddingsClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import numpy as np
import os

#CONSTANT
load_dotenv()
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_VERSION = os.getenv('AZURE_OPENAI_VERSION')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')

COHERE_ENDPOINT = os.getenv('COHERE_ENDPOINT_NEW')
COHERE_API_KEY = os.getenv('COHERE_API_KEY_NEW')



class SemanticRetriever:
    def __init__(self, embedding_matrix):
        self.emb_matrix = embedding_matrix
        self.text_embedding = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        self.embeddings_client = EmbeddingsClient(
            endpoint=COHERE_ENDPOINT,
            credential=AzureKeyCredential(COHERE_API_KEY)
        )
        
    def get_embedding(self, text, model='text-embedding-3-large'):
        text = text.replace("\n"," ")
        embedding_vector = self.text_embedding.embeddings.create(
            input=[text],
            model=model
            ).data[0].embedding
        
        return embedding_vector
    
    def forward(self, query):
        #embedding and dot product 
        query_embedding = self.get_embedding(query)
        semantic_score = np.dot(self.emb_matrix, query_embedding)
        
        #get {indices : rank} dict
        score_dict = {doc_index: score for doc_index, score in enumerate(semantic_score)}
        rank_dict_semantic = {index: rank+1 for rank, (index, score) in enumerate(sorted(score_dict.items(), key=lambda x: x[1], reverse=True))}
        rank_dict_semantic = dict(sorted(rank_dict_semantic.items()))
        print('Semantic search : Complete!')
        return rank_dict_semantic
    
    def forward_cohere(self, query):
        response = self.embeddings_client.embed(
            model="embed-v-4-0",
            input=[query]
        )
        q_embedding = response['data'][0]['embedding']
        semantic_score = np.dot(self.emb_matrix, q_embedding)
        score_dict = {doc_index: score for doc_index, score in enumerate(semantic_score)}
        rank_dict_semantic = {index: rank+1 for rank, (index, score) in enumerate(sorted(score_dict.items(), key=lambda x: x[1], reverse=True))}
        rank_dict_semantic = dict(sorted(rank_dict_semantic.items()))
        print('Semantic search : Complete!')
        return rank_dict_semantic
        
        
    