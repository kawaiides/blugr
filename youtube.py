from yt_dlp import YoutubeDL
from tqdm_decorator import with_tqdm, timeout
import json
import subprocess
import os
import requests

from yt_dlp import YoutubeDL
import browser_cookie3

class Youtube():
    def __init__(self):
        # Get cookies from your browser (choose the browser you use)
        try:
            # Try Chrome first
            cookies = browser_cookie3.chrome(domain_name='.youtube.com')
        except:
            try:
                # Try Firefox if Chrome fails
                cookies = browser_cookie3.firefox(domain_name='.youtube.com')
            except:
                print("Could not load cookies from Chrome or Firefox")
                cookies = None

        # Convert cookies to the format yt-dlp expects
        self.cookiesfile = './youtube.com_cookies.txt'
        if cookies:
            with open(self.cookiesfile, 'w') as f:
                for cookie in cookies:
                    if cookie.domain.endswith('.youtube.com'):
                        f.write(f"{cookie.domain}\tTRUE\t{cookie.path}\t"
                              f"{'TRUE' if cookie.secure else 'FALSE'}\t{cookie.expires}\t"
                              f"{cookie.name}\t{cookie.value}\n")

    @with_tqdm
    def download_audio_from_url(self, url):
        print("Downloading audio...")
        videoinfo = YoutubeDL({'cookiesfile': self.cookiesfile}).extract_info(url=url, download=False)
        length = videoinfo['duration']
        filename = f"./data/youtube/{videoinfo['id']}/audio.mp3"
        options = {
            'format': 'bestaudio/best',
            'keepvideo': False,
            'outtmpl': filename,
            'cookiesfile': self.cookiesfile,
        }
        with YoutubeDL(options) as ydl:
            ydl.download([videoinfo['webpage_url']])
        return filename, length

    @with_tqdm
    def download_video(self, url):
        videoinfo = YoutubeDL({'cookiesfile': self.cookiesfile}).extract_info(url=url, download=False)
        length = videoinfo['duration']
        filename = f"./data/youtube/{videoinfo['id']}/video.mp4"
        ydl_opts = {
            'outtmpl': filename,
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'cookiesfile': self.cookiesfile,
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return filename, length

    @with_tqdm
    def get_most_replayed(self, url):
        with YoutubeDL({'cookiesfile': self.cookiesfile}) as ydl:
            info_dict = ydl.extract_info(f"{url}", download=False)
            filename = f"./data/youtube/{info_dict['id']}"
            with open(f"{filename}/replay_info.json", 'w') as f:
                json.dump(info_dict.get('heatmap'), f, indent=4)
    
    @with_tqdm
    def save_thumbnail(self, video_url, save_path):
        ydl_opts = {
            'quiet': True,  # Suppress output
            'extract_flat': True,  # Avoid downloading the video itself
            'force_generic_extractor': True,  # Use a generic extractor
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            thumbnail_url = info_dict.get('thumbnail', None)
            
            if thumbnail_url:
                # Get the image from the URL
                response = requests.get(thumbnail_url)
                if response.status_code == 200:
                    # Save the image to disk
                    with open(save_path, 'wb') as file:
                        file.write(response.content)
                    print(f"Thumbnail saved to {save_path}")
                else:
                    print(f"Failed to download thumbnail. HTTP status code: {response.status_code}")
            else:
                print("Thumbnail not found.")

    @timeout(120)
    def take_screenshot(self, video_path, timestamp, id):
        try:
            # Check if the directory exists
            if not os.path.exists(video_path+'screenshots'):
                # Create the directory
                os.makedirs(video_path+'screenshots')
                print(f"Folder '{video_path+'screenshots'}' created successfully.")
            else:
                print(f"Folder '{video_path+'screenshots'}' already exists.")
        except OSError as error:
            print(f"Error creating folder '{video_path+'screenshots'}': {error}")

        output_path = os.path.join(video_path+'screenshots', f"{id}.png")
        command = [
            'ffmpeg',
            '-i', video_path+'video.mp4',
            '-ss', timestamp,
            '-vframes', '1',
            output_path
        ]
        
        try:
            # Run FFmpeg command
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Screenshot saved at {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while taking the screenshot: {e.stderr.decode()}")
        except FileNotFoundError:
            print("FFmpeg is not installed or not found in the PATH.")

    @timeout(120)
    def make_gif_most_viwed(self, video_path, start, duration):
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        # FFmpeg command for converting video to GIF
        command = [
            'ffmpeg', 
            '-ss', start,  # Start time
            '-t', duration,     # Duration
            '-i', video_path+'video.mp4',   # Input file
            '-vf', f"fps=10,scale=640:-1:flags=lanczos",  # Set frame rate and scale
            '-c:v', 'gif',      # Video codec for output
            '-y',               # Overwrite output file if it exists
            video_path+'most_watched.gif'         # Output file path
        ]

        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"GIF created at {video_path+'most_watched.gif'}")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while creating the GIF: {e.stderr.decode()}")
        except FileNotFoundError:
            print("FFmpeg is not installed or not found in the PATH.")
