import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from yt_dlp.dependencies import certifi

from s3 import S3CRUD
from whisper_wrapper import WhisperTranscriber
from summarize import generate_text
from tqdm_decorator import with_tqdm
from datetime import timedelta, datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from youtube import Youtube
from tfidf_search import search
import asyncio
import json
import os
import time

load_dotenv()
s3_handler = S3CRUD(bucket_name='blooogerai')

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


def save_to_mongodb(content_id, url, transcript_data, summary_data, search_data=None):
    client = get_mongo_client()
    if not client:
        return False

    try:
        db = client['blugr']
        collection = db['generated-texts']

        document = {
            "content_id": content_id,
            "url": url,
            "transcript": {
                "full_text": transcript_data["full_text"],
                "segments": transcript_data["segments"],
                "metadata": transcript_data.get("metadata", {})
            },
            "summary": {
                "raw_response": summary_data["raw_response"],
                "parsed_summary": summary_data["parsed_summary"]
            },
            "search_results": search_data if search_data else [],
            "metadata": {
                "created_at": datetime.utcnow(),
                "status": "completed",
                "version": "1.0",
                "has_search_results": bool(search_data)
            }
        }

        result = collection.update_one(
            {"content_id": content_id},
            {"$set": document},
            upsert=True
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
        transcriber = WhisperTranscriber(model_size='base')
        transcript_result = transcriber.transcribe(audio_filename)

        # Extract content ID safely
        content_id = os.path.basename(os.path.dirname(audio_filename))
        base_path = f"./data/youtube/{content_id}"
        os.makedirs(base_path, exist_ok=True)

        # Save full text transcript
        with open(f"{base_path}/transcript.txt", 'w', encoding='utf-8') as file:
            file.write(transcript_result["transcription"])

        # Save detailed transcription data
        with open(f"{base_path}/transcript.json", 'w', encoding='utf-8') as file:
            json.dump({
                "segments": transcript_result["segments"],
                "metadata": {
                    "language": transcript_result["language"],
                    "language_probability": transcript_result["language_probability"]
                }
            }, file, indent=2, ensure_ascii=False)

        # Generate SRT subtitles
        transcriber.generate_srt(
            transcript_result["segments"],
            f"{base_path}/subtitles.srt"
        )

        log(f"Transcript saved: {base_path}/transcript.txt")
        log(f"Detailed transcription saved: {base_path}/transcript.json")
        log(f"Subtitles saved: {base_path}/subtitles.srt")

        log("Generating summary using Gemini API...")
        response = await generate_text(transcript_result["transcription"])
        summary_response = response

        log("Writing summary to file...")
        with open(f"{base_path}/summary.json", "w", encoding='utf-8') as f:
            json.dump(summary_response, f, indent=4)

        # Parse the summary JSON
        try:
            summary_json = json.loads(summary_response["generated_text"])
        except json.JSONDecodeError as e:
            log(f"Warning: Could not parse summary JSON: {e}")
            summary_json = {
                "title": "Summary",
                "body": [{"h2": "Content", "text": summary_response["generated_text"]}]
            }

        # Process subheadings and perform TF-IDF analysis
        subheadings = [item["h2"] for item in summary_json["body"]]
        documents = [segment["text"] for segment in transcript_result["segments"]]

        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(documents)

        # Process subheadings and perform TF-IDF analysis
        log("Performing TF-IDF analysis and search...")
        search_results = []

        try:
            subheadings = [item["h2"] for item in summary_json["body"]]
            documents = [segment["text"] for segment in transcript_result["segments"]]

            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(documents)

            log("Performing search for each subheading...")
            for subheading in subheadings:
                log(f"Processing subheading: {subheading}")
                # Get matches for this subheading
                matches = search(transcript_result["segments"], subheading, vectorizer, tfidf_matrix)

                search_result = {
                    "subheading": subheading,
                    "matches": matches,
                    "timestamp": datetime.utcnow().isoformat(),
                    "match_count": len(matches)
                }
                search_results.append(search_result)
                log(f"Found {len(matches)} matches for '{subheading}'")

            # Generate screenshots for search results
            log("Generating screenshots for search results...")
            video_path = f"./data/youtube/{content_id}/"
            screenshots_dir = os.path.join(video_path, 'screenshots')
            os.makedirs(screenshots_dir, exist_ok=True)

            for result in search_results:
                match = result["matches"][0]
                try:
                    start_time = seconds_to_ffmpeg_timestamp(match["start"])
                    screenshot_id = f"{result['subheading'].replace(' ', '_')}_0"

                    log(f"Taking screenshot for timestamp {start_time} (ID: {screenshot_id})")

                    yt.take_screenshot(
                        video_path=video_path,
                        timestamp=start_time,
                        id=screenshot_id
                    )

                    local_screenshot_path = os.path.join(screenshots_dir, f"{screenshot_id}.png")
                    s3_path = f"screenshots/{content_id}/{screenshot_id}.png"

                    # Upload to S3
                    if os.path.exists(local_screenshot_path):
                        log(f"Uploading screenshot to S3: {s3_path}")
                        s3_handler.upload_file(local_screenshot_path, s3_path)

                        # Update the match data with S3 URL
                        s3_url = f"https://blooogerai.s3.amazonaws.com/{s3_path}"
                        match["screenshot_path"] = s3_url
                        match["local_screenshot_path"] = f"screenshots/{screenshot_id}.png"
                        # Optionally remove local file after upload
                        # os.remove(local_screenshot_path)
                    else:
                        log(f"Screenshot file not found: {local_screenshot_path}")
                        match["screenshot_path"] = None
                except Exception as e:
                    log(f"Error taking screenshot for {start_time}: {str(e)}")
                    match["screenshot_path"] = None

            # Calculate total matches
            total_matches = sum(result["match_count"] for result in search_results)

            # Prepare search data structure
            search_data = {
                "results": search_results,
                "metadata": {
                    "total_subheadings": len(subheadings),
                    "total_matches": total_matches,
                    "processed_at": datetime.utcnow().isoformat(),
                    "subheadings": subheadings,
                    "statistics": {
                        "average_matches_per_subheading": total_matches / len(subheadings) if subheadings else 0,
                        "subheadings_with_matches": sum(1 for result in search_results if result["matches"]),
                        "coverage_percentage": (sum(1 for result in search_results if result["matches"]) / len(
                            subheadings)) * 100 if subheadings else 0
                    }
                }
            }

            # Save search results locally
            log("Writing search results to file...")
            with open(f"{base_path}/search_results.json", 'w', encoding='utf-8') as file:
                json.dump(search_data, file, indent=4)

        except Exception as e:
            log(f"Warning: Error in search processing: {str(e)}")
            search_data = {
                "results": [],
                "metadata": {
                    "total_subheadings": len(subheadings) if 'subheadings' in locals() else 0,
                    "total_matches": 0,
                    "processed_at": datetime.utcnow().isoformat(),
                    "subheadings": subheadings if 'subheadings' in locals() else [],
                    "error": str(e)
                }
            }

        # Prepare data for MongoDB
        transcript_data = {
            "full_text": transcript_result["transcription"],
            "segments": transcript_result["segments"],
            "metadata": {
                "language": transcript_result["language"],
                "language_probability": transcript_result["language_probability"]
            }
        }

        summary_data = {
            "raw_response": summary_response["generated_text"],
            "parsed_summary": summary_json
        }

        # Save to MongoDB
        log("Saving to MongoDB...")
        mongodb_success = save_to_mongodb(
            content_id=content_id,
            url=url,
            transcript_data=transcript_data,
            summary_data=summary_data,
            search_data=search_data
        )

        if mongodb_success:
            log("Successfully saved to MongoDB")
        else:
            log("Failed to save to MongoDB")

        log("Processing completed successfully")
        return True

    except Exception as e:
        log(f"Error processing URL {url}: {str(e)}")
        return False


if __name__ == "__main__":
    url = input("Enter YouTube URL: ")
    asyncio.run(process_youtube_url(url))