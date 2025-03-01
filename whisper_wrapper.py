# whisper_wrapper.py
from faster_whisper import WhisperModel
import os


class WhisperTranscriber:
    def __init__(self, model_size='base', device='cpu', compute_type='int8'):
        """
        Initialize Whisper model
        model_size: 'tiny', 'base', 'small', 'medium', 'large'
        device: 'cpu' or 'cuda' for GPU
        compute_type: 'int8', 'int16', 'float16', or 'float32'
        """
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_path):
        """
        Transcribe audio file and return both full text and segments
        """
        try:
            print("Loading data and transcribing...")
            # Perform transcription
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=5,
                word_timestamps=True
            )

            print(f"Detected language: {info.language} with probability: {info.language_probability}")

            # Process segments
            processed_segments = []
            full_text = []

            print("Processing segments...")
            for i, segment in enumerate(segments):
                # Print progress every 10 segments
                if i % 10 == 0:
                    print(f"Processing segment {i}...")

                processed_segments.append({
                    "id": i,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "words": [
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": word.probability
                        }
                        for word in segment.words
                    ] if segment.words else []
                })
                full_text.append(segment.text.strip())

            print("Transcription completed!")

            result = {
                "transcription": " ".join(full_text),
                "segments": processed_segments,
                "language": info.language,
                "language_probability": info.language_probability
            }

            # Print some statistics
            print(f"Total segments: {len(processed_segments)}")
            print(f"Total words: {sum(len(seg['words']) for seg in processed_segments)}")
            print(f"Transcript length: {len(result['transcription'])} characters")

            return result

        except Exception as e:
            print(f"Transcription error: {str(e)}")
            raise

    def generate_srt(self, segments, output_file):
        """Generate SRT subtitle file from segments"""

        def format_time(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            seconds = seconds % 60
            milliseconds = int((seconds - int(seconds)) * 1000)
            return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(segments, 1):
                    f.write(f"{i}\n")
                    f.write(f"{format_time(segment['start'])} --> {format_time(segment['end'])}\n")
                    f.write(f"{segment['text']}\n\n")
            print(f"SRT file saved to: {output_file}")
            return True
        except Exception as e:
            print(f"Error generating SRT: {str(e)}")
            return False