blog_prompt = """[INST] You are given the transcript of a Youtube Video.
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

affiliate_prompt = """
        [INST] You are given transcripts of youtube videos and product description.
        Read the transcripts and summarize the contents of the Youtube Videos to make a blog post reviewing and recommending the product.
        Focus on key points and main ideas. Use clear, professional language.
        Write a blog post and then summarize it to title, blog_desc and body.
        Include 5 categories and 5 keywords.
        RELY HEAVILY ON THE TRANSCRIPT FOR THE CONTENT. TRY TO ADD REFERENCES TO THE TRANSCRIPT.
        The body should contain atleast 6 to 7 Subheadings and 6 to 7 corresponding paragraphs.
        Each paragraph can have a maximum of 400 words minimum of 300 words.
        Refrain from using any content given in the prompt in the output.
        Refrain from using "Summary" or "Youtube" in the blog_desc. blog_desc should be a brief description atleast of the whole transcript, atleast 50 words.
        Refrain from using "Transcript" or "Summary" or "Youtube" or "Video" or "video" or "Speaker".
        Your Summary should include:
            1. title (Title of the Blog, Maximum 10 words)
            2. blog_desc (Overall Description of the blog content, Maximum of 69 words)
            3. body (Body content of the blog, consiting of a list of <h2> descriptive headings and <p> paragraphs explaining the content)
            4. categories (list of categories for the blog)
            5. keywords (list of keywords for the blog)
        Make sure that the body is a list of Points, Points is defined as follows:
            class Points(BaseModel):
                h2: str = Field("Descriptive Subheading, Maximum 10 words")
                p: str = Field("Paragraph, content of the blog, Maximum 150 words")

        Output JSON
"""

reel_prompt = """
        [INST] You are tasked to write the scripts to a viral youtube reels, given the prompt, write a script that satitesfies the prompt.
        Include a witty and catchy Title for the script.
        Include a caption for the reel script.
        Include 5 categories and 5 keywords for the Script.

        You are given the transcripts of a few youtube videos.
        
        RELY HEAVILY ON THE TRANSCRIPT FOR THE CONTENT. TRY TO ADD REFERENCES TO THE TRANSCRIPT.
        The reel script should be atleast 4 to 5 Subheadings and 4 to 5 corresponding paragraphs.
        Subheadings should be descriptive of corresponding paragraphs, this will be used as key to do tfidf search over the transcripts to find timestamps

        EACH SCRIPT SHOULD BE LONG ENOUGH TO READ FOR ONE MINUTE

        Refrain from using "Summary" or "Youtube" in the blog_desc. blog_desc should be a brief description atleast of the whole transcript, atleast 50 words.
        Refrain from using "Transcript" or "Summary" or "Youtube" or "Video" or "video" or "Speaker".
        
        WRITE A SCRIPT FOR REELS, Each reel should have the format:
        [
            {
                "title": str,
                "caption": str,
                "keywords": List[str],
                "categories": List[str],
                "body": [
                    ...4 such elements,
                    , {
                        "Subheading": str, //Subheading should be descriptive of the paragraph, this will be used as key to do tfidf search over the transcripts to find timestamps
                        "Paragrah": str, //the script of the reel, this will be read out in the video, this should be the narrators voice, and should be continuous and coherent
                    }
                ]
            }
        ]
        The first Two subheadings should be fast paced and appealing, intruiging curiosity, so the viewer is hooked.
        Follow popular youtube shorts intros.
        The Paragraph will be read out by a narrator sequentially, so it should be meaningful spoken english and should represent the content of the reel's audio.
        Ask for Subscriptions or likes at the end of the script, should be in the last Paragraph.

        Output JSON
"""

reel_prompt = """
        [INST] You are tasked to write the scripts to a viral youtube reels, given the prompt, write a script that satitesfies the prompt.
        Include a witty and catchy Title for the script.
        Include a caption for the reel script.
        Include 5 categories and 5 keywords for the Script.

        You are given the transcripts of a few youtube videos.
        
        RELY HEAVILY ON THE TRANSCRIPT FOR THE CONTENT. TRY TO ADD REFERENCES TO THE TRANSCRIPT.
        The reel script should be atleast 4 to 5 Subheadings and 4 to 5 corresponding paragraphs.
        Subheadings should be descriptive of corresponding paragraphs, this will be used as key to do tfidf search over the transcripts to find timestamps

        EACH SCRIPT SHOULD BE LONG ENOUGH TO READ FOR ONE MINUTE

        Refrain from using "Summary" or "Youtube" in the blog_desc. blog_desc should be a brief description atleast of the whole transcript, atleast 50 words.
        Refrain from using "Transcript" or "Summary" or "Youtube" or "Video" or "video" or "Speaker".
        
        WRITE A SCRIPT FOR REELS, Each reel should have the format:
        [
            {
                "title": str,
                "caption": str,
                "keywords": List[str],
                "categories": List[str],
                "body": [
                    ...4 such elements,
                    , {
                        "Subheading": str, //Subheading should be descriptive of the paragraph, this will be used as key to do tfidf search over the transcripts to find timestamps
                        "keyword": str, //keyword to use to search for videos on youtube, make it a crist 2-3 word keyword that can fetch a good footage for the reel from a youtube search
                        "Paragraph": str, //the script of the reel, this will be read out in the video, this should be the narrators voice, and should be continuous and coherent
                    }
                ]
            }
        ]
        The first Two subheadings should be fast paced and appealing, intruiging curiosity, so the viewer is hooked.
        Follow popular youtube shorts intros.
        The Paragraph will be read out by a narrator sequentially, so it should be meaningful spoken english and should represent the content of the reel's audio.
        Ask for Subscriptions or likes at the end of the script, should be in the last Paragraph.
        keyword to use to search for videos on youtube, make it a crist 2-3 word keyword that can fetch a good footage for the reel from a youtube search
        Make sure you Oupt an Array
        Output JSON
        No Extra Characters
"""

reel_script_prompt = """"
    [INST] You are tasked to write the scripts to a viral youtube/instagram reel, given the prompt, write a script that satitesfies the prompt.
        Include a witty and catchy Title for the script.
        Include a caption for the reel script.
        Include 5 categories and 5 keywords for the Script.

        You are given the transcripts of a few youtube videos.
        
        RELY HEAVILY ON THE TRANSCRIPT FOR THE CONTENT. TRY TO ADD REFERENCES TO THE TRANSCRIPT.
        The reel script should be atleast 4 to 5 Subheadings and 4 to 5 corresponding paragraphs.
        Subheadings should be descriptive of corresponding paragraphs, this will be used as key to do tfidf search over the transcripts to find timestamps

        EACH SCRIPT SHOULD BE LONG ENOUGH TO READ FOR ONE MINUTE

        Refrain from using "Summary" or "Youtube" in the blog_desc. blog_desc should be a brief description atleast of the whole transcript, atleast 50 words.
        Refrain from using "Transcript" or "Summary" or "Youtube" or "Video" or "video" or "Speaker".
        
        WRITE A SCRIPT FOR REELS, Each reel should have the format:
        [
            {
                "title": str,
                "caption": str,
                "keywords": List[str],
                "categories": List[str],
                "body": [
                    ...4 such elements,
                    , {
                        "Subheading": str, //Subheading should be descriptive of the paragraph, this will be used as key to do tfidf search over the transcripts to find timestamps
                        "keyword": str, //keyword to use to search for videos on youtube, make it a crist 2-3 word keyword that can fetch a good footage for the reel from a youtube search
                        "Paragraph": str, //the script of the reel, this will be read out in the video, this should be the narrators voice, and should be continuous and coherent
                    }
                ]
            }
        ]
        The first Two subheadings should be fast paced and appealing, intruiging curiosity, so the viewer is hooked.
        Follow popular youtube shorts intros.
        The Paragraph will be read out by a narrator sequentially, so it should be meaningful spoken english and should represent the content of the reel's audio.
        Ask for Subscriptions or likes at the end of the script, should be in the last Paragraph.
        keyword to use to search for videos on youtube, make it a crist 2-3 word keyword that can fetch a good footage for the reel from a youtube search
        Make sure you Oupt an Array
        Output JSON
        No Extra Characters
"""