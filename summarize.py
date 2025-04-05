from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
import json
load_dotenv()
app = FastAPI()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)



@app.post("/generate-text")
async def generate_text(transcript, prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash") # Or "gemini-pro"
        # transcript = text_input.text
        llm_input = f"""
        Transcript: {transcript}
        {prompt}
        """
        response = model.generate_content(
            llm_input,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json" # Enable JSON mode
            )
        )
        generate_text = json.loads(response.text)
        return {"generated_text": generate_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
@app.post("/generate-script")
async def generate_script(prompt):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash") # Or "gemini-pro"
        # transcript = text_input.text
        llm_input = f"""
        {prompt}
        """
        response = model.generate_content(
            llm_input,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json" # Enable JSON mode
            )
        )
        generate_text = json.loads(response.text)
        return {"generated_text": generate_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

