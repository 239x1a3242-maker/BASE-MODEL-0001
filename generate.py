# generate.py
import torch
from load_model import get_model

def generate_response(
    user_prompt: str,
    system_prompt: str = "You are a helpful AI assistant.",
    max_tokens: int = 256,
    temperature: float = 0.2,
) -> str:
    """Generate response using ALREADY LOADED model"""
    model, tokenizer = get_model()  # Fast - no loading!

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    input_ids = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
    ).to(model.device)

    attention_mask = (input_ids != tokenizer.pad_token_id).long()

    do_sample = temperature > 0.0
    gen_kwargs = dict(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=max_tokens,
        pad_token_id=tokenizer.eos_token_id,
        use_cache=False,
        do_sample=do_sample,
    )
    if do_sample:
        gen_kwargs["temperature"] = float(temperature)
        gen_kwargs["top_p"] = 0.95

    with torch.no_grad():
        outputs = model.generate(**gen_kwargs)

    return tokenizer.decode(
        outputs[0][input_ids.shape[1]:],
        skip_special_tokens=True,
    ).strip()
