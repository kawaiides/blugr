# Blugr: YouTube Video Processing Tool

A comprehensive tool for processing YouTube videos, extracting and analyzing their content through transcription, summarization, and insights generation.

## Features

- **YouTube Video Download**: Easily download videos from YouTube
- **Audio Transcription**: Convert speech to text using advanced transcription
- **Content Summarization**: Generate concise summaries of video content
- **Key Insights Extraction**: Identify and extract important information and moments
- **TF-IDF Based Search**: Search through transcribed content efficiently
- **Web Interface**: Access all functionality through a convenient FastAPI web application

## Prerequisites

- Python 3.8 or higher
- ffmpeg (required for audio processing)
- Internet connection for downloading YouTube videos

## Setup Instructions

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/blugr.git
cd blugr
```

### Step 2: Create and Activate a Virtual Environment

#### For macOS and Linux:
```bash
python -m venv venv
source venv/bin/activate
```

#### For Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
brew install ffmpeg
brew install espeak-ng
```

> **Compatibility Notes**:
> - This project uses FastAPI 0.111.0+ which requires compatible versions of pydantic (>=2.10.0)
> - If you encounter errors with pydantic-core, make sure typing_extensions is version 4.12.2 or higher
> - The whispercpp library is installed directly from GitHub and may require additional setup

### Step 4: Environment Configuration

Create a `.env` file in the root directory with the following variables:

```
MONGODB_URL=your_mongodb_connection_string
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_BUCKET_NAME=your_s3_bucket_name
REGION_NAME=your_aws_region
```

## Usage

### Starting the Server

```bash
uvicorn server_fastapi:app --reload
```

This will start the server at `http://localhost:8000`

### API Endpoints

- **POST /video**: Submit a YouTube URL for processing
  ```bash
  curl -X POST "http://localhost:8000/video" -H "Content-Type: application/json" -d '{"youtube_url": "https://www.youtube.com/watch?v=your_video_id"}'
  ```

- **GET /video/{video_id}**: Get information about a processed video
  ```bash
  curl -X GET "http://localhost:8000/video/your_video_id"
  ```

- **GET /search/{query}**: Search through transcribed content
  ```bash
  curl -X GET "http://localhost:8000/search/your_search_term"
  ```

### Web Interface

Access the web interface by navigating to `http://localhost:8000` in your browser.

## Advanced Configuration

### Customizing Transcription

You can adjust the transcription parameters in the `app.py` file:

```python
whisper = WhisperCpp()
whisper.params.language = "en"
whisper.params.n_threads = 4
```

### Adjusting Summarization Settings

Modify summarization behavior in the `summarize.py` file.

## Troubleshooting

### Common Issues

1. **ffmpeg not found**: Ensure ffmpeg is installed and in your PATH
2. **Dependency conflicts**: If you encounter conflicts, try installing with:
   ```bash
   pip install -r requirements.txt --no-dependencies
   ```
   Then manually install conflicting packages

3. **Transcription errors**: Make sure you have sufficient disk space and memory

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# blugr

## mac
python -m venv myenv
source myenv/bin/activate
brew install ffmpeg
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
pip install -r requirements.txt
brew install nginx # will set default port 8080



## linux
sudo apt update
sudo apt install python3-pip
sudo apt install ffmpeg
pip install -r requirements.txt
sudo apt install nginx
cd /etc/nginx/sites-enabled/
sudo vim fastapi_nginx
"""
    server {
    listen 80;
    server_name <public ipv4 address here>;
    location / {
        proxy_pass http://127.0.0.1:8000;
        }
    }
"""
sudo service nginx restart
python3 -m uvicorn main:app --reload