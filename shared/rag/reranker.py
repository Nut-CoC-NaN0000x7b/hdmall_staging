import cohere
from dotenv import load_dotenv
import os
import pandas as pd
import logging
load_dotenv(override=True)  # Force reload .env file to pick up new API keys
#CONSTANT

COHERE_ENDPOINT = os.getenv('COHERE_ENDPOINT')
COHERE_RERANK_API_KEY = os.getenv('COHERE_RERANK_API_KEY')

logger = logging.getLogger(__name__)

class Reranker:
    def __init__(self,
                 top_k_indexes,
                 knowledge_base,
                 index_list):
        # Debug logging for Cohere configuration
        logger.info(f"🔧 [COHERE-CONFIG] Endpoint: {COHERE_ENDPOINT}")
        logger.info(f"🔧 [COHERE-CONFIG] API Key: {COHERE_RERANK_API_KEY[:8]}...{COHERE_RERANK_API_KEY[-4:] if COHERE_RERANK_API_KEY else 'None'}")
        logger.info(f"🔧 [COHERE-CONFIG] API Key Length: {len(COHERE_RERANK_API_KEY) if COHERE_RERANK_API_KEY else 0}")
        
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
        try:
            logger.info(f"🔄 [COHERE-REQUEST] Sending rerank request with {len(self.cohere_document)} documents")
            logger.info(f"🔄 [COHERE-REQUEST] Query: {query[:50]}..." if len(query) > 50 else f"🔄 [COHERE-REQUEST] Query: {query}")
            
            response = self.reranker.rerank(
                documents=self.cohere_document,
                query=query,
                rank_fields=["Content"],
                top_n=top_n,
                )
            rerank_top_k_indexes = [self.top_k_indexes[i] for i in range(len(response.results))]
            print("Reranking : Complete!")
            return rerank_top_k_indexes
        except Exception as e:
            logger.error(f"❌ [COHERE-ERROR] Full error details: {str(e)}")
            logger.error(f"❌ [COHERE-ERROR] Error type: {type(e).__name__}")
            logger.warning(f"Cohere reranking failed: {e}")
            logger.info("Falling back to original search order without reranking")
            print("Reranking : Failed! Using original order")
            # Return original order, limited to top_n
            return self.top_k_indexes[:top_n]
