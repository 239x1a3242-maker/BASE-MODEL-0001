# run.py - FastAPI Backend + Frontend Server (PORT 8080)
from fastapi import FastAPI, HTTPException, Form, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import uvicorn
from load_model import init_model
from generate import generate_response

# Initialize FastAPI app
app = FastAPI(title="GAKR AI")

# Templates (chat.html lives here)
templates = Jinja2Templates(directory="templates")

# CORS (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key
API_KEY = "gakr-ai-2025-secret"

# Load model ONCE at startup
print("🚀 Starting GAKR AI Backend...")
model, tokenizer = init_model(".")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve chat.html as homepage"""
    return templates.TemplateResponse("chat.html", {"request": request})

@app.post("/api/chat")
async def chat_endpoint(
    message: str = Form(...),
    api_key: str = Form(...),
    files: list[UploadFile] = File(None)
):
    """Main chat API endpoint"""
    
    # Validate API key
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        system_prompt = (
            "You are GAKR AI (not Phi), a helpful and honest AI assistant. "
            "You know general information up to 2024. "
            "Never mention Phi, Microsoft, or your training origin."
        )
        
        response = generate_response(
            user_prompt=message,
            system_prompt=system_prompt,
            max_tokens=512,
            temperature=0.2,
        )
        
        return JSONResponse({
            "response": response,
            "status": "success"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": True}

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🌐 SERVER & CHAT LOCATION")
    print("="*60)
    print("🚀 CHAT INTERFACE:     http://localhost:8000")
    print("📱 ALTERNATIVE URL:    http://127.0.0.1:8000") 
    print("🔧 API DOCUMENTATION:  http://localhost:8000/docs")
    print("✅ CHAT.HTML SERVED:   templates/chat.html")
    print("📁 TEMPLATES FOLDER:   ./templates/")
    print("="*60)
    
    # 🚀 RUN ON PORT 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
