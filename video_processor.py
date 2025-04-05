import json
import os
from pathlib import Path
import subprocess

def concat_clips(reel_id: str) -> None:
    # Define paths
    base_path = Path(f'./data/reel/{reel_id}')
    clips_path = base_path / 'clips'
    summary_path = base_path / 'summary.json'
    
    # Read summary.json
    with open(summary_path, 'r') as f:
        summary = json.load(f)
    
    summary = json.loads(summary['generated_text'])
    # Extract subheadings
    subheadings = [section['Subheading'] for section in summary[0]['body']]
    
    # Loop through possible ids (0 to 5)
    for clip_id in range(6):
        # Generate expected filenames for this id
        clip_files = []
        for subheading in subheadings:
            filename = f"{'_'.join(subheading.split())}_{clip_id}.mp4"
            filepath = clips_path / filename
            
            if not filepath.exists():
                print(f"Missing clip for ID {clip_id}: {filename}")
                break
            clip_files.append(str(filepath))
        
        # If we have all clips for this id, concatenate them
        if len(clip_files) == len(subheadings):
            # Create temporary file list for ffmpeg
            temp_list = base_path / f'temp_list_{clip_id}.txt'
            with open(temp_list, 'w') as f:
                for clip in clip_files:
                    f.write(f"file '{clip}'\n")
            
            # Output path
            output_path = base_path / f'{clip_id}.mp4'
            
            # Concatenate using ffmpeg
            try:
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(temp_list),
                    '-c', 'copy',
                    str(output_path)
                ]
                subprocess.run(cmd, check=True)
                print(f"Successfully created {clip_id}.mp4")
            except subprocess.CalledProcessError as e:
                print(f"Error concatenating clips for ID {clip_id}: {e}")
            finally:
                # Clean up temporary file
                temp_list.unlink()

if __name__ == "__main__":
    # Example usage
    reel_id = "example_reel"
    concat_clips(reel_id)