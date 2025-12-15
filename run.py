#!/usr/bin/env python3
"""
run.py - FastAPI backend + frontend server for GAKR AI

Features:
- Serves templates/chat.html at "/"
- /api/analyze:
    - prompt: required (must not be empty)
    - files: optional list[UploadFile] (0, 1, many; any type)
    - api_key: required
- If files are present → file-analysis mode (different system prompt)
- If no files → general assistant mode
- Detailed exceptions and logs for easier debugging
"""

from typing import List, Optional

import json
import traceback

from fastapi import (
    FastAPI,
    HTTPException,
    Form,
    UploadFile,
    File,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import uvicorn

from load_model import init_model
from generate import generate_response
from file_pipeline import process_files


# ============================================================
# APP SETUP
# ============================================================

app = FastAPI(title="GAKR AI")

# Templates (chat.html lives in ./templates)
templates = Jinja2Templates(directory="templates")

# CORS (open for dev; restrict origins in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # change to specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key
API_KEY = "gakr-ai-2025-secret"

# Load model ONCE at startup
print("🚀 Starting GAKR AI Backend...")
try:
    model, tokenizer = init_model(".")
    print("✅ Model initialized successfully")
except Exception as e:
    print("❌ Failed to load model at startup:")
    traceback.print_exc()
    raise e


# ============================================================
# ROUTES
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Serve chat.html as homepage.
    """
    try:
        return templates.TemplateResponse("chat.html", {"request": request})
    except Exception as e:
        # If template not found or other template error
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to render chat.html: {str(e)}",
        )


@app.post("/api/analyze")
async def analyze_endpoint(
    prompt: str = Form(...),                             # required
    api_key: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),      # optional
):
    """
    Main analysis endpoint.

    Cases:
    - prompt only (no files)      → general assistant mode
    - prompt + one/many files     → file-analysis mode (uses file context)
    """
    try:
        # ---------- Basic validation ----------
        if api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")

        if prompt is None:
            raise HTTPException(status_code=400, detail="Prompt is missing")
        if not prompt.strip():
            raise HTTPException(status_code=400, detail="Prompt cannot be empty")

        files = files or []

        # ---------- Branch by presence of files ----------
        if files:
            # ----- CASE 1: prompt + files -----
            try:
                context = await process_files(files)
            except Exception as extract_err:
                traceback.print_exc()
                raise HTTPException(
                    status_code=500,
                    detail=f"Error while processing uploaded files: {str(extract_err)}",
                )

            context_text = json.dumps(context, indent=2, ensure_ascii=False)
            combined_user_prompt = f"""
User question:
{prompt}

Below is structured information extracted from the user's uploaded files.
The extraction was done by automated tools.

Your task:
1. Answer the user's question as accurately as possible.
2. Use the context when it is relevant.
3. Highlight important patterns, risks, or opportunities.
4. If some information is missing or uncertain, say so honestly.

Context:
{context_text}
"""

            system_prompt = (
                "You are GAKR AI, a careful and honest analysis assistant that works with "
                "structured summaries of files (tables, PDFs, documents, images, audio, video, etc.). "
                "You never assume file contents beyond what the provided context states."
            )

        else:
            # ----- CASE 2: prompt only -----
            context = {"files": []}  # keep structure consistent
            combined_user_prompt = prompt

            system_prompt = (
                "You are GAKR AI, a helpful and honest general-purpose assistant. "
                "You answer questions, explain concepts, help with reasoning and coding, "
                "using your knowledge up to 2024. Be clear, concise, and direct."
            )

        # ---------- Generate with Phi‑3 ----------
        try:
            response_text = generate_response(
                user_prompt=combined_user_prompt,
                system_prompt=system_prompt,
                max_tokens=512,
                temperature=0.2,
            )
        except Exception as gen_err:
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Error during model generation: {str(gen_err)}",
            )

        return JSONResponse(
            {
                "response": response_text,
                "context": context,
                "status": "success",
            }
        )

    except HTTPException:
        # Let FastAPI handle HTTPException as-is
        raise
    except Exception as e:
        # Unexpected error: log full traceback and return 500
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected backend error: {str(e)}",
        )


@app.get("/health")
async def health_check():
    """
    Simple health check.
    """
    return {"status": "healthy", "model_loaded": True}


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🌐 SERVER & CHAT LOCATION")
    print("=" * 60)
    print("🚀 CHAT INTERFACE:     http://localhost:8080")
    print("📱 ALTERNATIVE URL:    http://127.0.0.1:8080")
    print("🔧 API DOCUMENTATION:  http://localhost:8080/docs")
    print("✅ CHAT.HTML SERVED:   templates/chat.html")
    print("📁 TEMPLATES FOLDER:   ./templates/")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8080)
