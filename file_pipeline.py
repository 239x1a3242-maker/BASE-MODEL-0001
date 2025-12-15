#!/usr/bin/env python3
"""
file_pipeline.py

Universal file pipeline for GAKR AI.

Responsibilities:
- Create dataupload/ folder structure (if not present)
- Save uploaded files to disk
- Detect file type
- Run type-specific extractors
- Return structured, text-friendly context for Phi-3
"""

from __future__ import annotations

import os
import mimetypes
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd
import pdfplumber
import docx
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import whisper
import ffmpeg
from fastapi import UploadFile

# ============================================================
# PATHS & FOLDERS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, "dataupload")

FOLDERS = {
    "image": "images",
    "video": "videos",
    "audio": "audio",
    "document": "documents",
    "tabular": "tabular",
    "other": "other",
}


def ensure_folders() -> None:
    """
    Ensure base upload folder and all subfolders exist.
    """
    os.makedirs(UPLOAD_ROOT, exist_ok=True)
    for sub in FOLDERS.values():
        os.makedirs(os.path.join(UPLOAD_ROOT, sub), exist_ok=True)


ensure_folders()

# ============================================================
# TYPE DETECTION & PATHS
# ============================================================


def detect_kind(filename: str, content_type: str | None) -> str:
    """
    Decide logical kind: tabular, document, image, audio, video, other.
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext in [".csv", ".xlsx", ".xls", ".json"]:
        return "tabular"
    if ext in [".pdf", ".txt"]:
        return "document"
    if ext in [".docx"]:
        return "document"
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
        return "image"
    if ext in [".mp3", ".wav", ".m4a"]:
        return "audio"
    if ext in [".mp4", ".mkv", ".mov", ".avi"]:
        return "video"

    if content_type:
        if content_type.startswith("image/"):
            return "image"
        if content_type.startswith("audio/"):
            return "audio"
        if content_type.startswith("video/"):
            return "video"

    return "other"


def make_target_path(kind: str, filename: str) -> str:
    """
    Build a safe, timestamped filepath under dataupload/{sub}/.
    """
    sub = FOLDERS.get(kind, "other")
    safe_name = os.path.basename(filename)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    final_name = f"{timestamp}_{safe_name}"
    return os.path.join(UPLOAD_ROOT, sub, final_name)


# ============================================================
# MAIN MULTI-FILE ENTRY POINT
# ============================================================


async def process_files(files: List[UploadFile]) -> Dict[str, Any]:
    """
    Save all files, run analyses, and return structured context.

    Output example:
    {
      "files": [
        {
          "original_name": "...",
          "stored_path": "dataupload/documents/...",
          "kind": "document",
          "summary": { ... }
        },
        ...
      ]
    }
    """
    ensure_folders()
    results: List[Dict[str, Any]] = []

    for uf in files:
        try:
            kind = detect_kind(uf.filename, uf.content_type)
            target_path = make_target_path(kind, uf.filename)

            # Save file to disk
            try:
                with open(target_path, "wb") as out:
                    data = await uf.read()
                    out.write(data)
            except Exception as save_err:
                results.append(
                    {
                        "original_name": uf.filename,
                        "stored_path": None,
                        "kind": kind,
                        "summary": {
                            "error": f"Failed to save file: {save_err}"
                        },
                    }
                )
                continue

            # Analyze by type
            try:
                summary = analyze_file(target_path, kind)
            except Exception as analyze_err:
                summary = {
                    "error": f"Unexpected error in analysis: {analyze_err}"
                }

            results.append(
                {
                    "original_name": uf.filename,
                    "stored_path": os.path.relpath(target_path, BASE_DIR),
                    "kind": kind,
                    "summary": summary,
                }
            )

        except Exception as outer_err:
            results.append(
                {
                    "original_name": getattr(uf, "filename", "unknown"),
                    "stored_path": None,
                    "kind": "unknown",
                    "summary": {
                        "error": f"Fatal error while handling file: {outer_err}"
                    },
                }
            )

    return {"files": results}


# ============================================================
# TYPE-SPECIFIC ANALYSIS
# ============================================================


def analyze_file(path: str, kind: str) -> Dict[str, Any]:
    if kind == "tabular":
        return analyze_tabular(path)
    if kind == "document":
        return analyze_document(path)
    if kind == "image":
        return analyze_image(path)
    if kind == "audio":
        return analyze_audio(path)
    if kind == "video":
        return analyze_video(path)
    return {"type": "other", "note": "Unsupported or unknown file type"}


# ---------- TABULAR: CSV / Excel / JSON ----------


def analyze_tabular(path: str) -> Dict[str, Any]:
    ext = os.path.splitext(path)[1].lower()
    df = None

    try:
        if ext == ".csv":
            df = pd.read_csv(path)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(path)
        elif ext == ".json":
            df = pd.read_json(path)
        else:
            return {
                "type": "tabular",
                "error": f"Unsupported tabular format: {ext}",
            }
    except Exception as e:
        return {"type": "tabular", "error": f"Failed to load table: {e}"}

    summary: Dict[str, Any] = {
        "type": "tabular",
        "rows": int(df.shape[0]),
        "columns": [str(c) for c in df.columns],
    }

    try:
        summary["missing_values"] = df.isna().sum().to_dict()
    except Exception as e:
        summary["missing_values_error"] = str(e)

    try:
        summary["numeric_stats"] = df.describe(include="number").to_dict()
    except Exception:
        summary["numeric_stats"] = {}

    return summary


# ---------- DOCUMENTS: PDF / DOCX / TXT ----------


def analyze_document(path: str) -> Dict[str, Any]:
    ext = os.path.splitext(path)[1].lower()
    text = ""

    try:
        if ext == ".pdf":
            # First try pdfplumber
            try:
                with pdfplumber.open(path) as pdf:
                    pages = []
                    for page in pdf.pages[:10]:
                        t = page.extract_text()
                        if t:
                            pages.append(t)
                text = "\n".join(pages)
            except Exception:
                # Fallback to PyMuPDF
                doc = fitz.open(path)
                chunks = []
                for page in doc[:10]:
                    chunks.append(page.get_text())
                text = "\n".join(chunks)
        elif ext == ".docx":
            d = docx.Document(path)
            paras = [p.text for p in d.paragraphs if p.text.strip()]
            text = "\n".join(paras)
        else:  # .txt or unknown plain-text
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
    except Exception as e:
        return {
            "type": "document",
            "error": f"Failed to extract document text: {e}",
        }

    short = text[:4000]
    return {
        "type": "document",
        "char_count": len(text),
        "preview": short,
    }


# ---------- IMAGES ----------


def analyze_image(path: str) -> Dict[str, Any]:
    try:
        img = Image.open(path)
    except Exception as e:
        return {"type": "image", "error": f"Failed to open image: {e}"}

    try:
        text = pytesseract.image_to_string(img)
    except Exception as e:
        text = ""
        ocr_error = str(e)
    else:
        ocr_error = None

    short = text[:2000]

    result: Dict[str, Any] = {
        "type": "image",
        "size": {"width": img.width, "height": img.height},
        "ocr_preview": short,
    }
    if ocr_error:
        result["ocr_error"] = ocr_error

    return result


# ---------- AUDIO (Whisper) ----------

_whisper_model = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            _whisper_model = whisper.load_model("small")
        except Exception as e:
            raise RuntimeError(f"Failed to load Whisper model: {e}")
    return _whisper_model


def analyze_audio(path: str) -> Dict[str, Any]:
    try:
        model = get_whisper_model()
    except Exception as e:
        return {"type": "audio", "error": str(e)}

    try:
        result = model.transcribe(path)
    except Exception as e:
        return {"type": "audio", "error": f"Whisper transcription failed: {e}"}

    text = result.get("text", "") or ""
    short = text[:4000]
    duration = None
    try:
        if result.get("segments"):
            duration = result["segments"][-1].get("end", None)
    except Exception:
        duration = None

    return {
        "type": "audio",
        "duration_sec": duration,
        "transcript_preview": short,
    }


# ---------- VIDEO (audio extraction + Whisper) ----------


def analyze_video(path: str) -> Dict[str, Any]:
    audio_path = path + ".tmp_audio.wav"
    audio_summary: Dict[str, Any]

    try:
        (
            ffmpeg
            .input(path)
            .output(audio_path, ac=1, ar=16000)
            .overwrite_output()
            .run(quiet=True)
        )
    except Exception as e:
        return {
            "type": "video",
            "error": f"Failed to extract audio from video: {e}",
        }

    try:
        audio_summary = analyze_audio(audio_path)
    finally:
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

    return {
        "type": "video",
        "audio_analysis": audio_summary,
    }
