from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ai_predict(data: dict) -> dict:
    prompt = f"""
Je bent DressGPT, een mode-AI.

Beoordeel deze outfit.

Geef ALLEEN JSON:
{{
  "label": 1 of 0,
  "confidence": getal tussen 0 en 1,
  "reason": "Er ging iets mis",
  "tips": ["tip1", "tip2"]
}}

BELANGRIJK:
- wees NIET te streng
- simpele outfits zijn vaak goed
- donkerblauw + wit + zwart = vaak goed
- sneakers mogen bij netjes als rustig

Outfit:
stijl: {data.get("style")}
top: {data.get("top_type")} {data.get("top_color")}
onder: {data.get("bottom_type")} {data.get("bottom_color")}
schoenen: {data.get("shoes_color")}
vest: {data.get("outer_layer")} {data.get("outer_layer_color")}
tas: {data.get("bag_type")} {data.get("bag_color")}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    text = response.output_text.strip()
    return json.loads(text)