# tfidf_search.py
def search(segments, query, vectorizer, tfidf_matrix):
    """
    Search for segments matching the query using TF-IDF.

    Args:
        segments: List of transcript segments
        query: Search query string
        vectorizer: Fitted TfidfVectorizer
        tfidf_matrix: Pre-computed TF-IDF matrix for segments

    Returns:
        List of matching segments with scores
    """
    try:
        # Transform query using the same vectorizer
        query_vector = vectorizer.transform([query])

        # Calculate similarity scores
        similarity_scores = (tfidf_matrix @ query_vector.T).toarray().flatten()

        # Get matching segments with scores
        matches = []
        for idx, score in enumerate(similarity_scores):
            if score > 0:  # Only include matches with positive scores
                segment = segments[idx]
                matches.append({
                    "segment_id": idx,
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"],
                    "score": float(score)  # Convert numpy float to Python float
                })

        # Sort by score in descending order
        matches.sort(key=lambda x: x["score"], reverse=True)

        # Return top matches (e.g., top 5)
        return matches[:5]

    except Exception as e:
        print(f"Search error: {str(e)}")
        return []
