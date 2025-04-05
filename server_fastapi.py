from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from main import process_youtube_url, full_processing_pipeline, make_reel, reel_script
from fastapi.middleware.cors import CORSMiddleware
import time
import aiofiles
from fastapi.responses import StreamingResponse
from pathlib import Path
from contextlib import asynccontextmanager
import logging

from fastapi import BackgroundTasks
from uuid import uuid4
from typing import Dict
import os
import psutil

from fastapi import  status, UploadFile, File, Form
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from task_manager import task_manager
from typing import Optional

from youtube import Youtube

# Import the new function we'll create
from main import process_local_video

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Rate limiter setup
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

class VideoRequest(BaseModel):
    url: str


class ProcessingResponse(BaseModel):
    status: str
    message: str
    content_id: str = None
    error: str = None

async def log_generator():
    log_file = Path('server.log')
    if not log_file.exists():
        log_file.touch()
    try:
        async with aiofiles.open('server.log', mode='r') as f:
            await f.seek(0, 2)  # Seek to end of file
            while True:
                line = await f.readline()
                if not line:
                    await asyncio.sleep(0.1)
                    continue
                yield f"data: {line}\n\n"
    except FileNotFoundError:
        yield "data: Log file not found\n"
    except Exception as e:
        yield f"error: {e}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for startup/shutdown events"""
    # Startup logic
    log_file = Path('server.log')
    
    try:
        if not log_file.exists():
            log_file.touch(mode=0o644)
            logging.info("Created log file")
            
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("server.log"),
                logging.StreamHandler()
            ]
        )
        logging.info("Application started")
        
        # Create uploads directory if it doesn't exist
        uploads_dir = Path('./data/uploads')
        if not uploads_dir.exists():
            uploads_dir.mkdir(parents=True, exist_ok=True)
            logging.info("Created uploads directory")
        
    except Exception as e:
        logging.error(f"Failed to initialize logging: {str(e)}")
        raise
    
    yield  # App runs here
    
    # Shutdown logic
    logging.info("Application shutting down")
    for handler in logging.root.handlers[:]:
        handler.close()
        logging.root.removeHandler(handler)


@app.get("/stream-logs")
async def stream_logs():
    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# Enhanced endpoints
@app.post("/process-video")
@limiter.limit("10/minute")
async def process_video(
    request: Request,
    background_tasks: BackgroundTasks
):
    req_body = await request.json()
    print(req_body)
    try:
        task_id = str(uuid4())
        
        try:
            task_manager.create_task(task_id, req_body["url"])
        except HTTPException as he:
            return JSONResponse(
                status_code=he.status_code,
                content={"detail": he.detail}
            )

        background_tasks.add_task(
            process_video_task,
            task_id,
            req_body["url"]
        )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "task_id": task_id,
                "status_url": f"/task-status/{task_id}",
                "monitor_url": "/system-status"
            }
        )

    except Exception as e:
        logging.error(f"Critical error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

async def process_video_task(task_id: str, url: str):
    try:
        content_id = await process_youtube_url(url, task_id)
        if content_id:
            task_manager.complete_task(task_id, { 'bloog_url': f"bloogist.com/blog/{content_id}"})

    except Exception as e:
        task_manager.fail_task(task_id, str(e))
        logging.error(f"Task {task_id} failed: {str(e)}")

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    task = task_manager.active_tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task.get("progress", 0),
        "duration": time.time() - task["start_time"],
        "estimated_remaining": calculate_remaining_time(task),
        "result": task.get("result"),
        "error": task.get("error")
    }

def calculate_remaining_time(task):
    if task["status"] == "completed":
        return 0
    elapsed = time.time() - task["start_time"]
    progress = task.get("progress", 1)
    if progress == 0:
        return None
    return (elapsed / progress) * (100 - progress)

@app.get("/system-status")
async def system_status():
    return {
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": psutil.virtual_memory().percent
    }
    
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

class AffiliateRequest(BaseModel):
    affiliate_url: str
    key: Optional[str] = None

@app.post("/process-affiliate")
@limiter.limit("10/minute")
async def process_affiliate(
    request: Request,
    background_tasks: BackgroundTasks,
    affiliate_request: AffiliateRequest
):
    try:
        task_id = str(uuid4())
        
        try:
            task_manager.create_task(task_id, affiliate_request.affiliate_url)
        except HTTPException as he:
            return JSONResponse(
                status_code=he.status_code,
                content={"detail": he.detail}
            )

        background_tasks.add_task(
            process_affiliate_task,
            task_id,
            affiliate_request.affiliate_url,
            affiliate_request.key
        )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "task_id": task_id,
                "status_url": f"/task-status/{task_id}",
                "monitor_url": "/system-status"
            }
        )

    except Exception as e:
        logging.error(f"Critical error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

async def process_affiliate_task(task_id: str, affiliate_url: str, key: str = None):
    try:
        result = await full_processing_pipeline(affiliate_url, key)
        task_manager.complete_task(task_id, {
            'product_info': result['product_info'],
            'videos_processed': result['videos_processed'],
            'analysis': result['analysis']
        })
    except Exception as e:
        task_manager.fail_task(task_id, str(e))
        logging.error(f"Affiliate processing task {task_id} failed: {str(e)}")

class ReelRequest(BaseModel):
    prompt: str
    id: str
    key: Optional[str] = None
    
@app.post("/make-reel")
@limiter.limit("20/minute")
async def create_reel(
    request: Request,
    background_tasks: BackgroundTasks,
    reel_request: ReelRequest
):
    try:
        task_id = str(uuid4())
        
        try:
            task_manager.create_task(task_id, reel_request.prompt)
        except HTTPException as he:
            return JSONResponse(
                status_code=he.status_code,
                content={"detail": he.detail}
            )

        background_tasks.add_task(
            process_reel_task,
            task_id,
            reel_request.prompt,
            reel_request.id,
            reel_request.key
        )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "task_id": task_id,
                "status_url": f"/task-status/{task_id}",
                "monitor_url": "/system-status"
            }
        )

    except Exception as e:
        logging.error(f"Critical error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

async def process_reel_task(task_id: str, prompt: str, reel_id: str, key: str = None):
    try:
        import cProfile
        profiler = cProfile.Profile()
        profiler.enable()
        result = await make_reel(prompt, reel_id, key)
        profiler.disable()
        profiler.dump_stats(f"profile_v1.prof")  # Per video profile file
        print(f"FinishedProfiling...")
        task_manager.complete_task(task_id, {
            'content_id': result['content_id'],
            'videos_processed': result['videos_processed'],
            'analysis': result['analysis']
        })
    except Exception as e:
        task_manager.fail_task(task_id, str(e))
        logging.error(f"Reel creation task {task_id} failed: {str(e)}")

@app.post("/make-reel-script")
@limiter.limit("20/minute")
async def create_reel_script(
    request: Request,
    background_tasks: BackgroundTasks,
    reel_request: ReelRequest
):
    try:
        task_id = str(uuid4())
        
        try:
            task_manager.create_task(task_id, reel_request.prompt)
        except HTTPException as he:
            return JSONResponse(
                status_code=he.status_code,
                content={"detail": he.detail}
            )

        background_tasks.add_task(
            process_reel_script_task,
            task_id,
            reel_request.prompt,
            reel_request.id,
            reel_request.key
        )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "task_id": task_id,
                "status_url": f"/task-status/{task_id}",
                "monitor_url": "/system-status"
            }
        )

    except Exception as e:
        logging.error(f"Critical error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

async def process_reel_script_task(task_id: str, prompt: str, reel_id: str, key: str = None):
    try:
        result = await reel_script(prompt, reel_id, key)
        task_manager.complete_task(task_id, {
            'content_id': result['content_id'],
            'videos_processed': result['videos_processed'],
            'analysis': result['analysis']
        })
    except Exception as e:
        task_manager.fail_task(task_id, str(e))
        logging.error(f"Reel creation task {task_id} failed: {str(e)}")

class SearchYTRequest(BaseModel):
    prompt: str
    count: Optional[int] = 1

async def _search_youtube(prompt: str, count: int = 1):
    try:
        yt = Youtube()
        videos = yt.search_videos(prompt, max_results=count)
        print(videos)
        results = []
        
        for video in videos:
            results.append({
                "title": video.get("title", ""),
                "url": video.get("url", ""),
                "view_count": video.get("view_count", 0),
                "duration": video.get("duration", 0)
            })
            
        return {"results": results}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching YouTube: {str(e)}"
        )

@app.get("/search_yt")
async def search_youtube_get(prompt: str, count: Optional[int] = 1):
    return await _search_youtube(prompt, count)

@app.post("/upload-video")
@limiter.limit("5/minute")
async def upload_process_video(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(None)
):
    if not file.filename.endswith('.mp4'):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Only MP4 files are supported"}
        )
    
    try:
        task_id = str(uuid4())
        content_id = str(uuid4())
        
        # Create directory for the uploaded file
        upload_dir = f"./data/uploads/{content_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the uploaded file
        file_path = f"{upload_dir}/video.mp4"
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        
        try:
            task_manager.create_task(task_id, f"Processing uploaded video: {file.filename}")
        except HTTPException as he:
            return JSONResponse(
                status_code=he.status_code,
                content={"detail": he.detail}
            )

        # Start processing in background
        background_tasks.add_task(
            process_video_upload_task,
            task_id,
            content_id,
            file_path,
            title or file.filename
        )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "task_id": task_id,
                "content_id": content_id,
                "status_url": f"/task-status/{task_id}",
                "monitor_url": "/system-status"
            }
        )

    except Exception as e:
        logging.error(f"Critical error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

async def process_video_upload_task(task_id: str, content_id: str, file_path: str, title: str):
    try:
        result_content_id = await process_local_video(file_path, content_id, title, task_id)
        if result_content_id:
            task_manager.complete_task(task_id, { 'content_id': result_content_id })
        else:
            task_manager.fail_task(task_id, "Failed to process video")
    except Exception as e:
        task_manager.fail_task(task_id, str(e))
        logging.error(f"Task {task_id} failed: {str(e)}")