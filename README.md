# GAKR AI – Local File‑Aware Chat Assistant

GAKR AI is a **local, privacy‑friendly chat assistant** that runs entirely on your machine.  
It combines a **FastAPI backend**, a modern **web chat UI**, and a **file‑intelligence pipeline** that can read and summarize many file types before generating natural‑language responses.

The assistant itself is **text‑only**. It never directly sees raw PDFs, images, audio, or videos.  
Instead, specialized tools convert files into **structured text summaries**, and the language model reasons over that text.

---

## ✨ Features

### 🌐 Web Chat Interface
- Clean dark UI with message bubbles and typing indicator  
- Auto‑growing input box  
- Attach files from camera, gallery, or filesystem  
- Works in any modern browser at **http://localhost:8080**

### 🧠 Text + File Understanding
- **Prompt only** → general assistant (explanations, coding help, reasoning)  
- **Prompt + files** → full analysis pipeline:
  - Detects file type
  - Stores uploads in `dataupload/`
  - Extracts structured facts
  - Feeds extracted context + question to the model

### 📂 Multi‑File, Multi‑Type Uploads
Upload multiple files at once:
- Documents: PDF, DOCX, TXT  
- Tabular data: CSV, Excel, JSON  
- Images: OCR via Tesseract  
- Audio: Speech‑to‑text via Whisper  
- Video: Audio extraction via ffmpeg → Whisper

### 💾 Persistent Uploads
- Files saved under `dataupload/` by type  
- Timestamped, safe filenames  
- Automatic directory creation

### 🔐 Simple Login Reminder UX
- After **5 guest messages**, a popup encourages login  
- Logged‑in users are not interrupted  
- Login state stored in `localStorage`

---

## 🗂 Project Structure

```
project_root/
├── run.py                # FastAPI backend + template serving
├── load_model.py         # Loads the language model once
├── generate.py           # generate_response() wrapper
├── file_pipeline.py      # File detection, storage, and summarization
├── templates/
│   ├── chat.html         # Main chat interface
│   └── auth.html         # Login / signup UI
├── dataupload/           # Created at runtime for uploads
│   ├── images/
│   ├── videos/
│   ├── audio/
│   ├── documents/
│   ├── tabular/
│   └── other/
└── requirements.txt
```

---

## ⚙️ Installation

### 1️⃣ Create & Activate Virtual Environment (Recommended)

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# or
.\.venv\Scripts\activate      # Windows
```

### 2️⃣ Install Python Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt**
```
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
```

### 3️⃣ Install System Tools

- **Tesseract OCR** (for image text extraction)
- **ffmpeg** (for audio extraction and Whisper)

Install via OS package manager (`apt`, `brew`, `choco`) or official installers.

---

## ▶️ Running GAKR AI

### Start the Backend

```bash
python run.py
```

Expected output:
```
🚀 Starting GAKR AI Backend...
✅ Model initialized successfully

🌐 SERVER & CHAT LOCATION
🚀 CHAT INTERFACE:     http://localhost:8080
🔧 API DOCUMENTATION:  http://localhost:8080/docs
✅ CHAT.HTML SERVED:   templates/chat.html
```

### Open the Chat UI
Navigate to:
```
http://localhost:8080
```

---

## 🔌 API Overview

### POST `/api/analyze`

**Request** (`multipart/form-data`)
- `api_key` (string, required)  
- `prompt` (string, required)  
- `files` (optional, multiple)

**Behavior**
- No files → General assistant mode  
- With files → File‑analysis mode using structured summaries

**Response**
```json
{
  "response": "natural-language answer here",
  "context": {
    "files": [
      {
        "original_name": "report.pdf",
        "stored_path": "dataupload/documents/20241214_report.pdf",
        "kind": "document",
        "summary": {
          "type": "document",
          "char_count": 12345,
          "preview": "First 4000 characters..."
        }
      }
    ]
  },
  "status": "success"
}
```

---

## 🧪 File Intelligence Pipeline

Handled by `file_pipeline.py`

### Type Detection
- Tabular → CSV, XLSX, JSON  
- Documents → PDF, DOCX, TXT  
- Images → PNG, JPG  
- Audio → MP3, WAV  
- Video → MP4, MKV  

### Summaries
- **Tabular**: rows, columns, missing values, stats  
- **Documents**: character count + preview  
- **Images**: dimensions + OCR text  
- **Audio**: duration + transcript preview  
- **Video**: extracted audio analysis  

Errors are stored per‑file and never crash the whole request.

---

## 🎨 Frontend UX Highlights

- Auto‑growing textarea  
- Attachment chips with remove buttons  
- Typing indicator  
- URL prefill: `?q=your+question`  
- Generic error message for all backend failures  

---

## 🔐 Security Notes

- API key is currently a fixed string (for local use)  
- For production:
  - Use environment variables
  - Add real authentication (JWT / sessions)
  - Restrict CORS
  - Apply upload size limits and cleanup policies

---

## 🚀 Extending GAKR AI

Ideas:
- Per‑user chat & file history (database)
- Search across uploaded documents
- External API integrations
- HTTPS + reverse proxy deployment

---

## 🧠 Philosophy

**GAKR AI is an intelligence layer.**  
Tools translate reality (files, media, data) into structured language.  
The language model turns that language into insight, reasoning, and action.
