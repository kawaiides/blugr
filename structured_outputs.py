from pydantic import BaseModel, Field

class Points(BaseModel):
    h2: str = Field("Descriptive Subheading, Maximum 10 words")
    p: str = Field("Paragraph, content of the blog, Maximum 150 words")

class Summary(BaseModel):
    title: str = Field("Title of the Blog, Maximum 10 words")
    blog_desc: str = Field("Description of the blog, Maximum 69 words")
    body: list[Points] = Field("Body content of the blog, consiting of a list of <h2> headings and <p> paragraphs")

class Timestamp(BaseModel):
    start: float = Field(description="Starting timestamp")
    end: float = Field(description="Ending timestamp")
    description: str = Field(description="Description of Image based on the transcript")
    h2: str = Field(description="Sub")

class ClipperOutput(BaseModel):
    timestamps: list[Timestamp] = Field(description="list of timestamps")