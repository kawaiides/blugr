import argparse
import asyncio
import json
import os
from main import create_final_reel  # Replace with actual module name

async def main(reel_id, voice="en_1"):
    base_path = f"./data/reel/{reel_id}"
    summary_path = os.path.join(base_path, "summary.json")
    voiceover_dir = os.path.join(base_path, 'voiceovers')
    
    # Load summary data
    with open(summary_path, 'r') as f:
        summary_data = json.load(f)
    
    # Create output directory
    os.makedirs(voiceover_dir, exist_ok=True)
    
    # Generate voiceovers
    audio_files = await create_final_reel(
        reel_id
    )
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate AI voiceover for reel content')
    parser.add_argument('--reel_id', required=True, help='ID of the reel')
    parser.add_argument('--voice', default='en_1', help='Voice model (en_1, en_2, etc)')
    
    args = parser.parse_args()
    
    asyncio.run(main(
        reel_id=args.reel_id,
        voice=args.voice,
    ))