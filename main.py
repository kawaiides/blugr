import requests
from dotenv import load_dotenv
from pymongo import MongoClient
from yt_dlp.dependencies import certifi
import re
import glob
import logging

from s3 import S3CRUD
from whisper_wrapper import WhisperTranscriber
from summarize import generate_text, generate_script
from tqdm_decorator import with_tqdm
from datetime import timedelta, datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from youtube import Youtube
from tfidf_search import search
import asyncio
import json
import os
import time
from affiliates import resolve_affiliate_link, extract_product_info
from prompts import affiliate_prompt, blog_prompt, reel_prompt, reel_script_prompt
from typing import List, Dict
from video_transcriber import VideoTranscriber

# from video_processor import VideoProcessor

load_dotenv()
s3_handler = S3CRUD(bucket_name='blooogerai')

from TTS.api import TTS
import torch
from torch.serialization import StorageType, _get_restore_location
import numpy as np

from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip
import subprocess

import os
import subprocess
import ffmpeg
import math

async def run_command(cmd: List[str]) -> None:
    """Helper function to run shell commands with async support"""
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"Command failed: {stderr.decode()}")

def format_time(seconds):

    hours = math.floor(seconds / 3600)
    seconds %= 3600
    minutes = math.floor(seconds / 60)
    seconds %= 60
    milliseconds = round((seconds - math.floor(seconds)) * 1000)
    seconds = math.floor(seconds)
    formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:01d},{milliseconds:03d}"

    return formatted_time

def generate_subtitle_file(language, segments):
    subtitle_file = f"sub.{language}.srt"
    text = ""
    for index, segment in enumerate(segments):
        print(segment)
        segment_start = format_time(segment['start'])
        segment_end = format_time(segment['end'])
        text += f"{str(index+1)} \n"
        text += f"{segment_start} --> {segment_end} \n"
        text += f"{segment['text']} \n"
        text += "\n"
        
    f = open(subtitle_file, "w")
    f.write(text)
    f.close()

    return subtitle_file

def add_subtitle_to_video(soft_subtitle, subtitle_file,  subtitle_language, input_video):
    input_video_name = os.path.basename(input_video).split(".")[0]
    video_input_stream = ffmpeg.input(input_video)
    subtitle_input_stream = ffmpeg.input(subtitle_file)
    output_video = f"output-{input_video_name}.mp4"
    subtitle_track_title = subtitle_file.replace(".srt", "")

    if soft_subtitle:
        stream = ffmpeg.output(
            video_input_stream, subtitle_input_stream, output_video, **{"c": "copy", "c:s": "mov_text"},
            **{"metadata:s:s:0": f"language={subtitle_language}",
            "metadata:s:s:0": f"title={subtitle_track_title}"}
        )
        ffmpeg.run(stream, overwrite_output=True)

async def create_final_reel(reel_id: str, base_dir: str = "data/reel") -> None:
    """Create final video reels with synchronized audio narration"""
    
    # Setup paths
    base_dir = os.path.abspath(base_dir)
    reel_dir = os.path.join(base_dir, reel_id)
    clips_dir = os.path.join(reel_dir, "clips")
    final_dir = os.path.join(reel_dir, "final")
    voiceover_dir = os.path.join(reel_dir, "voiceovers")
    
    os.makedirs(final_dir, exist_ok=True)

    async def process_variant(clips, variant_name, combined_audio):
        """Helper to process long or fast variants"""
        if not clips:
            return
        print("processing variant...")
        # Create concat list
        list_file = os.path.join(final_dir, f"{variant_name}_list.txt")
        with open(list_file, 'w') as f:
            for clip in clips:
                f.write(f"file '{os.path.abspath(clip)}'\n")

        concat_output = os.path.join(final_dir, f"temp_{variant_name}.mp4")
        concat_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            '-fflags', '+genpts',
            '-reset_timestamps', '1',
            concat_output
        ]
        await run_command(concat_cmd)
        
        # Get video duration
        duration_cmd = [
            'ffprobe', 
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            concat_output
        ]
        process = await asyncio.create_subprocess_exec(
            *duration_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()
        video_duration = float(stdout.decode().strip())

        # Get audio duration
        audio_duration = 0
        if os.path.exists(combined_audio):
            duration_cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                combined_audio
            ]
            process = await asyncio.create_subprocess_exec(
                *duration_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            audio_duration = float(stdout.decode().strip())

        final_output = os.path.join(final_dir, f"{variant_name}.mp4")

        if audio_duration > video_duration:
            # Get video FPS for looping
            fps_cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=r_frame_rate',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                concat_output
            ]
            process = await asyncio.create_subprocess_exec(
                *fps_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            fps_str = stdout.decode().strip()
            numerator, denominator = map(int, fps_str.split('/'))
            fps = numerator / denominator
            size = int(fps * video_duration)
            loop_count = int(audio_duration // video_duration)

            mix_cmd = [
                'ffmpeg', '-y',
                '-i', concat_output,
                '-i', combined_audio,
                '-filter_complex', f'''
                    [0:v]loop=loop={loop_count}:size={size},
                    setpts=N/FRAME_RATE/TB,
                    trim=duration={audio_duration}[v];
                    [1:a]aformat=sample_rates=44100:channel_layouts=stereo[a]
                ''',
                '-map', '[v]',
                '-map', '[a]',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-b:a', '192k',
                final_output
            ]
        else:
            mix_cmd = [
                'ffmpeg', '-y',
                '-i', concat_output,
                '-i', combined_audio,
                '-filter_complex', '[1:a]aformat=sample_rates=44100:channel_layouts=stereo[a]',
                '-map', '0:v:0',
                '-map', '[a]',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                final_output
            ]

        await run_command(mix_cmd)
        vt = VideoTranscriber(final_output, combined_audio)
        vt.transcribe_video()
        vt.create_video(f"final_{variant_name}.mp4")

        # Mix with audio (using existing duration logic)
        final_output = os.path.join(final_dir, f"{variant_name}.mp4")
        return final_output

    try:
        # Load summary.json to get subheadings
        with open(os.path.join(reel_dir, "summary.json")) as f:
            summary = json.load(f)
            summary_data = summary["generated_text"]
            subheadings = [re.sub(r'[^\w\-_\. ]', '',section["Subheading"].replace(' ', '_')).replace(" ", "_").replace("__", "_") for section in summary_data[0]["body"]]
            print(subheadings)
        # Combine all narrations
        narration_files = []
        for num in range(5):
            narration_path = os.path.join(voiceover_dir, f"narration_{num}.wav")
            if os.path.exists(narration_path):
                narration_files.append(narration_path)
        
        
        combined_audio = os.path.join(final_dir, "combined_narration.wav")
        if narration_files:
            audio_filter = "".join([f"[{i}:a]" for i in range(len(narration_files))])
            audio_cmd = [
                'ffmpeg', '-y',
                *sum([['-i', f] for f in narration_files], []),
                '-filter_complex', f"{audio_filter}concat=n={len(narration_files)}:v=0:a=1[outa]",
                '-map', '[outa]',
                combined_audio
            ]
            await run_command(audio_cmd)
        long_clips = []
        fast_clips = []
        print(subheadings)
        for subheading in subheadings:
            # Find all clips for this subheading
            clip_pattern = os.path.join(clips_dir, f"{subheading}_*.mp4")
            matching_clips = glob.glob(clip_pattern)
            print(f"Matching: {matching_clips}")
            if not matching_clips:
                continue

            # Get clip durations
            clip_durations = []
            for clip in matching_clips:
                duration_cmd = [
                    'ffprobe', '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    clip
                ]
                process = await asyncio.create_subprocess_exec(
                    *duration_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await process.communicate()
                duration = float(stdout.decode().strip())
                clip_durations.append((clip, duration))

            # Sort by duration and select extremes
            sorted_clips = sorted(clip_durations, key=lambda x: x[1])
            print(sorted_clips)
            long_clips.append(sorted_clips[-1][0])  # Longest
            fast_clips.append(sorted_clips[0][0])   # Shortest
        print(long_clips, fast_clips)
        # Process variants
        clip_pattern = os.path.join(clips_dir, f"*.mp4")
        matching_clips = glob.glob(clip_pattern)
        print(f"Matching: {matching_clips}")
        if matching_clips:
            await process_variant(matching_clips, "all", combined_audio)
        await process_variant(long_clips, "long", combined_audio)
        await process_variant(fast_clips, "fast", combined_audio)


        # Process each sequence
        # for num in range(5):
        #     clip_pattern = os.path.join(clips_dir, f"*_{num}.mp4")
        #     all_clips = sorted(glob.glob(clip_pattern))
            
        #     if not all_clips:
        #         print(f"No clips found for sequence {num}, skipping...")
        #         continue

        #     # Concatenate clips
        #     list_file = os.path.join(final_dir, f"clips_{num}.txt")
        #     with open(list_file, 'w') as f:
        #         for path in all_clips:
        #             escaped = path.replace("'", "'\\''")
        #             f.write(f"file '{escaped}'\n")

        #     concat_output = os.path.join(final_dir, f"temp_{num}.mp4")
        #     concat_cmd = [
        #         'ffmpeg', '-y',
        #         '-f', 'concat',
        #         '-safe', '0',
        #         '-i', list_file,
        #         '-c', 'copy',
        #         '-fflags', '+genpts',
        #         '-reset_timestamps', '1',
        #         concat_output
        #     ]
        #     await run_command(concat_cmd)
            
        #     # Get video duration
        #     duration_cmd = [
        #         'ffprobe', 
        #         '-v', 'error',
        #         '-show_entries', 'format=duration',
        #         '-of', 'default=noprint_wrappers=1:nokey=1',
        #         concat_output
        #     ]
        #     process = await asyncio.create_subprocess_exec(
        #         *duration_cmd,
        #         stdout=asyncio.subprocess.PIPE,
        #         stderr=asyncio.subprocess.PIPE
        #     )
        #     stdout, _ = await process.communicate()
        #     video_duration = float(stdout.decode().strip())

        #     # Get audio duration
        #     audio_duration = 0
        #     if os.path.exists(combined_audio):
        #         duration_cmd = [
        #             'ffprobe',
        #             '-v', 'error',
        #             '-show_entries', 'format=duration',
        #             '-of', 'default=noprint_wrappers=1:nokey=1',
        #             combined_audio
        #         ]
        #         process = await asyncio.create_subprocess_exec(
        #             *duration_cmd,
        #             stdout=asyncio.subprocess.PIPE,
        #             stderr=asyncio.subprocess.PIPE
        #         )
        #         stdout, _ = await process.communicate()
        #         audio_duration = float(stdout.decode().strip())

        #     final_output = os.path.join(final_dir, f"{num}.mp4")

        #     if audio_duration > video_duration:
        #         # Get video FPS for looping
        #         fps_cmd = [
        #             'ffprobe',
        #             '-v', 'error',
        #             '-select_streams', 'v:0',
        #             '-show_entries', 'stream=r_frame_rate',
        #             '-of', 'default=noprint_wrappers=1:nokey=1',
        #             concat_output
        #         ]
        #         process = await asyncio.create_subprocess_exec(
        #             *fps_cmd,
        #             stdout=asyncio.subprocess.PIPE,
        #             stderr=asyncio.subprocess.PIPE
        #         )
        #         stdout, _ = await process.communicate()
        #         fps_str = stdout.decode().strip()
        #         numerator, denominator = map(int, fps_str.split('/'))
        #         fps = numerator / denominator
        #         size = int(fps * video_duration)
        #         loop_count = int(audio_duration // video_duration)

        #         mix_cmd = [
        #             'ffmpeg', '-y',
        #             '-i', concat_output,
        #             '-i', combined_audio,
        #             '-filter_complex', f'''
        #                 [0:v]loop=loop={loop_count}:size={size},
        #                 setpts=N/FRAME_RATE/TB,
        #                 trim=duration={audio_duration}[v];
        #                 [1:a]aformat=sample_rates=44100:channel_layouts=stereo[a]
        #             ''',
        #             '-map', '[v]',
        #             '-map', '[a]',
        #             '-c:v', 'libx264',
        #             '-c:a', 'aac',
        #             '-b:a', '192k',
        #             final_output
        #         ]
        #     else:
        #         mix_cmd = [
        #             'ffmpeg', '-y',
        #             '-i', concat_output,
        #             '-i', combined_audio,
        #             '-filter_complex', '[1:a]aformat=sample_rates=44100:channel_layouts=stereo[a]',
        #             '-map', '0:v:0',
        #             '-map', '[a]',
        #             '-c:v', 'copy',
        #             '-c:a', 'aac',
        #             '-b:a', '192k',
        #             final_output
        #         ]

        #     await run_command(mix_cmd)
        #     vt = VideoTranscriber(final_output, combined_audio)
        #     vt.transcribe_video()
        #     vt.create_video(f"final_{num}.mp4")

        print("Successfully created all final reel segments")
        return os.path.join(final_dir, "final_reel.mp4")

    except Exception as e:
        print(f"Error creating reel: {str(e)}")
        raise



# video_processor = VideoProcessor()
def generate_narration(text, output_path, voice="p228"):
    """Generate high-quality narration using pre-trained voices"""
    # Initialize with auto-download capability
    tts = TTS(
        model_name="tts_models/en/vctk/vits",
        progress_bar=True,
        gpu=False
    )
    
    # Generate optimized audio for social media
    tts.tts_to_file(
        text=text,
        file_path=output_path,
        speaker=voice,  # Try p245 (male), p228 (female), p262 (neutral)
        speed=1.1,      # Optimal for short-form content
        sample_rate=44100  # Standard reel format
    )

def patched_load_model(ckpt_path, device):
    with torch.serialization.safe_globals([np.core.multiarray.scalar]):
        return _load_model_f(ckpt_path, device)

async def generate_voiceover(summary_json, reel_id, output_dir, language="en", speed=1.5, voice="p228"):
    """
    Generate voiceover using XTTS v2 with proper configuration
    """
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        print(summary_json[0]["body"])
        # Initialize TTS (VCTK VITS specific config)
        tts = TTS(
            model_name="tts_models/en/vctk/vits",
            progress_bar=True,
            gpu=False
        )

        audio_files = []
        print(summary_json[0]["body"])
        for idx, section in enumerate(summary_json[0]["body"]):
            print(section)
            text = section["Paragraph"]
            output_path = os.path.join(output_dir, f"narration_{idx}.wav")
            
            # Run blocking TTS code in executor
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: tts.tts_to_file(
                    text=text,
                    file_path=output_path,
                    speaker=voice,
                    speed=speed,
                    # Must match model's native sample rate
                    sample_rate=22050
                )
            )
            
            audio_files.append({
                "subheading": section["Subheading"],
                "audio_path": output_path,
                "s3_path": f"https://blooogerai.s3.amazonaws.com/voiceovers/{reel_id}/narration_{idx}.wav"
            })
        
        return audio_files

    except Exception as e:
        logging.error(f"Voiceover generation failed: {str(e)}")
        raise  # Propagate error for proper handling

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

def save_to_mongodb(content_id, url, summary_data, reel=False, transcript_data=None, search_data=None, product_data=None, related_posts=None):
    client = get_mongo_client()
    if not client:
        return False

    if reel:
        try:
            db = client['blugr']
            collection = db['reels']

            document = {
                "content_id": content_id,
                "url": url,
                "transcript": {
                    "full_text": transcript_data["full_text"] if transcript_data else [],
                    "segments": transcript_data["segments"] if transcript_data else [],
                    "metadata": transcript_data.get("metadata", {}) if transcript_data else {}
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
                },
                "product_data": product_data if product_data else [],
                "related_posts": related_posts if related_posts else [],
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
    else:
        try:
            db = client['blugr']
            collection = db['generated-texts']

            document = {
                "content_id": content_id,
                "url": url,
                "transcript": {
                    "full_text": transcript_data["full_text"] if transcript_data else [],
                    "segments": transcript_data["segments"] if transcript_data else [],
                    "metadata": transcript_data.get("metadata", {}) if transcript_data else {}
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
                },
                "product_data": product_data if product_data else [],
                "related_posts": related_posts if related_posts else [],
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

def save_product(product_data, related, affiliate_id):
    client = get_mongo_client()
    if not client:
        return False

    
    try:
        db = client['blugr']
        collection = db['products']
        document = {
            "product_data": product_data,
            "related_posts": related
        }
        result = collection.update_one(
            {"affiliate_id": affiliate_id},
            {"$set": document},
            upsert=True
        )

        if result.upserted_id:
            print(f"Inserted new document with ID: {result.upserted_id}")
        else:
            print(f"Updated existing document for content_id: {affiliate_id}")

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

def transcribe(audio_filename, log_queue=None):
    def log(message):
        if log_queue:
            log_queue.write(message)
        print(message)
    transcriber = WhisperTranscriber(model_size='base')
    transcript_result = transcriber.transcribe(audio_filename)
    content_id = os.path.basename(os.path.dirname(audio_filename))
    base_path = f"./data/youtube/{content_id}"
    # Extract content ID safely
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
    return transcript_result

def tf_idf(summary_json, transcript_result, log_queue=None, reel=False): 
    def log(message):
        if log_queue:
            log_queue.write(message)
        print(message)

    if reel:
        subheadings = [item["Subheading"] for item in summary_json["body"]]
    else:
        subheadings = [item["h2"] for item in summary_json["body"]]

    documents = [segment["text"] for segment in transcript_result["segments"]]

    # Process subheadings and perform TF-IDF analysis
    log("Performing TF-IDF analysis and search...")
    search_results = []

    try:
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
    except Exception as e:  # <-- ADD MISSING EXCEPT BLOCK
        log(f"Error in TF-IDF processing: {str(e)}")
        return []
    
    return search_results

def screenshots_matchs(content_id, search_results, video_path, screenshots_dir, index=0, log_queue=None):
    yt = Youtube()
    def log(message):
        if log_queue:
            log_queue.write(message)
        print(message)
    for result in search_results:
        # Check if there are matches before accessing [0]
        if not result.get('matches'):
            log(f"No matches found for subheading: {result['subheading']}")
            continue
            
        match = result["matches"][0]  # Now safe to access
        # Rest of the function remains the same
        start_time = seconds_to_ffmpeg_timestamp(match["start"])
        screenshot_id = f"{result['subheading'].replace(' ', '_')}_{index}"
        local_screenshot_path = os.path.join(screenshots_dir, f"{screenshot_id}.png")

        if os.path.exists(local_screenshot_path):
            log(f"Screenshot already exists at {local_screenshot_path}")
        else:
            log(f"Taking screenshot for timestamp {start_time} (ID: {screenshot_id})")
            yt.take_screenshot(
                video_path=video_path,
                timestamp=start_time,
                screenshots_dir=screenshots_dir,
                id=screenshot_id
            )

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

def videos_match(content_id, search_results, video_path, videos_dir, index=0, log_queue=None):
    yt = Youtube()
    def log(message):
        if log_queue:
            log_queue.write(message)
        print(message)

    log("clipping...")
    for result in search_results:
        # Check if there are matches before accessing [0]
        if not result.get('matches'):
            log(f"No matches found for subheading: {result['subheading']}")
            continue
            
        match = result["matches"][0]  # Now safe to access
        # Rest of the function remains the same
        start_time = seconds_to_ffmpeg_timestamp(match["start"])
        end_time = seconds_to_ffmpeg_timestamp(match["end"])

        video_id = f"{result['subheading'].replace(' ', '_')}_{index}"
        video_id = re.sub(r'[^\w\-_\. ]', '', video_id)
        video_id = video_id.replace(" ", "_").replace("__", "_")
        local_video_path = os.path.join(videos_dir, f"{video_id}.mp4")

        if os.path.exists(local_video_path):
            log(f"Clip already exists at {local_video_path}")
        else:
            log(f"Making clip for timestamp {start_time} (ID: {video_id})")

            yt.save_video_clip(
                video_path=video_path,
                output_dir=videos_dir,
                start_time = start_time,
                end_time = end_time,
                clip_id=video_id
            )

            local_video_path = os.path.join(videos_dir, f"{video_id}.mp4")
            s3_path = f"clips/{content_id}/{video_id}.mp4"

            # Upload to S3
            if os.path.exists(local_video_path):
                log(f"Uploading clip to S3: {s3_path}")
                s3_handler.upload_file(local_video_path, s3_path)

                # Update the match data with S3 URL
                s3_url = f"https://blooogerai.s3.amazonaws.com/{s3_path}"
                match["video_path"] = s3_url
                match["local_video_path"] = f"clips/{video_id}.mp4"
                # Optionally remove local file after upload
                # os.remove(local_screenshot_path)
            else:
                log(f"Clip file not found: {local_video_path}")
                match["video_path"] = None

async def process_youtube_url(url, product_data=None, related_posts=None, log_queue=None):
    
    client = get_mongo_client()
    if not client:
        return False
    db = client['blugr']
    collection = db['generated-texts']
    print(url.split('/')[-1])
    exists = collection.find_one({'content_id': url.split('/')[-1]})
    if exists:
        return True

    def log(message):
        if log_queue:
            log_queue.write(message)
        print(message)

    try:
        log("Initializing YouTube processing...")
        yt = Youtube()
        log("Downloading audio...")
        audio_filename, length = yt.download_audio_from_url(url)
        log(f"Downloaded audio: {audio_filename}")
        log("Downloading video...")
        video_path, _ = yt.download_video(url)
        log("Getting most replayed segments...")
        most_replayed = yt.get_most_replayed(url)

        try:
            with open(most_replayed, 'r') as f:
                try:
                    info = json.load(f)
                except json.JSONDecodeError:
                    log("Error: Empty or invalid most_replayed JSON file")
                    info = None
                    
            if info:
                info.sort(key=lambda x: x['value'], reverse=True)
                # Add bounds checking
                start_time = max(0, info[0]['start_time'] - 0.5)
                duration = info[0]['end_time'] - info[0]['start_time'] + 0.5
                yt.make_gif_most_viewed(video_path, str(start_time), str(duration))
        except FileNotFoundError:
            log("Most replayed data file not found")
        except Exception as e:
            log(f"Error processing most replayed data: {str(e)}")
        
        content_id = os.path.basename(os.path.dirname(audio_filename))
        base_path = f"./data/youtube/{content_id}"
        log("Transcribing audio...")
        # Fix transcript loading logic
        transcript_file = f"{base_path}/transcript.json"
        transcript_data = None
        # Inside the process_youtube_url function, when checking if the transcript file exists:
        if os.path.exists(transcript_file):
            with open(transcript_file, 'r', encoding='utf-8') as file:
                transcript_result = json.load(file)
            # Ensure we have the transcription text
            if "transcription" not in transcript_result:  # Note: Fix typo if needed ("transcription" -> "transcription")
                transcript_result["transcription"] = " ".join([seg["text"] for seg in transcript_result["segments"]])
            # Prepare transcript_data structure similar to when generated
            transcript_data = {
                "full_text": transcript_result["transcription"],
                "segments": transcript_result["segments"],
                "metadata": transcript_result.get("metadata", {})
            }
        else:
            # Generate new transcript and create transcript_data as before
            transcript_result = transcribe(audio_filename, log_queue)
            transcript_data = {
                "full_text": transcript_result["transcription"],
                "segments": transcript_result["segments"],
                "metadata": {
                    "language": transcript_result["language"],
                    "language_probability": transcript_result["language_probability"]
                }
            }

        log(f"Transcript saved: {base_path}/transcript.txt")
        log(f"Detailed transcription saved: {base_path}/transcript.json")
        log(f"Subtitles saved: {base_path}/subtitles.srt")


        # After
        summary_path = f"{base_path}/summary.json"
        if os.path.exists(summary_path) and os.path.getsize(summary_path) > 0:
            with open(summary_path, 'r', encoding='utf-8') as f:
                try:
                    log("Opening existing summary file...")
                    summary_response = json.load(f)
                except json.JSONDecodeError:
                    log("Corrupt summary file, regenerating...")
                    # Regenerate logic here
        else:
            log("Generating summary using Gemini API...")
            response = await generate_text(transcript_result['transcription'], blog_prompt)
            summary_response = response
            log("Writing summary to file...")
            with open(f"{base_path}/summary.json", "w", encoding='utf-8') as f:
                json.dump(summary_response, f, indent=4)

        # Parse the summary JSON
        try:
            summary_json = summary_response["generated_text"]
        except json.JSONDecodeError as e:
            log(f"Warning: Could not parse summary JSON: {e}")

        # Process subheadings and perform TF-IDF analysis
        subheadings = [item["h2"] for item in summary_json["body"]]
        documents = [segment["text"] for segment in transcript_result["segments"]]
        # Process subheadings and perform TF-IDF analysis
        log("Performing TF-IDF analysis and search...")
        search_results = tf_idf(summary_json, transcript_result)
        try:
            log("Generating screenshots for search results...")
            video_path = f"./data/youtube/{content_id}/"
            screenshots_dir = os.path.join(video_path, 'screenshots')
            os.makedirs(screenshots_dir, exist_ok=True)

            screenshots_matchs(content_id, search_results, video_path, screenshots_dir)
            
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

        summary_data = {
            "raw_response": summary_response["generated_text"],
            "parsed_summary": summary_json
        }

        # Save to MongoDB
        log("Saving to MongoDB...")
        mongodb_success = save_to_mongodb(
            content_id=content_id,
            url=url,
            transcript_data= transcript_data if transcript_data else None,
            summary_data=summary_data,
            search_data=search_data,
            product_data = product_data if product_data else None,
            related_posts = related_posts if related_posts else None
        )
        if mongodb_success:
            log("Successfully saved to MongoDB")
        else:
            log("Failed to save to MongoDB")

        log("Processing completed successfully")
        return content_id

    except Exception as e:
        log(f"Error processing URL {url}: {str(e)}")
        return False

async def full_processing_pipeline(affiliate_url, key=None, log_queue=None):
    base_path = f"./data/amazon/{affiliate_url.split('/')[-1].split('=')[-1]}"
    product_id = affiliate_url.split('/')[-1].split('=')[-1]
    screenshots_dir = os.path.join(base_path, 'screenshots')
    def log(message):
        if log_queue:
            log_queue.write(message)
        print(message)
    try:
        # Step 1: Get product info
        print('extract product info')
        product_info = extract_product_info(affiliate_url)
        
        # Step 2: Search YouTube using yt-dlp
        yt = Youtube()
        if key:
            top_videos = yt.search_videos(key)
        else:
            top_videos = yt.search_videos(product_info['title'])
        print(top_videos)
        # Step 3: Process videos (existing code)
        related = [video['url'].split('/')[-1].split('=')[-1] for video in top_videos]
        save_product(product_info, related, product_id)
        all_transcripts = []
        content_ids = []
        for video in top_videos:
            content_id = await process_youtube_url(video['url'], product_data=product_info, related_posts=related)
            print(content_id)
            if content_id:
                with open(f"./data/youtube/{content_id}/transcript.txt", 'r') as f:
                    all_transcripts.append(f.read())
                    content_ids.append(content_id)
        print('i')
        # Step 4: Analysis (existing code)
        combined_text = "\n\n".join(all_transcripts)
        analysis = await generate_text(f"transcripts {combined_text}\n", affiliate_prompt)
        summary_response = analysis
        log("Writing summary to file...")
        os.makedirs(base_path, exist_ok=True)
        with open(f"{base_path}/summary.json", "w", encoding='utf-8') as f:
            json.dump(summary_response, f, indent=4)
        print('j')
        try:
            summary_json = json.loads(summary_response["generated_text"])
        except json.JSONDecodeError as e:
            log(f"Warning: Could not parse summary JSON: {e}")
            summary_json = {
                "title": "Summary",
                "body": [{"h2": "Content", "text": summary_response["generated_text"]}]
            }

        print('k')
        transcripts = []
        video_paths = []
        for content_id in content_ids:
            transcript_path = f"./data/youtube/{content_id}/transcript.json"
            video_path = f"./data/youtube/{content_id}/"
            with open(transcript_path) as f:
                transcript_result = json.load(f)
            transcripts.append(transcript_result)
            video_paths.append(video_path)
        print('m')
        search_res = [tf_idf(summary_json, transcript) for transcript in transcripts]

        # Process each video's search results
        for video_index, video_search_results in enumerate(search_res):
            screenshots_matchs(
                product_id, 
                video_search_results,  # Pass the full list of results for this video
                video_paths[video_index], 
                screenshots_dir,
                index=video_index
            )  # Use video_index to get the correct video path

        print('l')
        summary_data = {
            "raw_response": summary_response["generated_text"],
            "parsed_summary": summary_json
        }
        log("Saving to MongoDB...")
        mongodb_success = save_to_mongodb(
            content_id=product_id,
            url=f'bloogist.com/blog/{product_id}',
            summary_data=summary_data,
            product_data=product_info,
            related_posts=related
        )
        if mongodb_success:
            log("Successfully saved to MongoDB")
        else:
            log("Failed to save to MongoDB")
        return {
            'product_info': product_info,
            'videos_processed': len(top_videos),
            'analysis': analysis
        }
    
    except Exception as e:
        raise RuntimeError(f"Processing pipeline failed: {str(e)}")

async def reel_script(prompt, reel_id, key=None, log_queue=None):
    yt = Youtube()
    def log(message):
        if log_queue:
            log_queue.write(message)
        print(message)
    base_path = f"./data/reel/{reel_id}"
    videos_dir = os.path.join(base_path, 'clips')

    summary_path = f"{base_path}/summary.json"
    os.makedirs(base_path, exist_ok=True)
    if os.path.exists(summary_path) and os.path.getsize(summary_path) > 0:
        with open(summary_path, 'r', encoding='utf-8') as f:
            try:
                log("Opening existing summary file...")
                summary_response = json.load(f)
                response = summary_response
                print(response)
            except json.JSONDecodeError:
                log("Corrupt summary file, regenerating...")
                # Regenerate logic here
    else:
        log("Generating summary using Gemini API...")
        response = await generate_script(prompt=reel_script_prompt+f"\n\n The reel Script should be about: {prompt}")
        summary_response = response
        log("Writing summary to file...")
        with open(f"{base_path}/summary.json", "w", encoding='utf-8') as f:
            json.dump(summary_response, f, indent=4)
    
    # Parse the summary JSON
    summary_json = summary_response["generated_text"]
    print('k')
    print(summary_json)
    all_transcripts = []
    content_ids = []
    print(summary_json[0]['body'])
    for section in summary_json[0]['body']:
        print(section)
        top_video = yt.search_videos(section["keyword"], max_results=1)
        if top_video:
            video = top_video[0]
            content_id = await process_youtube_url(video['url'])
            print(content_id)
            if content_id:
                with open(f"./data/youtube/{content_id}/transcript.txt", 'r') as f:
                    all_transcripts.append(f.read())
                    content_ids.append(content_id)
        else:
            log(f"No videos found for keyword: {section['keyword']}")

    combined_text = "\n--transcript--\n\n".join(all_transcripts)

    voiceover_dir = os.path.join(base_path, 'voiceovers')
    os.makedirs(voiceover_dir, exist_ok=True)
    
    # Generate voiceovers with different parameters if needed
    audio_files = await generate_voiceover(
        summary_json,
        reel_id,
        voiceover_dir
    )
    print('l')

    for audio in audio_files:
        if os.path.exists(audio["audio_path"]):
            s3_handler.upload_file(audio["audio_path"], audio["s3_path"])
            # Add paths to your summary data
            audio["s3_url"] = f"https://blooogerai.s3.amazonaws.com/{audio['s3_path']}"
    print('x')
    transcripts = []
    video_paths = []
    for content_id in content_ids:
        transcript_path = f"./data/youtube/{content_id}/transcript.json"
        video_path = f"./data/youtube/{content_id}/video.mp4"
        with open(transcript_path) as f:
            transcript_result = json.load(f)
        transcripts.append(transcript_result)
        video_paths.append(video_path)
    print('m')
    search_res = [[tf_idf(reel_body, transcript, reel=True) for transcript in transcripts] for reel_body in summary_json]
    print('n')
    for reel_search_res in search_res:
        print('k')
        for video_index, video_search_results in enumerate(reel_search_res):
            print(video_search_results)
            videos_match(
                content_id,
                video_search_results,
                video_paths[video_index],
                videos_dir,
                index=video_index,
            )

    print('l')

    log("Stitching final reel...")
    output_dir = os.path.join(base_path, 'final')
    os.makedirs(output_dir, exist_ok=True)
    
    final_reel_path, temp_files = await create_final_reel(
        reel_id
    )
    print('stitch')
    # Upload final reel to S3
    s3_reel_path = f"reels/{reel_id}/final.mp4"
    s3_handler.upload_file(final_reel_path, s3_reel_path)
    
    # Cleanup temporary files
    for f in temp_files:
        if os.path.exists(f):
            os.remove(f)
    print('o')
    # Update MongoDB with final reel URL
    summary_data = {
        "raw_response": summary_response["generated_text"],
        "parsed_summary": summary_json,
        "final_reel_url": f"https://blooogerai.s3.amazonaws.com/{s3_reel_path}",
        "audio_files": audio_files
    }
    log("Saving to MongoDB...")
    mongodb_success = save_to_mongodb(
        content_id=reel_id,
        url=f'bloogist.com/reels/{reel_id}',
        summary_data=summary_data,
    )
    if mongodb_success:
        log("Successfully saved to MongoDB")
    else:
        log("Failed to save to MongoDB")
    return {
        'content_id': reel_id,
        'videos_processed': len(content_ids),
        'analysis': response
    }

async def make_reel(prompt, reel_id, key=None, product_info=None, log_queue=None):
    def log(message):
        if log_queue:
            log_queue.write(message)
        print(message)
    base_path = f"./data/reel/{reel_id}"
    videos_dir = os.path.join(base_path, 'clips')
    print(base_path)
    yt = Youtube()
    print("searching...")
    if key:
        top_videos = yt.search_videos(key)
    else:
        top_videos = yt.search_videos(prompt)
    print(top_videos)
    all_transcripts = []
    content_ids = []
    related = [video['url'].split('/')[-1].split('=')[-1] for video in top_videos]
    for video in top_videos:
        content_id = await process_youtube_url(video['url'], product_data=product_info, related_posts=related)
        log(f"finished processing video {content_id}...")
        print(content_id)
        if content_id:
            with open(f"./data/youtube/{content_id}/transcript.txt", 'r') as f:
                all_transcripts.append(f.read())
                content_ids.append(content_id)

    combined_text = "\n--transcript--\n\n".join(all_transcripts)


    # analysis = await generate_text(f"transcripts: {combined_text}\n", reel_prompt+f"\n\n The reel should be: {prompt}")
    # summary_response = analysis
    # log("Writing summary to file...")
    # os.makedirs(base_path, exist_ok=True)
    # with open(f"{base_path}/summary.json", "w", encoding='utf-8') as f:
    #     json.dump(summary_response, f, indent=4)
    # print('j')
    # try:
    #     summary_json = json.loads(summary_response["generated_text"])
    # except json.JSONDecodeError as e:
    #     log(f"Warning: Could not parse summary JSON: {e}")
    #     summary_json = {
    #         "title": "Summary",
    #         "body": [{"h2": "Content", "text": summary_response["generated_text"]}]
    #     }

    summary_path = f"{base_path}/summary.json"
    os.makedirs(base_path, exist_ok=True)
    if os.path.exists(summary_path) and os.path.getsize(summary_path) > 0:
        with open(summary_path, 'r', encoding='utf-8') as f:
            try:
                log("Opening existing summary file...")
                summary_response = json.load(f)
                response = summary_response
            except json.JSONDecodeError:
                log("Corrupt summary file, regenerating...")
                # Regenerate logic here
    else:
        log("Generating summary using Gemini API...")
        response = await generate_text(f"transcripts: {combined_text}\n", reel_prompt+f"\n\n The reel should be: {prompt}")
        summary_response = response
        log("Writing summary to file...")
        with open(f"{base_path}/summary.json", "w", encoding='utf-8') as f:
            json.dump(summary_response, f, indent=4)

    # Parse the summary JSON
    try:
        summary_json = summary_response["generated_text"]
    except json.JSONDecodeError as e:
        log(f"Warning: Could not parse summary JSON: {e}")
        summary_json = {
            "title": "Summary",
            "body": [{"h2": "Content", "text": summary_response["generated_text"]}]
            }
    print('k')
    voiceover_dir = os.path.join(base_path, 'voiceovers')
    os.makedirs(voiceover_dir, exist_ok=True)
    
    # Generate voiceovers with different parameters if needed
    audio_files = await generate_voiceover(
        summary_json,
        reel_id,
        voiceover_dir
    )
    print('l')

    for audio in audio_files:
        if os.path.exists(audio["audio_path"]):
            s3_handler.upload_file(audio["audio_path"], audio["s3_path"])
            # Add paths to your summary data
            audio["s3_url"] = f"https://blooogerai.s3.amazonaws.com/{audio['s3_path']}"
    
    # Update MongoDB data with voiceover info
    print('x')
    transcripts = []
    video_paths = []
    for content_id in content_ids:
        transcript_path = f"./data/youtube/{content_id}/transcript.json"
        video_path = f"./data/youtube/{content_id}/video.mp4"
        with open(transcript_path) as f:
            transcript_result = json.load(f)
        transcripts.append(transcript_result)
        video_paths.append(video_path)
    print('m')
    search_res = [[tf_idf(reel_body, transcript, reel=True) for transcript in transcripts] for reel_body in summary_json]
    print('n')
    for reel_search_res in search_res:
        print('k')
        for video_index, video_search_results in enumerate(reel_search_res):
            print(video_search_results)
            videos_match(
                content_id,
                video_search_results,
                video_paths[video_index],
                videos_dir,
                index=video_index,
            )

    print('l')

    log("Stitching final reel...")
    output_dir = os.path.join(base_path, 'final')
    os.makedirs(output_dir, exist_ok=True)
    
    final_reel_path, temp_files = await create_final_reel(
        reel_id
    )
    
    # Upload final reel to S3
    s3_reel_path = f"reels/{reel_id}/final.mp4"
    s3_handler.upload_file(final_reel_path, s3_reel_path)
    
    # Cleanup temporary files
    for f in temp_files:
        if os.path.exists(f):
            os.remove(f)
    
    # Update MongoDB with final reel URL
    summary_data = {
        "raw_response": summary_response["generated_text"],
        "parsed_summary": summary_json,
        "final_reel_url": f"https://blooogerai.s3.amazonaws.com/{s3_reel_path}",
        "audio_files": audio_files
    }
    log("Saving to MongoDB...")
    mongodb_success = save_to_mongodb(
        content_id=reel_id,
        url=f'bloogist.com/reels/{reel_id}',
        summary_data=summary_data,
    )
    if mongodb_success:
        log("Successfully saved to MongoDB")
    else:
        log("Failed to save to MongoDB")
    return {
        'content_id': reel_id,
        'videos_processed': len(top_videos),
        'analysis': response
    }

async def make_reel_script(prompt, reel_id, key=None, product_info=None, log_queue=None):
    def log(message):
        if log_queue:
            log_queue.write(message)
        print(message)
    base_path = f"./data/reel/{reel_id}"
    videos_dir = os.path.join(base_path, 'clips')
    print(base_path)

    summary_path = f"{base_path}/summary.json"
    os.makedirs(base_path, exist_ok=True)
    if os.path.exists(summary_path) and os.path.getsize(summary_path) > 0:
        with open(summary_path, 'r', encoding='utf-8') as f:
            try:
                log("Opening existing summary file...")
                summary_response = json.load(f)
                response = summary_response
            except json.JSONDecodeError:
                log("Corrupt summary file, regenerating...")
                # Regenerate logic here
    else:
        log("Generating summary using Gemini API...")
        response = await generate_text(f"transcripts: {combined_text}\n", reel_prompt+f"\n\n The reel should be: {prompt}")
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

async def get_reel_sources(reel_id, product_info=None, log_queue=None):
    def log(message):
        if log_queue:
            log_queue.write(message)
        print(message)
    base_path = f"./data/reel/{reel_id}"
    videos_dir = os.path.join(base_path, 'clips')
    print(base_path)

    summary_path = f"{base_path}/summary.json"
    os.makedirs(base_path, exist_ok=True)
    if os.path.exists(summary_path) and os.path.getsize(summary_path) > 0:
        with open(summary_path, 'r', encoding='utf-8') as f:
            try:
                log("Opening existing summary file...")
                summary_response = json.load(f)
                summary_json = json.loads(summary_response['generated_text'])
            except:
                log("Error loading summary file...")

    subheadings = [item["Subheading"] for item in summary_json["body"]]

    yt = Youtube()
    print("searching...")
    yt_search_results = [yt.search_videos(subheading, 1) for subheading in subheadings] 
    
    return yt_search_results

async def make_clips(reel_id, product_info=None, log_queue=None):
    def log(message):
        if log_queue:
            log_queue.write(message)
        print(message)
    base_path = f"./data/reel/{reel_id}"
    videos_dir = os.path.join(base_path, 'clips')
    print(base_path)

    all_transcripts = []
    content_ids = []
    related = [video[0]['url'].split('/')[-1].split('=')[-1] for video in yt_search_results]

    for video in yt_search_results:
        if product_info:
            content_id = await process_youtube_url(video[0]['url'], product_data=product_info, related_posts=related)
        else:
            content_id = await process_youtube_url(video[0]['url'], related_posts=related)
        
        log(f"finished processing video {content_id}...")
        print(content_id)
        if content_id:
            with open(f"./data/youtube/{content_id}/transcript.txt", 'r') as f:
                all_transcripts.append(f.read())
                content_ids.append(content_id)
    
    voiceover_dir = os.path.join(base_path, 'voiceovers')
    os.makedirs(voiceover_dir, exist_ok=True)
    
    # Generate voiceovers with different parameters if needed
    audio_files = await generate_voiceover(
        summary_json, 
        voiceover_dir
    )
    print('l')

    for audio in audio_files:
        if os.path.exists(audio["audio_path"]):
            s3_handler.upload_file(audio["audio_path"], audio["s3_path"])
            # Add paths to your summary data
            audio["s3_url"] = f"https://blooogerai.s3.amazonaws.com/{audio['s3_path']}"

    transcripts = []
    video_paths = []
    for content_id in content_ids:
        transcript_path = f"./data/youtube/{content_id}/transcript.json"
        video_path = f"./data/youtube/{content_id}/video.mp4"
        with open(transcript_path) as f:
            transcript_result = json.load(f)
        transcripts.append(transcript_result)
        video_paths.append(video_path)
    print('m')

    search_res = [[tf_idf(reel_body, transcript, reel=True) for transcript in transcripts] for reel_body in summary_json]

    print('n')
    for reel_search_res in search_res:
        print('k')
        for video_index, video_search_results in enumerate(reel_search_res):
            print(video_search_results)
            videos_match(
                content_id,
                video_search_results,
                video_paths[video_index],
                videos_dir,
                index=video_index,
            )

    print('l')
    summary_data = {
        "raw_response": summary_response["generated_text"],
        "parsed_summary": summary_json
    }
    log("Saving to MongoDB...")
    mongodb_success = save_to_mongodb(
        content_id=reel_id,
        url=f'bloogist.com/reels/{reel_id}',
        summary_data=summary_data,
    )
    if mongodb_success:
        log("Successfully saved to MongoDB")
    else:
        log("Failed to save to MongoDB")
    return {
        'content_id': reel_id,
        'videos_processed': len(top_videos),
        'analysis': response
    }

if __name__ == "__main__":
    url = input("Enter YouTube URL: ")
    asyncio.run(process_youtube_url(url))