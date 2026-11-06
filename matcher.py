import json
import os
from typing import Literal

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from pypdf import PdfReader

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Set it in a .env file as GEMINI_API_KEY=...")


class JobMatchResult(BaseModel):
    suitability: Literal["Perfect Match", "Good Match", "Stretch Role", "Unsuitable"]
    matching_skills: list[str]
    missing_skills: list[str]
    analysis_summary: str


def extract_resume_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def main() -> None:
    client = genai.Client(api_key=GEMINI_API_KEY)

    resume_text = extract_resume_text("resume.pdf")

    job_description = """
    PASTE THE TARGET JOB DESCRIPTION HERE.
    """

    prompt = f"""You are an expert technical recruiter. Compare the CANDIDATE RESUME against the
JOB DESCRIPTION and evaluate the candidate's suitability for the role.

CANDIDATE RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=JobMatchResult,
        ),
    )

    result: JobMatchResult = response.parsed

    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()
