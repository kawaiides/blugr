from app import transcriptions
from tqdm_decorator import with_tqdm
from datetime import timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from youtube import Youtube
from transcribe import transcribe_audio
from summarize import summarizer_chat
from tfidf_search import search
import asyncio
import json
import os
import time


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

        log("Generating summary...")
        summary_response = await summarizer_chat(transcript)
        structed_summary_response = summary_response.model_dump(mode='json')

        log("Writing summary to file...")
        with open(f"{base_path}/summary.json", "w", encoding='utf-8') as f:
            json.dump(structed_summary_response, f, indent=4)

        log("Processing transcript and summary data...")
        with open(f"{base_path}/transcript.json", "r", encoding='utf-8') as file:
            timestamped_transcript = json.load(file)
        with open(f"{base_path}/summary.json", "r", encoding='utf-8') as file:
            summary_data = json.load(file)

        # Process subheadings and perform TF-IDF analysis
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
