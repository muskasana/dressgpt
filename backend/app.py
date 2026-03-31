from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from pathlib import Path
import csv
import json
from datetime import datetime
from typing import Any, Optional

client = OpenAI(api_key="sk-JOUW_KEY_HIER")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FEEDBACK_PATH = Path(__file__).parent / "feedback.csv"


class Outfit(BaseModel):
    garment_type: str = "tshirt"
    outer_layer: str = "none"
    outer_layer_color: str = "none"
    bottom_subtype: str = "none"
    shoe_type: str = "sneakers"
    bag_type: str = "none"

    top_color: str
    bottom_type: str
    bottom_color: str
    shoes_color: str
    style: str

    top_type: str = "shirt"
    is_dress: str = "no"
    dress_color: str = "none"
    bag_present: str = "no"
    bag_color: str = "none"


class Feedback(BaseModel):
    agree: bool
    predicted_label: int
    confidence: Optional[float] = None
    note: str = ""
    payload: dict[str, Any]


@app.get("/")
def home():
    return {"status": "ok", "mode": "chatgpt"}


@app.post("/predict")
def predict(outfit: Outfit):
    data = outfit.model_dump()

    prompt = f"""
Je bent DressGPT, een mode-AI.

Beoordeel deze outfit op stijl en combinatie.
Geef antwoord als JSON met exact deze velden:
- label (1 = goed, 0 = niet goed)
- confidence (getal tussen 0 en 1)
- reason (korte uitleg in het Nederlands)
- tips (lijst van 1 tot 3 korte tips in het Nederlands)

Outfit:
- stijl: {data.get("style")}
- bovenstuk type: {data.get("top_type")}
- bovenstuk kleur: {data.get("top_color")}
- jurk: {data.get("is_dress")}
- jurk kleur: {data.get("dress_color")}
- onderstuk type: {data.get("bottom_type")}
- onderstuk kleur: {data.get("bottom_color")}
- schoenen kleur: {data.get("shoes_color")}
- schoen type: {data.get("shoe_type")}
- vest/jasje: {data.get("outer_layer")}
- vest kleur: {data.get("outer_layer_color")}
- tas aanwezig: {data.get("bag_present")}
- tas type: {data.get("bag_type")}
- tas kleur: {data.get("bag_color")}

Regels:
- let goed op of de outfit past bij de gekozen stijl
- geef alleen JSON terug
- geen extra tekst buiten de JSON
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    text = response.output_text

    try:
        result = json.loads(text)
    except Exception:
        return {
            "label": 0,
            "confidence": 0.0,
            "reason": "De AI gaf geen geldig antwoord terug.",
            "tips": ["Probeer opnieuw."]
        }

    return result


@app.post("/feedback")
def feedback(item: Feedback):
    row = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "agree": int(item.agree),
        "predicted_label": int(item.predicted_label),
        "confidence": "" if item.confidence is None else float(item.confidence),
        "note": item.note.strip(),
        "payload_json": json.dumps(item.payload, ensure_ascii=False),
    }

    write_header = not FEEDBACK_PATH.exists()

    with open(FEEDBACK_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    return {"status": "saved"}