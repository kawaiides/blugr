import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from yt_dlp.dependencies import certifi

from app import transcriptions
from summarize import generate_text
from tqdm_decorator import with_tqdm
from datetime import timedelta, datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from youtube import Youtube
# from transcribe import transcribe_audio
# from summarize import summarizer_chat
from tfidf_search import search
import asyncio
import json
import os
import time

load_dotenv()


def get_mongo_client():
    try:
        uri = os.getenv("MONGO_DB_KEY")
        if not uri:
            raise ValueError("MongoDB URI not found in environment variables")

        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=5000,
            ssl=True,
            ssl_ca_certs=certifi.where(),
            connect=True,
            connectTimeoutMS=30000,
            retryWrites=True,
            w='majority'
        )

        # Test connection
        client.admin.command('ping')
        print("MongoDB connection successful")
        return client
    except Exception as e:
        print(f"MongoDB connection failed: {str(e)}")
        return None


def save_to_mongodb(content_id, url, transcript_data, summary_data):
    client = get_mongo_client()
    if not client:
        return False

    try:
        db = client['blugr']  # Your database name
        collection = db['generated-texts']  # Your collection name

        # Prepare document
        document = {
            "content_id": content_id,
            "url": url,
            "transcript": transcript_data,
            "summary": summary_data,
            "created_at": datetime.utcnow(),
            "status": "completed"
        }

        # Use update_one with upsert to avoid duplicates
        result = collection.update_one(
            {"content_id": content_id},  # filter
            {"$set": document},  # update
            upsert=True  # create if doesn't exist
        )

        if result.upserted_id:
            print(f"Inserted new document with ID: {result.upserted_id}")
        else:
            print(f"Updated existing document for content_id: {content_id}")

        return True

    except Exception as e:
        print(f"Error saving to MongoDB: {str(e)}")
        return False

    finally:
        client.close()


def seconds_to_ffmpeg_timestamp(seconds):
    if seconds < 0:
        raise ValueError("Seconds must be non-negative")

    delta = timedelta(seconds=seconds)
    return f"{delta // timedelta(hours=1):02d}:{delta.seconds // 60 % 60:02d}:{delta.seconds % 60:02d}"


def remove_file_with_retry(file_path, retries=5, delay=60):
    """Attempt to remove a file, retrying if it fails due to the file being in use."""
    attempt = 0
    while attempt < retries:
        try:
            os.remove(file_path)
            print(f"File '{file_path}' removed successfully.")
            return True
        except PermissionError as e:
            print(f"PermissionError: {e}. Retrying... ({attempt + 1}/{retries})")
            time.sleep(delay)
            attempt += 1
    print(f"Failed to delete file '{file_path}' after {retries} attempts.")
    return False


# main.py
async def process_youtube_url(url, log_queue=None):
    def log(message):
        if log_queue:
            log_queue.write(message)
        print(message)

    try:
        log("Initializing YouTube processing...")
        yt = Youtube()

        log("Downloading audio...")
        audio_filename, length = yt.download_audio_from_url(url)

        if not os.path.exists(audio_filename):
            raise FileNotFoundError(f"Audio file was not downloaded: {audio_filename}")

        log(f"Downloaded audio: {audio_filename}")

        log("Downloading video...")
        yt.download_video(url)

        log("Getting most replayed segments...")
        yt.get_most_replayed(url)

        log("Transcribing audio...")
        transcript_result = await transcriptions(audio_filename)

        # Extract content ID safely
        content_id = os.path.basename(os.path.dirname(audio_filename))
        base_path = f"./data/youtube/{content_id}"
        os.makedirs(base_path, exist_ok=True)

        # Ensure we have a string for the transcript
        transcript_text = transcript_result["transcription"]
        if isinstance(transcript_text, list):
            transcript_text = ' '.join(transcript_text)

        # Save full text transcript
        with open(f"{base_path}/transcript.txt", 'w', encoding='utf-8') as file:
            file.write(transcript_text)

        # Save timestamped segments
        with open(f"{base_path}/transcript.json", 'w', encoding='utf-8') as file:
            json.dump(transcript_result["segments"], file, indent=2, ensure_ascii=False)

        log(f"Transcript saved: {base_path}/transcript.txt")
        log(f"Timestamped segments saved: {base_path}/transcript.json")

        log("Reading transcript for summary...")
        with open(f"{base_path}/transcript.txt", 'r', encoding='utf-8') as file:
            transcript = file.read()

        log("Generating summary using Gemini API...")
        # Make request to the local FastAPI endpoint
        response = await generate_text(transcript)

        summary_response = response
        print(summary_response)

        log("Writing summary to file...")
        with open(f"{base_path}/summary.json", "w", encoding='utf-8') as f:
            json.dump(summary_response, f, indent=4)

        log("Processing transcript and summary data...")
        with open(f"{base_path}/transcript.json", "r", encoding='utf-8') as file:
            timestamped_transcript = json.load(file)

        transcript_data = {
            "full_text": transcript_text,
            "segments": transcript_result["segments"]
        }

        summary_data = {
            "generated_text": summary_response["generated_text"],
            "summary_json": json.loads(summary_response["generated_text"])
        }

        # Save to MongoDB
        log("Saving to MongoDB...")
        mongodb_success = save_to_mongodb(
            content_id=content_id,
            url=url,
            transcript_data=transcript_data,
            summary_data=summary_data
        )

        if mongodb_success:
            log("Successfully saved to MongoDB")
        else:
            log("Failed to save to MongoDB")
        # Process subheadings and perform TF-IDF analysis
        summary_data = json.loads(summary_response["generated_text"])
        subheadings = [item["h2"] for item in summary_data["body"]]
        documents = [f"{item['text']}" for item in timestamped_transcript]

        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(documents)

        log("Performing search for each subheading...")
        results = []
        for subheading in subheadings:
            log(f"Processing subheading: {subheading}")
            res = search(timestamped_transcript, subheading, vectorizer, tfidf_matrix)
            results.append(res)

        log("Writing search results to file...")
        with open(f"{base_path}/search_results.json", 'w', encoding='utf-8') as file:
            json.dump(results, file, indent=4)

        log("Processing completed successfully")
        return True

    except Exception as e:
        log(f"Error processing URL {url}: {str(e)}")
        return False

if __name__ == "__main__":
    url = input("Enter YouTube URL: ")
    asyncio.run(process_youtube_url(url))
