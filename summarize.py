import warnings
import asyncio
from ollama import AsyncClient
from structured_outputs import Summary
import json

async def summarizer_chat(transcript):
    message = {
      'role': 'user',
      'content': \
        f"""
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
        """,
    }
    response = await AsyncClient().chat(
        messages=[
            message
        ],
        model='llama3.2:latest',
        format=Summary.model_json_schema(),
    )
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        summarizer_output = Summary.model_validate_json(response.message.content)
        if w:
            summarizer_chat(transcript)
            
    return summarizer_output


if __name__ == "__main__":
    """
        C:/Users/Asus-2023/blooogerai/llm_stuff/data/transcriptions/y1jrZ6gP2Tg.mp3_text_timestamp.txt
    """
    transcript_path = input("input transcript_path to summarize: ")
    with open(f"{transcript_path}", "r") as file:
        transcript = file.read()
    response = asyncio.run(summarizer_chat(transcript))
    res = response.model_dump(mode='json')
    with open(f"./data/youtube/{transcript_path.split('/')[-2]}/summary.json", "w") as f:
        json.dump(res, f, indent=4)
