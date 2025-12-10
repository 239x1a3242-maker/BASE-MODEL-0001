# load_model.py
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

_model = None
_tokenizer = None

def init_model(model_dir: str = "."):
    """Call this ONCE at startup to load model into memory"""
    global _model, _tokenizer
    
    if _model is not None:
        print("✅ Model already loaded!")
        return _model, _tokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    print("\n" + "=" * 70)
    print(f"Loading model from local files on {device.upper()}...")
    print("=" * 70)

    _model = AutoModelForCausalLM.from_pretrained(
        model_dir,
        device_map=device,
        torch_dtype="auto",
        trust_remote_code=True,
        local_files_only=True,
    )

    _tokenizer = AutoTokenizer.from_pretrained(
        model_dir,
        local_files_only=True,
    )

    print(f"✅ Model loaded! ({sum(p.numel() for p in _model.parameters()) / 1e9:.1f}B params)")
    print("=" * 70 + "\n")
    
    return _model, _tokenizer

def get_model():
    """Get the already-loaded model (fast)"""
    global _model, _tokenizer
    if _model is None:
        raise RuntimeError("Model not initialized! Call init_model() first.")
    return _model, _tokenizer
