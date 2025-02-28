from tqdm_decorator import with_tqdm
from datetime import timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sources.youtube.youtube import Youtube
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
    
    # Convert seconds to a timedelta object
    delta = timedelta(seconds=seconds)
    
    # Format the timedelta into HH:MM:SS
    # We use strftime with hours, minutes, and seconds, ensuring hours are at least two digits
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
            time.sleep(delay)  # Wait before retrying
            attempt += 1
    print(f"Failed to delete file '{file_path}' after {retries} attempts.")
    return False

if __name__ == "__main__":
    url = input("enter yt url: ")
    yt = Youtube()
    audio_filename, length = yt.download_audio_from_url(url)
    yt.download_video(url)
    yt.get_most_replayed(url)

    transcript_filename = transcribe_audio(audio_filename)

    with open(f"{transcript_filename}.txt", 'r') as file:
        transcript = file.read()
    summary_response = asyncio.run(summarizer_chat(transcript))
    structed_summary_response = summary_response.model_dump(mode='json')
    content_id = audio_filename.split('/')[-2]

    yt.save_thumbnail(url, f"./data/youtube/{content_id}/thumbnail.png")

    with open(f"./data/youtube/{content_id}/summary.json", "w") as f:
        json.dump(structed_summary_response, f, indent=4)

    with open(f"{transcript_filename}.json", "r") as file:
        timestamped_transcript = json.load(file)
    with open(f"./data/youtube/{content_id}/summary.json", "r") as file:
        summary_data = json.load(file)
    subheadings = [item["h2"] for item in summary_data["body"]]
    documents = [f"{item['text']}" for item in timestamped_transcript]
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(documents)
    results = []
    for subheading in subheadings:
        res = search(timestamped_transcript, subheading, vectorizer, tfidf_matrix)
        results.append(res)
    with open(f"./data/youtube/{content_id}/search_results.json", 'w') as file:
        json.dump(results, file, indent=4)

    with open(f"./data/youtube/{content_id}/replay_info.json", "r") as file:
        replay_info = json.load(file)
    if replay_info is None:
        pass
    else:
        sorted_replay_info = sorted(replay_info, key=lambda x: x.get("value"), reverse=True)
        most_replayed = sorted_replay_info[1]
        try:
            yt.make_gif_most_viwed(f"./data/youtube/{content_id}/",\
                                    seconds_to_ffmpeg_timestamp(most_replayed['start_time']),\
                                    duration=str(most_replayed['end_time']-most_replayed['start_time']))
        except:
            pass

    with open(f"./data/youtube/{content_id}/search_results.json", "r") as file:
        search_results = json.load(file)
    timestamps = [[seconds_to_ffmpeg_timestamp((item[0]["start"] + item[0]["end"])/2), item[0]["id"]] for item in search_results]
    for timestamp in timestamps:
        try:
            yt.take_screenshot(f"./data/youtube/{content_id}/", timestamp[0], timestamp[1])
        except:
            continue
    remove_file_with_retry(f"./data/youtube/{content_id}/video.mp4")
    