GAKR AI – File‑Aware Chat Assistant
1. Overview
GAKR AI is a local, privacy‑friendly chat assistant that can answer questions from:

Direct text prompts

Uploaded files (PDF, DOCX, TXT, CSV, Excel, JSON)

Images (with OCR)

Audio recordings (speech‑to‑text)

Video files (audio extracted and transcribed)

The assistant never reads raw binary files directly. Instead, a file‑pipeline converts uploads into structured summaries that the model can reason over.

Backend is built with FastAPI; frontend is a single‑page chat.html served as a template.

2. System Architecture
2.1 Components
Frontend (templates/chat.html)

Modern chat UI with:

Auto‑growing textarea input

File attachment chips (camera, gallery, generic files)

Typing indicator

Guest‑mode login reminder after N messages

Sends prompt and optional files to backend using FormData.

Backend API (run.py)

FastAPI app exposing:

GET / – serves chat.html

POST /api/analyze – main chat + file analysis endpoint

GET /health – health check

Handles:

API key validation

Prompt validation

Routing requests to file pipeline and text generator

File Pipeline (file_pipeline.py)

Detects file type (tabular, document, image, audio, video, other).

Saves files into dataupload/ subfolders (images/, documents/, etc.).

Extracts structured summaries:

Tabular: shape, columns, missing values, basic stats

Documents: text preview and length

Images: OCR text and dimensions

Audio: transcript preview and duration

Video: audio transcript summary

Model Loader (load_model.py)

Loads the language model and tokenizer once at startup.

Provides init_model() used by run.py.

Text Generation (generate.py)

Exposes generate_response(user_prompt, system_prompt, ...).

Uses the loaded model to generate answers from combined prompt + context.

3. Directory Structure
text
project_root/
├── run.py                 # FastAPI app (serves UI and /api/analyze)
├── load_model.py          # Loads model & tokenizer
├── generate.py            # generate_response() helper
├── file_pipeline.py       # File detection, storage, and summarization
├── requirements.txt       # Python dependencies
├── templates/
│   ├── chat.html          # Main chat interface
│   └── auth.html          # Login / signup page
├── dataupload/            # Auto-created storage for user uploads
│   ├── images/
│   ├── videos/
│   ├── audio/
│   ├── documents/
│   ├── tabular/
│   └── other/
└── model/                 # (optional) local model weights/config
dataupload/ and subfolders are created automatically when files are processed.

4. Installation & Setup
4.1 Prerequisites
Python 3.9+

Sufficient RAM/VRAM for the chosen model

FFmpeg installed and available on PATH (required for audio/video processing)​

Example FFmpeg installation on Ubuntu:

bash
sudo apt update && sudo apt install ffmpeg
4.2 Install Python dependencies
Create and activate a virtual environment (recommended), then:

bash
pip install -r requirements.txt
requirements.txt should contain:

text
fastapi
uvicorn[standard]
python-multipart

torch
transformers
accelerate
safetensors

pandas
numpy

pdfplumber
pymupdf
python-docx

Pillow
pytesseract

openai-whisper
ffmpeg-python
5. Running the System
5.1 Start the backend server
From project_root:

bash
python run.py
Expected console output (simplified):

Model loading logs

“GAKR AI Backend…”

Uvicorn running on http://0.0.0.0:8080

5.2 Access the web UI
Open your browser and navigate to:

Chat UI: http://localhost:8080

API docs (Swagger): http://localhost:8080/docs

6. Core API – /api/analyze
6.1 Request format
Method: POST

URL: http://localhost:8080/api/analyze

Content type: multipart/form-data

Fields:

api_key – must match the key configured in run.py.

prompt – required user message (non‑empty).

files – optional, one or many UploadFile entries.

Example JavaScript (any frontend):

javascript
const formData = new FormData();
formData.append("api_key", "gakr-ai-2025-secret");
formData.append("prompt", "Summarize these documents.");

files.forEach(file => formData.append("files", file));

const res = await fetch("http://localhost:8080/api/analyze", {
  method: "POST",
  body: formData,
});

const data = await res.json();
console.log(data.response);
6.2 Backend logic
Case A – Prompt only

files empty.

Backend:

Skips file processing.

Passes prompt directly to generate_response with a general assistant system prompt.

Use case: normal chat, Q&A, explanations, coding help.

Case B – Prompt + files

files contains one or more uploads of any supported type.

Backend:

Calls process_files(files) to:

Save each file under dataupload/<type>/....

Build per‑file summaries.

Constructs a combined prompt containing:

User question.

Structured JSON “Context” describing each file.

Calls generate_response with a file‑analysis system prompt that:

Explains that the model should rely only on the provided context.

This design ensures the model never sees binaries directly, only human‑readable summaries.

6.3 Response format
On success:

json
{
  "response": "Natural language answer from the assistant.",
  "context": {
    "files": [
      {
        "original_name": "report.pdf",
        "stored_path": "dataupload/documents/20241214_..._report.pdf",
        "kind": "document",
        "summary": {
          "type": "document",
          "char_count": 5421,
          "preview": "First few thousand characters..."
        }
      }
    ]
  },
  "status": "success"
}
On error, an HTTP 4xx/5xx is returned with a detail message; the default chat UI shows a generic “server issue” message to the user.

7. File Pipeline Specification
7.1 Type detection
By extension and MIME type:

Tabular: .csv, .xlsx, .xls, .json → tabular

Documents: .pdf, .docx, .txt → document

Images: .png, .jpg, .jpeg, .webp, .bmp → image

Audio: .mp3, .wav, .m4a → audio

Video: .mp4, .mkv, .mov, .avi → video

Else → other

7.2 Storage
Each upload is saved as:

text
dataupload/<kind_folder>/<UTC_TIMESTAMP>_<original_filename>
Example:

text
dataupload/documents/20241214_120001_123456_quarterly_report.pdf
7.3 Summaries
Tabular (pandas)

Rows, columns, missing value counts, numeric statistics.

Document (pdfplumber / PyMuPDF / python-docx)

Character count, text preview (first ~4000 characters).

Image (Pillow + Tesseract)

Dimensions, OCR text preview.

Audio (Whisper + ffmpeg)

Approximate duration, transcript preview.

Video (ffmpeg + Whisper)

Audio transcript summary embedded under audio_analysis.

Any error (e.g., unreadable file) is recorded in that file’s summary.error instead of crashing.

8. Frontend Behaviour (chat.html)
8.1 Chat interactions
Sends prompt and files to /api/analyze via FormData.

Shows user bubble immediately; shows AI bubble when response arrives.

If the backend is unreachable or returns an error, shows a generic error message.

8.2 Attachments
Camera, gallery, and generic file picker.

Multiple files of mixed types can be attached to a single prompt.

Chips show file names; users can remove individual files before sending.

8.3 Login reminder (guest mode)
Uses localStorage.getItem("gakr_is_logged_in"):

"true" → treated as logged in.

Anything else → guest.

After every 5 user messages from a guest:

Shows a centered modal:

Message: encourage login to save chat history.

Buttons:

“Continue without login” → dismisses modal.

“Log in to save chats” → navigates to auth.html.

9. Auth Integration (auth.html)
When login/signup succeeds, auth.html should run:

javascript
localStorage.setItem('gakr_is_logged_in', 'true');
window.location.href = 'chat.html';
Optional logout can clear the flag:

javascript
localStorage.removeItem('gakr_is_logged_in');
The FastAPI backend itself is secured with an API key; browser login state is primarily for UX (saving conversations, reminders), not backend authentication.

10. Extensibility
Additional file types

Extend detect_kind and add new analyze_* functions in file_pipeline.py.

Richer analysis

For tabular data, plug in profiling or ML models (e.g., anomaly detection).

For documents, add chunk‑wise summarization and topic extraction.

Multiple frontends

Any site can call /api/analyze if it:

Can reach the backend URL.

Sends api_key, prompt, and optional files in FormData.

CORS is currently configured to allow all origins.

This design keeps a clear separation of concerns:

Files → Structured context → Language model reasoning → Human‑readable insight.
