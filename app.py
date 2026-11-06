from io import BytesIO
from typing import Literal, Optional

import docx
import streamlit as st
from openai import InternalServerError, OpenAI
from pydantic import BaseModel
from pypdf import PdfReader


class JobMatchResult(BaseModel):
    suitability: Literal["Perfect Match", "Good Match", "Stretch Role", "Unsuitable"]
    matching_skills: list[str]
    missing_skills: list[str]
    experience_alignment: list[str]
    experience_gap_mitigation: str
    analysis_summary: str


SUITABILITY_STYLE = {
    "Perfect Match": ("🟢", "success"),
    "Good Match": ("🟢", "success"),
    "Stretch Role": ("🟠", "warning"),
    "Unsuitable": ("🔴", "error"),
}


def extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_docx(file_bytes):
    doc = docx.Document(BytesIO(file_bytes))
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return "\n".join(full_text)


def analyze(resume_text: str, job_description: str) -> JobMatchResult:
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    system_message = (
        "You are an expert technical recruiter. Compare the CANDIDATE RESUME against the "
        "JOB DESCRIPTION and evaluate the candidate's suitability for the role."
    )

    prompt_text = f"""In the experience_alignment section, evaluate how the candidate's professional work experience,
past job roles, and career timeline prepare them for this target position.

If the job description asks for a specific number of years of experience (e.g., 2 years) but is
listed as junior/entry-level, analyze how the candidate's technical project depth or adjacent
stack knowledge can mitigate this gap. Provide a 2-sentence tactical recommendation in the
experience_gap_mitigation field.

CANDIDATE RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}
"""

    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt_text},
    ]

    try:
        response = client.beta.chat.completions.parse(
            model="llama3.1",
            messages=messages,
            response_format=JobMatchResult,
        )
    except InternalServerError as e:
        print(f"WARNING: llama3.1 request failed ({e}). Retrying once...")
        response = client.beta.chat.completions.parse(
            model="llama3.1",
            messages=messages,
            response_format=JobMatchResult,
        )

    return response.choices[0].message.parsed


st.set_page_config(page_title="Job Match Analyzer", page_icon="🎯", layout="centered")
st.title("🎯 Job Match Analyzer")
st.caption("Upload a resume and paste a job description to get an instant AI-powered suitability analysis.")

resume_file = st.file_uploader("Upload your resume", type=["pdf", "docx"])
job_description = st.text_area(
    "Paste the job description",
    height=250,
    placeholder="Paste the full job description here...",
)

analyze_clicked = st.button("Analyze My Resume", type="primary", use_container_width=True)

if analyze_clicked:
    if not resume_file:
        st.warning("Please upload a resume (PDF or DOCX) first.")
    elif not job_description.strip():
        st.warning("Please paste a job description first.")
    else:
        with st.spinner("Analyzing resume with Ollama..."):
            if resume_file.name.lower().endswith(".pdf"):
                resume_text = extract_pdf_text(resume_file.getvalue())
            elif resume_file.name.lower().endswith(".docx"):
                resume_text = extract_text_from_docx(resume_file.getvalue())
            st.session_state["result"] = analyze(resume_text, job_description)

result: Optional[JobMatchResult] = st.session_state.get("result")

if result:
    st.divider()

    emoji, style = SUITABILITY_STYLE[result.suitability]
    getattr(st, style)(f"{emoji} **Suitability: {result.suitability}**")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("✅ Matching Skills")
        if result.matching_skills:
            for skill in result.matching_skills:
                st.markdown(f"- {skill}")
        else:
            st.markdown("_None found_")

    with col2:
        st.subheader("❌ Missing Skills")
        if result.missing_skills:
            for skill in result.missing_skills:
                st.markdown(f"- {skill}")
        else:
            st.markdown("_None found_")

    st.subheader("💼 Work Experience Evaluation")
    if result.experience_alignment:
        for point in result.experience_alignment:
            st.markdown(f"- {point}")
    else:
        st.markdown("_None found_")

    st.markdown("💡 **Strategic Portfolio Advice:** " + result.experience_gap_mitigation)

    st.subheader("📝 Analysis Summary")
    st.info(result.analysis_summary)
