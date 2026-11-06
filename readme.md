# Job Match Analyzer 🎯

An enterprise-grade, privacy-first software utility that leverages semantic natural language processing (NLP) to map unstructured resume documents against corporate job listings, outputting deterministic, type-safe career alignment metrics.

This project was engineered to solve the legacy limitations of rigid keyword-counting applicant tracking systems by implementing full semantic comprehension of technical skills and transferable experience.

## 🛠️ Tech Stack & Architecture

- **User Interface:** Streamlit (Reactive Python web dashboard utilizing in-memory binary stream state management to process file buffers natively in RAM without disk footprint).
- **AI Orchestration Framework:** Built with an abstract client boundary allowing seamless hot-swapping between cloud platforms (**Google Gen AI SDK / Gemini 3.8 Flash**) and fully air-gapped, on-premise local edge computing (**OpenAI SDK / Ollama / Llama 3.1 8B**).
- **Deterministic Inference:** Locked down with zero-temperature sampling (`temperature=0.0`) to enforce strict classification consistency and prevent evaluation variance across runs.
- **Data Ingestion:** `pypdf` and `python-docx` for low-overhead, in-memory extraction of unstructured text streams from binary PDF and Word (`.docx`) documents.
- **Relational Persistence:** Built-in `sqlite3` storage engine (`jobs_history.db`) for tracking historical match logs, preserving full structured evaluation payloads, timestamps, and application metadata.
- **Type Safety & Data Integrity:** `Pydantic` schema enforcement (`BaseModel`) to force probabilistic language models to return strictly validated, deterministic JSON structures.

## 💼 Core Features

- **Multi-Format Resume Ingestion:** Supports both `.pdf` and `.docx` files, parsing document streams directly in memory via `io.BytesIO`.
- **Semantic Talent Matching:** Evaluates transferable capabilities rather than strict keyword strings (e.g., mapping asynchronous backend structures like C#/.NET to Python workflows based on conceptual engineering foundations).
- **Chronological Experience Evaluation:** Maps candidate career timelines directly against requested seniority levels to gauge architectural maturity.
- **Experience Gap Mitigation:** A custom portfolio-advice layer designed to calculate how academic project depth and adjacent stack familiarity can strategically bypass the junior "2–3 years of experience" corporate paradox.
- **Application URL Tracking:** Captures original job posting URLs alongside evaluations, providing one-click access (`st.link_button`) directly to live job applications.
- **Audit Trail & State Hydration:** An interactive historical match inspector that queries SQLite and rehydrates previous evaluations directly back into the reactive UI state without re-running LLM inference.
- **Air-Gapped Privacy Implementation:** Can be executed 100% locally on user hardware to fully secure candidate Personally Identifiable Information (PII), aligning with enterprise data protection standards (GDPR).

## 🚀 Getting Started (Local Edge-Inference Mode)

### 1. Clone & Install Dependencies
Ensure you have Python installed, then set up the local project environment:
```bash
git clone https://github.com
cd job-match-analyzer
pip install -r requirements.txt
```

### 2. Configure Environment Isolation
Create a local `.env` file in the root directory to store your configurations securely:
```env
# Optional if running fully local via Ollama, required if running cloud-fallback mode
GEMINI_API_KEY=your_google_ai_studio_key_here
```

### 3. Launch the Local Core Model
This application leverages your local hardware to run inference. Start your local background engine (e.g., using an Intel Core Ultra 9 / Arc GPU architecture via Ollama):
```bash
ollama run llama3.1
```

### 4. Run the Dashboard
Boot up the Streamlit frontend web server locally:
```bash
python -m streamlit run app.py
```
Open your browser and navigate to `http://localhost:8501` to test job listings against your CV in real-time.
