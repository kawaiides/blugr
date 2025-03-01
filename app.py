from fastapi import FastAPI, UploadFile, File
import os
import shutil
from whispercpp import Whisper
from fastapi.middleware.cors import CORSMiddleware
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

w = Whisper('tiny')
UPLOAD_DIR="/tmp"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
    
@app.post('/transcribe')
async def transcriptions(file: UploadFile = File(...)):
    filename = file.filename
    fileobj = file.file
    upload_name = os.path.join(UPLOAD_DIR, filename)
    upload_file = open(upload_name, 'wb+')
    shutil.copyfileobj(fileobj, upload_file)
    upload_file.close()
    
    result = w.transcribe(upload_name)

    segments_list = []
    for segment in result['segments']:
        id = segment["id"]
        start = segment["start"]
        end = segment["end"]
        text = segment["text"]
        segments_list.append(
            {
                "id": id,
                "start": start,
                "end": end,
                "text": text
            }
        )

    text = w.extract_text(result)
    
    return text, segments_list