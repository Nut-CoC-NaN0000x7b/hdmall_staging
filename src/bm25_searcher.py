"""
This .py file is about keyword search branch
in our hybrid RAG architecture
we use BM25 algorithm for this part
"""
from pythainlp.tokenize import word_tokenize
from rank_bm25 import BM25Okapi
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json

class BM25Retriever:
    def __init__(self,
                 tokens_file,
                 k1: float = 1.5,
                 b: float = 0.75):
        """
        Initialize BM25 with pre-tokenized documents
        """
        # Load tokenized documents
        data = tokens_file
        self.tokenized_docs = data["tokens"]
        self.original_indices = data["indices"]
        self.total_docs = len(self.original_indices)

        # Initialize BM25
        self.bm25 = BM25Okapi(self.tokenized_docs, k1=k1, b=b)

        # Create a set of all document indices for quick reference
        self.all_indices = set(self.original_indices)

        #print(f"Initialized BM25 with {self.total_docs} documents")

    def _tokenize_query(self, query: str) -> List[str]:
        """Tokenize search query"""
        query = ' '.join(query.split())
        tokens = word_tokenize(query, engine="newmm")
        return [token for token in tokens if token.strip()]

    def forward(self, query: str) -> Dict[int, int]:
        """
        Get ranks for ALL documents, including those with zero scores

        Args:
            query: Search query

        Returns:
            Dictionary of {doc_idx: rank} for ALL documents
        """
        query_tokens = self._tokenize_query(query)

        # Initialize scores for all documents
        scores = {idx: 0.0 for idx in range(self.total_docs)}

        if query_tokens:
            # Get BM25 scores
            bm25_scores = self.bm25.get_scores(query_tokens)

            # Map scores to original indices
            for idx, score in enumerate(bm25_scores):
                orig_idx = self.original_indices[idx]
                scores[orig_idx] = score

        # Sort by score to get ranks
        sorted_items = sorted(
            scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Assign ranks (same score = same rank)
        rank_dict = {}
        current_rank = 1
        previous_score = None

        for idx, (doc_idx, score) in enumerate(sorted_items):
            if score != previous_score:
                current_rank = idx + 1
            rank_dict[doc_idx] = current_rank
            previous_score = score
        print('Lexical search : Complete!')
        return rank_dict

    def search(self, query: str, k: int = None) -> Dict[int, float]:
        """
        Get scores for ALL documents

        Args:
            query: Search query
            k: Ignored (kept for compatibility)

        Returns:
            Dictionary of {doc_idx: score} for ALL documents
        """
        query_tokens = self._tokenize_query(query)

        # Initialize scores for all possible indices
        scores = {idx: 0.0 for idx in range(self.total_docs)}

        if query_tokens:
            # Get BM25 scores
            bm25_scores = self.bm25.get_scores(query_tokens)

            # Map scores to original indices
            for idx, score in enumerate(bm25_scores):
                orig_idx = self.original_indices[idx]
                scores[orig_idx] = score

        return scores

        