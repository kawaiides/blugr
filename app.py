# app.py
from fastapi import FastAPI, UploadFile, File
import os
import shutil
from whispercpp import Whisper
from fastapi.middleware.cors import CORSMiddleware
import json
from ytnoti import YouTubeNotifier

app = FastAPI()

notifier = YouTubeNotifier()

@notifier.upload()
async def listener(video):
    print(f"New video from {video.channel.name}: {video.title}")

#notifier.subscribe("UC9EEyg7QBL-stRX-7hTV3ng")  # Channel ID of SpeedyStyle
notifier.run(app=app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
    expose_headers=["Content-Disposition"],
)

w = Whisper('base')


@app.post('/transcribe')
async def transcriptions(audio_filename):
    try:
        upload_name = os.path.abspath(audio_filename)

        # Get the transcription result
        result = w.transcribe(upload_name)

        # Extract the text
        text = w.extract_text(result)

        # Create a simple segment for the entire text
        segments = [{
            "id": 0,
            "start": 0,
            "end": 0,  # You might want to get the audio duration here
            "text": text
        }]

        return {
            "transcription": text,
            "segments": segments
        }
    except Exception as e:
        print(f"Transcription error: {str(e)}")
        raise