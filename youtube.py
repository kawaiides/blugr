from yt_dlp import YoutubeDL
from tqdm_decorator import with_tqdm, timeout
import json
import subprocess
import os
import requests

from yt_dlp import YoutubeDL

class Youtube():
    def __init__(self):
        # Directly use the cookies.txt file in the root directory
        self.cookiesfile = './cookies.txt'
        self.ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,
        }

    @with_tqdm
    def download_audio_from_url(self, url):
        print("Downloading audio...")
        videoinfo = YoutubeDL({'cookiefile': self.cookiesfile}).extract_info(url=url, download=False)
        length = videoinfo['duration']
        filename = f"./data/youtube/{videoinfo['id']}/audio.mp3"
        options = {
            'format': 'bestaudio/best',
            'keepvideo': False,
            'outtmpl': filename,
            'cookiefile': self.cookiesfile,
        }
        with YoutubeDL(options) as ydl:
            ydl.download([videoinfo['webpage_url']])
        return filename, length

    @with_tqdm
    def download_video(self, url):
        videoinfo = YoutubeDL({'cookiefile': self.cookiesfile}).extract_info(url=url, download=False)
        length = videoinfo['duration']
        filename = f"./data/youtube/{videoinfo['id']}/video.mp4"
        ydl_opts = {
            'outtmpl': filename,
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'cookiefile': self.cookiesfile,
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return filename, length

    @with_tqdm
    def get_most_replayed(self, url):
        with YoutubeDL({'cookiefile': self.cookiesfile}) as ydl:
            info_dict = ydl.extract_info(f"{url}", download=False)
            filename = f"./data/youtube/{info_dict['id']}"
            filename = f"{filename}/replay_info.json"
            with open(f"{filename}", 'w') as f:
                json.dump(info_dict.get('heatmap'), f, indent=4)
            return filename
    
    @with_tqdm
    def save_thumbnail(self, video_url, save_path):
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'cookiefile': self.cookiesfile,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            thumbnail_url = info_dict.get('thumbnail', None)
            
            if thumbnail_url:
                response = requests.get(thumbnail_url)
                if response.status_code == 200:
                    with open(save_path, 'wb') as file:
                        file.write(response.content)
                    print(f"Thumbnail saved to {save_path}")
                else:
                    print(f"Failed to download thumbnail. HTTP status code: {response.status_code}")
            else:
                print("Thumbnail not found.")

    @timeout(120)
    def take_screenshot(self, video_path, screenshots_dir, timestamp, id):
        try:
            if not os.path.exists(screenshots_dir):
                os.makedirs(screenshots_dir)
                print(f"Folder '{screenshots_dir}' created successfully.")
            else:
                print(f"Folder '{screenshots_dir}' already exists.")
        except OSError as error:
            print(f"Error creating folder '{screenshots_dir}': {error}")

        output_path = os.path.join(screenshots_dir, f"{id}.png")
        command = [
            'ffmpeg',
            '-i', video_path+'video.mp4',
            '-ss', timestamp,
            '-vframes', '1',
            output_path
        ]
        
        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Screenshot saved at {output_path}")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while taking the screenshot: {e.stderr.decode()}")
        except FileNotFoundError:
            print("FFmpeg is not installed or not found in the PATH.")

    @timeout(120)
    def make_gif_most_viewed(self, video_path, start, duration):

        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        command = [
            'ffmpeg', 
            '-ss', start,
            '-t', duration,
            '-i', video_path,
            '-vf', f"fps=10,scale=640:-1:flags=lanczos",
            '-c:v', 'gif',
            '-y',
            '/'.join(video_path.split('/')[:-1])+'/most_watched.gif'
        ]

        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"GIF created at {video_path+'most_watched.gif'}")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while creating the GIF: {e.stderr.decode()}")
        except FileNotFoundError:
            print("FFmpeg is not installed or not found in the PATH.")

    @timeout(120)
    def search_videos(self, product_name, max_results=5):
        """Search YouTube videos using yt-dlp and return top most viewed long-form videos (excluding Shorts)"""
        try:
            videos = []
            search_query = f"ytsearch20:{product_name}"  # Get 20 results to find top viewed
            
            with YoutubeDL(self.ydl_opts) as ydl:
                result = ydl.extract_info(search_query, download=False)
                entries = result.get('entries', [])[:20]  # Get first 20 results

            # Get detailed info for each video to find view counts and filter Shorts
            detailed_videos = []
            for entry in entries:
                if entry.get('url'):
                    try:
                        with YoutubeDL({'quiet': True, 'skip_download': True}) as vid_ydl:
                            info = vid_ydl.extract_info(entry['url'], download=False)
                            duration = info.get('duration', 0)
                            # Skip videos with duration <=60 seconds (Shorts)
                            if duration <= 60:
                                continue
                            detailed_videos.append({
                                'url': entry['url'],
                                'title': info.get('title'),
                                'view_count': info.get('view_count', 0),
                                'duration': duration,
                                'id': info.get('id')
                            })
                    except Exception as e:
                        print(f"Error processing video {entry['url']}: {str(e)}")
                        continue

            # Sort by view count descending and return top results
            sorted_videos = sorted(detailed_videos, 
                                key=lambda x: x['view_count'], 
                                reverse=True)
            return sorted_videos[:max_results]

        except Exception as e:
            print(f"YouTube search failed: {str(e)}")
            return []