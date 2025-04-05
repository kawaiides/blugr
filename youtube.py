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
        try:
            videoinfo = YoutubeDL({'cookiefile': self.cookiesfile}).extract_info(url=url, download=False)
            length = videoinfo['duration']
            filename_base = f"./data/youtube/{videoinfo['id']}/audio"
            
            # More flexible format selection
            # options = {
            #     'format': 'bestaudio/best',
            #     'postprocessors': [{
            #         'key': 'FFmpegExtractAudio',
            #         'preferredcodec': 'mp3',
            #         'preferredquality': '192',
            #     }],
            #     'outtmpl': filename_base,
            #     'cookiefile': self.cookiesfile,
            #     'force_generic_extractor': True,  # Bypass age restrictions
            #     'format_sort': ['ext:mp3', 'm4a', 'aac'],  # Prioritize direct audio formats
            #     'postprocessor_args': ['-ar', '44100'],  # Standard sampling rate
            #     'verbose': True  # For debugging
            # }

            options = {
                'outtmpl': filename_base,
                'format': '233/234/bestaudio/best',
                'merge_output_format': 'mp3',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'cookiefile': self.cookiesfile,
                'ignoreerrors': True,
                'force_generic_extractor': True,
            }

            # Attempt download with fallback
            with YoutubeDL(options) as ydl:
                try:
                    ydl.download([url])
                except Exception as e:
                    print(f"Primary download failed: {e}")
                    # Fallback to video format extraction
                    options['format'] = 'bestvideo[ext=mp4]+bestaudio/best'
                    ydl.params.update(options)
                    ydl.download([url])

            return f"{filename_base}.mp3", length

        except Exception as e:
            print(f"Final download failure: {e}")
            raise RuntimeError(f"Could not download audio: {str(e)}")

    @with_tqdm
    def download_video(self, url):
        videoinfo = YoutubeDL({'cookiefile': self.cookiesfile}).extract_info(url=url, download=False)
        length = videoinfo['duration']
        filename = f"./data/youtube/{videoinfo['id']}/video.mp4"
        ydl_opts = {
            'outtmpl': filename,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'cookiefile': self.cookiesfile,
            'merge_output_format': 'mp4',  # Ensures compatibility
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',  # fallback
            }],
        }
        # ydl_opts = {
        #     'outtmpl': filename,
        #     'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        #     'cookiefile': self.cookiesfile,
        # }
        if length <= 60*30:
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
    def save_video_clip(self, video_path, output_dir, start_time, end_time, clip_id):
        """
        Save a video clip from a source video between specified timestamps.
        
        Args:
            video_path (str): Full path to the input video file.
            output_dir (str): Directory to save the output clip.
            start_time (str): Start timestamp (e.g., "00:01:23").
            end_time (str): End timestamp (e.g., "00:02:45").
            clip_id (str/num): Unique identifier for the output filename.
        """
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                print(f"Folder '{output_dir}' created successfully.")
            else:
                print(f"Folder '{output_dir}' already exists.")
        except OSError as error:
            print(f"Error creating folder '{output_dir}': {error}")
            return

        output_path = os.path.join(output_dir, f"{clip_id}.mp4")
        command = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-i', video_path,
            '-ss', start_time,
            '-to', end_time,
            '-c:v', 'libx264',  # H.264 video codec
            '-c:a', 'aac',      # AAC audio codec
            '-preset', 'fast',  # Speed/quality tradeoff
            '-crf', '23',       # Quality level (0-51, lower is better)
            output_path
        ]
        
        try:
            subprocess.run(
                command, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            print(f"Video clip saved at {output_path}")
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.decode()
            print(f"Error saving video clip: {error_message}")
            if "Invalid duration" in error_message:
                print("Possible cause: End time is before start time")
            elif "Invalid argument" in error_message:
                print("Possible cause: Invalid timestamp format (use HH:MM:SS)")
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
        print(f"searching for {product_name}")
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
                            if duration >= 60*30:
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