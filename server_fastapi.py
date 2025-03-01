from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
from datetime import datetime
import uvicorn
import os
import shutil
from whispercpp import Whisper
from fastapi.middleware.cors import CORSMiddleware
from main import process_youtube_url

app = FastAPI(title="Audio Processing API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
    expose_headers=["Content-Disposition"],
)

# Initialize Whisper
w = Whisper('tiny')
# UPLOAD_DIR = "/tmp"
# if not os.path.exists(UPLOAD_DIR):
#     os.makedirs(UPLOAD_DIR)


# Pydantic models
class ProcessRequest(BaseModel):
    url: str


class TaskStatus(BaseModel):
    url: str
    status: str
    start_time: str
    result: Optional[str] = None


class ProcessResponse(BaseModel):
    message: str
    task_id: int
    status: str


class LogsResponse(BaseModel):
    task_id: int
    status: str
    logs: List[str]


# Storage
tasks: Dict[int, TaskStatus] = {}
logs: Dict[int, List[str]] = {}


async def log_message(task_id: int, message: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    if task_id not in logs:
        logs[task_id] = []
    logs[task_id].append(log_entry)
    print(log_entry)


class AsyncLogQueue:
    def __init__(self, task_id: int):
        self.task_id = task_id

    async def write(self, message: str):
        await log_message(self.task_id, message)

    def flush(self):
        pass


async def process_with_logging(url: str, task_id: int):
    try:
        log_queue = AsyncLogQueue(task_id)

        tasks[task_id] = TaskStatus(
            url=url,
            status='processing',
            start_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        await log_message(task_id, f"Starting processing for URL: {url}")

        # Call the async process_youtube_url function
        result = await process_youtube_url(url, log_queue)

        tasks[task_id] = TaskStatus(
            url=url,
            status='completed' if result else 'failed',
            start_time=tasks[task_id].start_time,
            result=str(result)
        )
        await log_message(task_id, f"Processing {'completed successfully' if result else 'failed'}")

    except Exception as e:
        tasks[task_id] = TaskStatus(
            url=url,
            status='failed',
            start_time=tasks[task_id].start_time
        )
        await log_message(task_id, f"Error during processing: {str(e)}")


@app.post("/process/youtube", response_model=ProcessResponse)
async def process_video(request: ProcessRequest):
    url = request.url
    task_id = len(tasks) + 1

    tasks[task_id] = TaskStatus(
        url=url,
        status='initializing',
        start_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

    # Create background task
    await asyncio.create_task(process_with_logging(url, task_id))

    return ProcessResponse(
        message='Processing started',
        task_id=task_id,
        status='initializing'
    )


@app.post('/transcribe')
async def transcribe_file(file: UploadFile = File(...)):
    try:
        filename = file.filename
        upload_name = os.path.join(filename)
        print(upload_name + "herre")
        with open(upload_name, 'wb+') as upload_file:
            shutil.copyfileobj(file.file, upload_file)

        result = w.transcribe(upload_name)
        text = w.extract_text(result)

        # Clean up the uploaded file
        os.remove(upload_name)

        return {"status": "success", "text": text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{task_id}", response_model=TaskStatus)
async def get_status(task_id: int):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks[task_id]


@app.get("/logs/{task_id}", response_model=LogsResponse)
async def get_logs(task_id: int):
    if task_id not in logs:
        raise HTTPException(status_code=404, detail="Task not found")
    return LogsResponse(
        task_id=task_id,
        status=tasks[task_id].status,
        logs=logs[task_id]
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("server_fastapi:app", host="0.0.0.0", port=8000, reload=True)