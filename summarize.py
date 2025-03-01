from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os

load_dotenv()
app = FastAPI()
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)



@app.post("/generate-text")
async def generate_text(transcript):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash") # Or "gemini-pro"
        # transcript = text_input.text
        llm_input = f"""
        Transcript: {transcript}
        
        [INST] You are given the transcript of a Youtube Video.
        Read the transcript and summarize the contents of the Youtube Video.
        Focus on key points and main ideas. Use clear, professional language.
        Write a blog post and then summarize it to title, blog_desc and body.
        RELY HEAVILY ON THE TRANSCRIPT FOR THE CONTENT. TRY TO ADD REFERENCES TO THE TRANSCRIPT.
        The body should contain atleast 3 to 4 Subheadings and 3 to 4 corresponding paragraphs.
        Each paragraph can have a maximum of 200 words minimum of 100 words.
        Refrain from using any content given in the prompt in the output.
        Refrain from using "Summary" or "Youtube" in the blog_desc. blog_desc should be a brief description atleast of the whole transcript, atleast 50 words.
        Refrain from using "Transcript" or "Summary" or "Youtube" or "Video" or "video" or "Speaker".
        Your Summary should include:
            1. title (Title of the Blog, Maximum 10 words)
            2. blog_desc (Overall Description of the blog content, Maximum of 69 words)
            3. body (Body content of the blog, consiting of a list of <h2> descriptive headings and <p> paragraphs explaining the content)
        Make sure that the body is a list of Points, Points is defined as follows:
            class Points(BaseModel):
                h2: str = Field("Descriptive Subheading, Maximum 10 words")
                p: str = Field("Paragraph, content of the blog, Maximum 150 words")

        Output JSON
        """
        response = model.generate_content(
            llm_input,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json" # Enable JSON mode
            )
        )
        return {"generated_text": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

