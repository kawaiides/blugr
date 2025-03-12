from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from main import process_youtube_url
from fastapi.middleware.cors import CORSMiddleware
import time
import aiofiles
from fastapi.responses import StreamingResponse
from pathlib import Path
from contextlib import asynccontextmanager
import logging

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
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


@app.post("/process-video")
async def process_video(request: VideoRequest):
    try:
        # logger.info(f"Processing video URL: {request.url}")

        # Process the video
        result = await process_youtube_url(request.url)

        if result:
            print(True)
            return ProcessingResponse(
                status="success",
                message="Video processed successfully",
                content_id={request.url},
            )
        else:
            raise HTTPException(status_code=500)

    except Exception as e:
        print("uh oh")
        # logger.error(f"Error processing video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy"}