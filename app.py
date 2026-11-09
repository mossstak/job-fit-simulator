import json
import os
import sqlite3
from datetime import datetime
from io import BytesIO
from typing import Literal, Optional

import docx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from openai import InternalServerError, OpenAI
from pydantic import BaseModel
from pypdf import PdfReader

DB_PATH = "jobs_history.db"


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


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            job_title TEXT,
            suitability TEXT,
            matching_skills TEXT,
            missing_skills TEXT,
            experience_alignment TEXT,
            experience_gap_mitigation TEXT,
            analysis_summary TEXT,
            job_url TEXT
        )
        """
    )
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(matches)")}
    for column in (
        "matching_skills",
        "missing_skills",
        "experience_alignment",
        "experience_gap_mitigation",
        "job_url",
    ):
        if column not in existing_columns:
            try:
                conn.execute(f"ALTER TABLE matches ADD COLUMN {column} TEXT")
            except sqlite3.OperationalError:
                pass
    conn.commit()
    conn.close()


def log_match(
    job_title: str,
    suitability: str,
    matching_skills: list[str],
    missing_skills: list[str],
    experience_alignment: list[str],
    experience_gap_mitigation: str,
    analysis_summary: str,
    job_url: str = "",
) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO matches (
            timestamp, job_title, suitability, matching_skills, missing_skills,
            experience_alignment, experience_gap_mitigation, analysis_summary, job_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(timespec="seconds"),
            job_title,
            suitability,
            json.dumps(matching_skills),
            json.dumps(missing_skills),
            json.dumps(experience_alignment),
            experience_gap_mitigation,
            analysis_summary,
            job_url,
        ),
    )
    conn.commit()
    conn.close()


def fetch_history() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT id, timestamp, job_title, suitability, matching_skills, missing_skills,
               experience_alignment, experience_gap_mitigation, analysis_summary, job_url
        FROM matches ORDER BY id DESC
        """,
        conn,
    )
    conn.close()
    return df


def _safe_json_loads(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return json.loads(value)


def derive_job_title(job_description: str) -> str:
    first_line = next((line.strip() for line in job_description.splitlines() if line.strip()), "Untitled Role")
    return first_line[:150]


def extract_pdf_text(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_docx(file_bytes):
    doc = docx.Document(BytesIO(file_bytes))
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return "\n".join(full_text)


# Engine Configurations
ENGINE_GEMINI = "Gemini (Cloud / High Precision)"
ENGINE_OLLAMA = "Ollama Local (Qwen 2.5 / Offline)"

GEMINI_PRIMARY_MODEL = "gemini-3.8-flash"
GEMINI_FALLBACK_MODEL = "gemini-3.5-flash-lite"

# Set to "qwen2.5:14b" (or "qwen2.5" / "qwen2.5:7b" depending on which model you pulled in Ollama)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")

SYSTEM_MESSAGE = """You are a precise, objective Technical Recruiter and Hiring Manager.
Evaluate the candidate's CV against the job description with balanced realism.

EVALUATION GUIDELINES:
- matching_skills: List specific tools, programming languages, and core technical skills that exist on both the CV and the job description (e.g., C#, Unity, Git, SQL). Do not omit a language simply because it was used in an academic or personal setting.
- missing_skills: List ONLY tools, technologies, and technical domain practices explicitly required by the job description that do NOT appear on the candidate's CV (e.g., mobile memory profiling, live-service deployment pipelines).
- suitability:
  * 'Perfect Match': 90%+ match across technical stack AND required seniority level.
  * 'Good Match': Core technical skills match; candidate meets the target seniority.
  * 'Stretch Role': Candidate has core fundamentals but is stepping up one level (e.g., Junior to Mid, or Mid to Senior).
  * 'Unsuitable': Severe structural mismatch (e.g., Junior applying for Team Lead/Principal), or missing the primary programming language/domain completely. Non-technical leadership (e.g., retail/hospitality shift lead) cannot substitute for software engineering leadership."""


def build_user_prompt(resume_text: str, job_description: str) -> str:
    return f"""Evaluate candidate alignment:

CANDIDATE RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}"""


def analyze_with_gemini(resume_text: str, job_description: str) -> JobMatchResult:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Set it in a .env file as GEMINI_API_KEY=...")

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_MESSAGE,
        response_mime_type="application/json",
        response_schema=JobMatchResult,
    )
    prompt_text = build_user_prompt(resume_text, job_description)

    try:
        response = client.models.generate_content(
            model=GEMINI_PRIMARY_MODEL, contents=prompt_text, config=config
        )
    except genai_errors.APIError as e:
        print(f"WARNING: {GEMINI_PRIMARY_MODEL} request failed ({e}). Falling back to {GEMINI_FALLBACK_MODEL}...")
        response = client.models.generate_content(
            model=GEMINI_FALLBACK_MODEL, contents=prompt_text, config=config
        )

    if response.parsed is not None:
        return response.parsed
    return JobMatchResult.model_validate_json(response.text)


def analyze_with_ollama(resume_text: str, job_description: str) -> JobMatchResult:
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": build_user_prompt(resume_text, job_description)},
    ]

    try:
        response = client.beta.chat.completions.parse(
            model=OLLAMA_MODEL,
            messages=messages,
            response_format=JobMatchResult,
            temperature=0.0,
        )
    except InternalServerError as e:
        print(f"WARNING: {OLLAMA_MODEL} request failed ({e}). Retrying once...")
        response = client.beta.chat.completions.parse(
            model=OLLAMA_MODEL,
            messages=messages,
            response_format=JobMatchResult,
            temperature=0.0,
        )

    return response.choices[0].message.parsed


def analyze(resume_text: str, job_description: str, engine: str) -> JobMatchResult:
    if engine == ENGINE_GEMINI:
        return analyze_with_gemini(resume_text, job_description)
    return analyze_with_ollama(resume_text, job_description)


load_dotenv()
init_db()

st.set_page_config(page_title="Job-Fit Simulator", page_icon="", layout="centered")
st.title("Job-Fit Simulator")
st.caption("Upload a resume and paste a job description to get an instant AI-powered suitability analysis.")

engine_choice = st.sidebar.radio(
    "Select AI Engine",
    [ENGINE_GEMINI, ENGINE_OLLAMA],
    index=0,
)

resume_file = st.file_uploader("Upload your resume", type=["pdf", "docx"])
job_description = st.text_area(
    "Paste the job description",
    height=250,
    placeholder="Paste the full job description here...",
)
job_url = st.text_input("Job Application Link (Optional)", placeholder="https://...")

analyze_clicked = st.button("Analyze My Resume", type="primary", use_container_width=True)

if analyze_clicked:
    if not resume_file:
        st.warning("Please upload a resume (PDF or DOCX) first.")
    elif not job_description.strip():
        st.warning("Please paste a job description first.")
    else:
        engine_label = "Gemini" if engine_choice == ENGINE_GEMINI else "Ollama (Qwen 2.5)"
        with st.spinner(f"Analyzing resume with {engine_label}..."):
            if resume_file.name.lower().endswith(".pdf"):
                resume_text = extract_pdf_text(resume_file.getvalue())
            elif resume_file.name.lower().endswith(".docx"):
                resume_text = extract_text_from_docx(resume_file.getvalue())
            result = analyze(resume_text, job_description, engine_choice)
            st.session_state["result"] = result
            st.session_state["job_url"] = job_url
            log_match(
                derive_job_title(job_description),
                result.suitability,
                result.matching_skills,
                result.missing_skills,
                result.experience_alignment,
                result.experience_gap_mitigation,
                result.analysis_summary,
                job_url,
            )

result: Optional[JobMatchResult] = st.session_state.get("result")
displayed_job_url: str = st.session_state.get("job_url", "")

if result:
    st.divider()

    emoji, style = SUITABILITY_STYLE[result.suitability]
    getattr(st, style)(f"{emoji} **Suitability: {result.suitability}**")

    if displayed_job_url:
        st.link_button("Open Job Application Page", displayed_job_url)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Matching Skills")
        if result.matching_skills:
            for skill in result.matching_skills:
                st.markdown(f"- {skill}")
        else:
            st.markdown("_None found_")

    with col2:
        st.subheader("Missing Skills")
        if result.missing_skills:
            for skill in result.missing_skills:
                st.markdown(f"- {skill}")
        else:
            st.markdown("_None found_")

    st.subheader("Work Experience Evaluation")
    if result.experience_alignment:
        for point in result.experience_alignment:
            st.markdown(f"- {point}")
    else:
        st.markdown("_None found_")

    st.markdown("**Strategic Portfolio Advice:** " + result.experience_gap_mitigation)

    st.subheader("Analysis Summary")
    st.info(result.analysis_summary)

with st.expander("Past Matches History"):
    history_df = fetch_history()
    if history_df.empty:
        st.markdown("_No past matches yet._")
    else:
        display_df = history_df.drop(
            columns=["matching_skills", "missing_skills", "experience_alignment", "experience_gap_mitigation"]
        )
        # Convert to clean markdown table without triggering pyarrow
        table_rows = ["| Date | Job Title | Suitability | Link |", "| :--- | :--- | :--- | :--- |"]
        for row in display_df.itertuples():
            link_md = f"[🔗 Open]({row.job_url})" if getattr(row, "job_url", None) else "-"
            table_rows.append(f"| {row.timestamp} | {row.job_title} | {row.suitability} | {link_md} |")
        st.markdown("\n".join(table_rows))

        options = {
            f"{row.timestamp} — {row.job_title}": row.id for row in history_df.itertuples()
        }
        selected_label = st.selectbox("Select a past evaluation to reload", options.keys())

        if st.button("Load Evaluation"):
            selected_row = history_df.loc[history_df["id"] == options[selected_label]].iloc[0]
            st.session_state["result"] = JobMatchResult(
                suitability=selected_row["suitability"],
                matching_skills=_safe_json_loads(selected_row["matching_skills"]),
                missing_skills=_safe_json_loads(selected_row["missing_skills"]),
                experience_alignment=_safe_json_loads(selected_row["experience_alignment"]),
                experience_gap_mitigation=selected_row["experience_gap_mitigation"] or "",
                analysis_summary=selected_row["analysis_summary"] or "",
            )
            st.session_state["job_url"] = selected_row["job_url"] or ""
            st.rerun()