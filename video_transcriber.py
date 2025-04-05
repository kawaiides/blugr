import os
import shutil
import cv2
from moviepy import ImageSequenceClip, AudioFileClip, VideoFileClip
from tqdm import tqdm
from whisper_wrapper import WhisperTranscriber

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.8
FONT_THICKNESS = 2
TEXT_COLOR = (255, 255, 255)  # White text
BG_COLOR = (0, 0, 0)          # Black background
LINE_SPACING = 5               # Spacing between lines
PADDING = 10 

class VideoTranscriber:
    def __init__(self, video_path, audio_path: str = None):
        self.model = WhisperTranscriber(model_size='base')
        self.video_path = video_path
        self.audio_path = audio_path
        self.text_array = []
        self.fps = 0
        self.char_width = 0
        self.scale_factor = 0.75  # New scale factor

    def transcribe_video(self):
        print('Transcribing video')
        result = self.model.transcribe(self.audio_path)
        text = result["segments"][0]["text"]
        textsize = cv2.getTextSize(text, FONT, FONT_SCALE, FONT_THICKNESS)[0]
        cap = cv2.VideoCapture(self.video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        asp = 16/9
        ret, frame = cap.read()
        width = frame[:, int(int(width - 1 / asp * height) / 2):width - int((width - 1 / asp * height) / 2)].shape[1]
        width = width - (width * 0.1)
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        self.char_width = int(textsize[0] / len(text))
        
        for j in tqdm(result["segments"]):
            print(j)
            lines = []
            text = j["text"]
            end = j["end"]
            start = j["start"]
            total_frames = int((end - start) * self.fps)
            start = start * self.fps
            total_chars = len(text)
            words = text.split(" ")
            i = 0
            
            while i < len(words):
                words[i] = words[i].strip()
                if words[i] == "":
                    i += 1
                    continue
                length_in_pixels = (len(words[i]) + 1) * self.char_width
                remaining_pixels = width - length_in_pixels
                line = words[i] 
                
                while remaining_pixels > 0:
                    i += 1 
                    if i >= len(words):
                        break
                    length_in_pixels = (len(words[i]) + 1) * self.char_width
                    remaining_pixels -= length_in_pixels
                    if remaining_pixels < 0:
                        continue
                    else:
                        line += " " + words[i]
                
                line_array = [line, int(start) + 15, int(len(line) / total_chars * total_frames) + int(start) + 15]
                start = int(len(line) / total_chars * total_frames) + int(start)
                lines.append(line_array)
                self.text_array.append(line_array)
        
        cap.release()
        print('Transcription complete')
    
    def extract_audio(self):
        print('Extracting audio')
        audio_path = os.path.join(os.path.dirname(self.video_path), "audio.mp3")
        video = VideoFileClip(self.video_path)
        audio = video.audio 
        audio.write_audiofile(audio_path)
        self.audio_path = audio_path
        print('Audio extracted')
    
    def wrap_text(self, text, max_width):
        """Split text into lines that fit within specified width."""
        lines = []
        words = text.split(' ')
        current_line = ''

        for word in words:
            test_line = f'{current_line} {word}'.strip()
            (width, _), _ = cv2.getTextSize(test_line, FONT, FONT_SCALE, FONT_THICKNESS)
            
            if width <= max_width:
                current_line = test_line
            else:
                if current_line == '':
                    # Handle case where single word exceeds width
                    lines.append(word)
                    current_line = ''
                else:
                    lines.append(current_line)
                    current_line = word
        
        if current_line:
            lines.append(current_line)
        return lines

    def draw_text_with_background(self, frame, text):
        """Draw text with background box and automatic wrapping (modified for overlay)"""
        frame_height, frame_width = frame.shape[:2]
        max_text_width = int(frame_width * 0.9 * self.scale_factor)  # Adjusted for scaled video

        # Split text into wrapped lines
        lines = self.wrap_text(text, max_text_width)
        if not lines:
            return frame

        # Calculate total text block dimensions
        line_heights = []
        total_height = 0
        max_line_width = 0
        
        for line in lines:
            (line_width, line_height), _ = cv2.getTextSize(line, FONT, FONT_SCALE, FONT_THICKNESS)
            line_heights.append(line_height)
            total_height += line_height + LINE_SPACING
            max_line_width = max(max_line_width, line_width)
        
        total_height -= LINE_SPACING  # Remove last spacing

        # Calculate background box position (top center)
        box_width = max_line_width + 2*PADDING
        box_height = total_height + 2*PADDING
        x = (frame_width - box_width) // 2
        y = PADDING * 2  # Position at top

        # Draw semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay,
                      (x, y),
                      (x + box_width, y + box_height),
                      BG_COLOR, -1)
        
        # Add transparency
        alpha = 0.6  # Adjust transparency level
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        # Draw each line of text
        y_text = y + PADDING + line_heights[0]
        for i, line in enumerate(lines):
            (line_width, line_height), _ = cv2.getTextSize(line, FONT, FONT_SCALE, FONT_THICKNESS)
            x_line = (frame_width - line_width) // 2
            cv2.putText(frame, line, (x_line, y_text),
                       FONT, FONT_SCALE, TEXT_COLOR, FONT_THICKNESS)
            
            if i < len(lines) - 1:
                y_text += line_heights[i] + LINE_SPACING
        
        return frame

    def extract_frames(self, output_folder):
        print('Extracting frames')
        cap = cv2.VideoCapture(self.video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        asp = width / height
        N_frames = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Create blurred background
            blurred = cv2.GaussianBlur(frame, (101, 101), 0)
            
            # Scale down the original frame
            scaled_frame = cv2.resize(frame, None, fx=self.scale_factor, fy=self.scale_factor)
            
            # Calculate position to center the scaled frame
            h, w = scaled_frame.shape[:2]
            y_offset = (height - h) // 2
            x_offset = (width - w) // 2
            
            # Create alpha channel for smooth edges
            alpha = np.zeros((h, w), dtype=np.uint8)
            cv2.ellipse(alpha, (w//2, h//2), (w//2, h//2), 0, 0, 360, 255, -1)
            alpha = cv2.GaussianBlur(alpha, (51, 51), 0)
            alpha = alpha[:, :, np.newaxis] / 255.0
            
            # Overlay scaled frame on blurred background with alpha blending
            region = blurred[y_offset:y_offset+h, x_offset:x_offset+w]
            blended = (region * (1 - alpha) + scaled_frame * alpha).astype(np.uint8)
            blurred[y_offset:y_offset+h, x_offset:x_offset+w] = blended
            
            # Add subtitles to the blurred composite frame
            composite_frame = self.draw_text_with_background(blurred, i[0])

            cv2.imwrite(os.path.join(output_folder, f"{N_frames}.jpg"), composite_frame)
            N_frames += 1

        cap.release()
        print('Frames extracted')
    
    def create_video(self, output_video_path):
        print('Creating video')
        image_folder = os.path.join(os.path.dirname(self.video_path), "frames")
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)
        
        self.extract_frames(image_folder)
        
        images = [img for img in os.listdir(image_folder) if img.endswith(".jpg")]
        images.sort(key=lambda x: int(x.split(".")[0]))
        
        frame = cv2.imread(os.path.join(image_folder, images[0]))
        height, width, layers = frame.shape
        
        clip = ImageSequenceClip([os.path.join(image_folder, image) for image in images], fps=self.fps)
        audio = AudioFileClip(self.audio_path)
        clip = clip.with_audio(audio)
        clip.write_videofile(output_video_path)
        shutil.rmtree(image_folder)

# Example usage
model_path = "base"
# video_path = "test_videos/videoplayback.mp4"
output_video_path = "output.mp4"
# output_audio_path = "test_videos/audio.mp3"
    