# Job Match Analyzer 🎯

An enterprise-grade, privacy-first software utility that leverages semantic natural language processing (NLP) to map unstructured resume documents against corporate job listings, outputting type-safe career alignment metrics.

This project was engineered to solve the legacy limitations of rigid keyword-counting applicant tracking systems by implementing full semantic comprehension of technical skills and transferable experience.

## 🛠️ Tech Stack & Architecture

- **User Interface:** Streamlit (Reactive Python web dashboard utilizing in-memory binary stream state management to process file buffers natively in RAM without disk footprint).
- **Dual-Engine AI Selector:** A sidebar toggle switches each analysis between two engines:
  - **Gemini (Cloud / High Precision)** — default. Google Gen AI SDK calling `gemini-3.8-flash`, with automatic fallback to `gemini-3.5-flash-lite` if the primary request fails.
  - **Ollama Local (Qwen 2.5 / Offline)** — fully air-gapped, on-premise inference via the OpenAI SDK pointed at Ollama (`http://localhost:11434/v1`). Defaults to `qwen2.5:14b`, configurable with the `OLLAMA_MODEL` environment variable.
- **Calibrated Evaluation Prompt:** Both engines share one recruiter-style system prompt with explicit rules for matching skills, missing skills and the four suitability levels.
- **Deterministic Local Inference:** The Ollama engine runs with zero-temperature sampling (`temperature=0.0`) for consistent classification across runs.
- **Data Ingestion:** `pypdf` and `python-docx` for low-overhead, in-memory extraction of unstructured text streams from binary PDF and Word (`.docx`) documents.
- **Relational Persistence:** Built-in `sqlite3` storage engine (`jobs_history.db`, created automatically on first run) for tracking historical match logs, preserving full structured evaluation payloads, timestamps, and application metadata.
- **Type Safety & Data Integrity:** `Pydantic` schema enforcement (`BaseModel`) to force probabilistic language models to return strictly validated JSON structures.

## 💼 Core Features

- **Multi-Format Resume Ingestion:** Supports both `.pdf` and `.docx` files, parsing document streams directly in memory via `io.BytesIO`.
- **Semantic Talent Matching:** Evaluates transferable capabilities rather than strict keyword strings (e.g., mapping asynchronous backend structures like C#/.NET to Python workflows based on conceptual engineering foundations).
- **Seniority-Aware Suitability Scoring:** Classifies each role as *Perfect Match*, *Good Match*, *Stretch Role* or *Unsuitable*, weighing the technical stack against the requested seniority level. Non-technical leadership (e.g., retail or hospitality shift lead) is not treated as software engineering leadership.
- **Chronological Experience Evaluation:** Maps candidate career timelines directly against requested seniority levels to gauge architectural maturity.
- **Experience Gap Mitigation:** A portfolio-advice section suggesting how project depth and adjacent stack familiarity can offset the junior "2–3 years of experience" paradox.
- **Application URL Tracking:** Captures original job posting URLs alongside evaluations, providing one-click access (`st.link_button`) directly to live job applications.
- **Audit Trail & State Hydration:** A "📜 Past Matches History" panel lists every previous evaluation (newest first) and can reload any of them back into the UI without re-running LLM inference. The table is rendered as native Markdown, so it does not depend on PyArrow (useful on machines where Windows Application Control blocks `pyarrow.lib`).
- **Air-Gapped Privacy Implementation:** With the Ollama engine selected, everything runs 100% locally on user hardware to fully secure candidate Personally Identifiable Information (PII), aligning with enterprise data protection standards (GDPR).

## 🚀 Getting Started

### 1. Clone & Install Dependencies
Ensure you have Python installed, then set up the local project environment:
```bash
git clone https://github.com/mossstak/job-match-analyzer.git
cd job-match-analyzer
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a local `.env` file in the root directory (it is already listed in `.gitignore`):
```env
# Required for the Gemini engine; not needed if you only use Ollama
GEMINI_API_KEY=your_google_ai_studio_key_here

# Optional: which Ollama model to use (default: qwen2.5:14b)
OLLAMA_MODEL=qwen2.5:14b
```

### 3. (Optional) Set Up the Local Model
Only needed for the **Ollama Local** engine. Install [Ollama](https://ollama.com), then pull the model and make sure Ollama is running:
```bash
ollama pull qwen2.5:14b
```
On lower-memory hardware, use `qwen2.5:7b` instead and set `OLLAMA_MODEL=qwen2.5:7b` in your `.env`.

### 4. Run the Dashboard
Boot up the Streamlit frontend web server locally:
```bash
python -m streamlit run app.py
```
Open your browser and navigate to `http://localhost:8501`, pick an engine in the sidebar, upload your CV, paste a job description and click **Analyze My Resume**.

## 📁 Project Files

| File | Purpose |
| :--- | :--- |
| `app.py` | The Streamlit dashboard (both engines, history, UI). |
| `matcher.py` | A standalone command-line Gemini script that compares `resume.pdf` against a job description pasted into the file. |
| `requirements.txt` | Python dependencies. |
| `jobs_history.db` | Local SQLite match history, created automatically on first run. |
