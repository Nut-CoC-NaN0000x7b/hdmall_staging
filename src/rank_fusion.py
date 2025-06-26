#reciprocal rank fusion



def compute_rrf(rank_BM25, rank_semantics,mask,k=60, alpha=0.5):
    """
    Compute Reciprocal Rank Fusion scores for two ranking dictionaries.

    Args:
        rank_BM25 (dict): Dictionary of {original_index: rank} for BM25 rankings
        rank_semantics (dict): Dictionary of {original_index: rank} for semantic rankings
        k (int): Constant to prevent division by zero and smooth the impact of high rankings

    Returns:
        dict: Dictionary of {original_index: final_score} sorted by score in descending order
    """
    # Initialize dictionary to store RRF scores
    rrf_scores = {}

    # Get all unique document indices
    all_docs = set(rank_BM25.keys()).union(set(rank_semantics.keys()))

    #geo masking #TODO could add more masking
    all_docs = [doc_id for i, doc_id in enumerate(all_docs) if mask[i] == 1]

    # Compute RRF scores for each document
    for doc_id in all_docs:
        # Get ranks (default to max possible rank + 1 if document not in ranking)
        max_rank = max(len(rank_BM25), len(rank_semantics)) + 1
        rank1 = rank_BM25.get(doc_id, max_rank)
        rank2 = rank_semantics.get(doc_id, max_rank)

        # Compute RRF score: RRF(d) = Σ 1/(k + r(d))
        score1 = (1 / (k + rank1)) * (1-alpha)
        score2 = (1 / (k + rank2)) * alpha
        rrf_scores[doc_id] = score1 + score2

    # Sort by score in descending order
    sorted_results = dict(sorted(rrf_scores.items(),
                               key=lambda x: x[1],
                               reverse=True))

    return sorted_results

# Example usage:
def get_top_k(rrf_scores, k=10):
    """
    Get top-k results from RRF scores.

    Args:
        rrf_scores (dict): Dictionary of {original_index: score}
        k (int): Number of top results to return

    Returns:
        dict: Dictionary of top-k {original_index: score}
    """
    print("Rank fusion : Complete!")
    return dict(list(rrf_scores.items())[:k])