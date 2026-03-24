from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import pandas as pd
from pathlib import Path
import csv
import json
from datetime import datetime
from typing import Any, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = Path(__file__).parent / "model.joblib"
FEEDBACK_PATH = Path(__file__).parent / "feedback.csv"

model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None

FEATURES = [
    "top_color", "top_type", "is_dress", "dress_color",
    "bottom_type", "bottom_color", "shoes_color", "style",
    "bag_present", "bag_color"
]


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


def build_reason_and_tips(data: dict, pred: int):
    tips = []

    if pred == 1:
        reason = "Deze outfit lijkt goed bij elkaar te passen."
    else:
        reason = "Deze outfit oogt minder in balans."

    if data.get("style") == "business":
        tips.append("Bij business werken rustige kleuren en nette combinaties vaak beter.")

    if data.get("bag_present") == "yes" and data.get("bag_color") == data.get("shoes_color"):
        tips.append("Tas en schoenen in dezelfde kleur geven vaak extra rust.")

    if data.get("is_dress") == "yes":
        tips.append("Bij een jurk werken rustige accessoires vaak mooi.")

    if not tips:
        if pred == 1:
            tips.append("De kleuren voelen vrij samenhangend.")
        else:
            tips.append("Probeer minder opvallende kleuren tegelijk te combineren.")

    return reason, tips


@app.get("/")
def home():
    return {"status": "ok", "model_loaded": model is not None}


@app.post("/predict")
def predict(outfit: Outfit):
    if model is None:
        return {"error": "Model not found. Run train_model.py first."}

    data = outfit.model_dump()
    df = pd.DataFrame([data])[FEATURES]
    pred = int(model.predict(df)[0])

    conf = None
    if hasattr(model, "predict_proba"):
        conf = float(model.predict_proba(df).max())

    reason, tips = build_reason_and_tips(data, pred)

    return {
        "label": pred,
        "confidence": conf,
        "reason": reason,
        "tips": tips
    }


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