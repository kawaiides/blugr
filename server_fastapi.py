from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from main import process_youtube_url
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(_name_)

app = FastAPI()


class VideoRequest(BaseModel):
    url: str


class ProcessingResponse(BaseModel):
    status: str
    message: str
    content_id: str = None
    error: str = None


@app.post("/process-video")
async def process_video(request: VideoRequest):
    try:
        # logger.info(f"Processing video URL: {request.url}")

        # Process the video
        result = await process_youtube_url(request.url)

        if result:
            return ProcessingResponse(
                status="success",
                message="Video processed successfully",
                content_id={request.url},
            )
        else:
            raise HTTPException(status_code=500)

    except Exception as e:
        # logger.error(f"Error processing video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy"}