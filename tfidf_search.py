import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Function to search
def search(data, query, vectorizer, tfidf_matrix, top_n=1):
    # Transform the query into TF-IDF vector
    query_vector = vectorizer.transform([query])
    
    # Compute cosine similarity between query and documents
    similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
    
    # Sort by similarity and get top N results
    top_indices = similarities.argsort()[-top_n:][::-1]
    
    # Return the top N results
    results = []
    for idx in top_indices:
        results.append({
            "id": data[idx]["id"],
            "start": data[idx]["start"],
            "end": data[idx]["end"],
            "text": data[idx]["text"],
            "query": query,
            "similarity": similarities[idx]
        })
    return results

if __name__ == "__main__":
    path = input("input video path: ")
    summary_path = path + '/summary.json'
    timestamped_transcript_path = path + '/transcript.json'

    with open(f"{timestamped_transcript_path}", "r") as file:
        timestamped_transcript = json.load(file)
    with open(f"{summary_path}", "r") as file:
        summary_data = json.load(file)
    
    subheadings = [item["h2"] for item in summary_data["body"]]
    documents = [f"{item['text']}" for item in timestamped_transcript]

    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(documents)

    results = []
    for subheading in subheadings:
        res = search(timestamped_transcript, subheading, vectorizer, tfidf_matrix)
        results.append(res)

    with open(f"{path}/search_results.json", 'w') as file:
        json.dump(results, file, indent=4)
