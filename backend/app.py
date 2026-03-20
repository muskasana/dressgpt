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
model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None

FEATURES = [
    "top_color", "top_type", "is_dress", "dress_color",
    "bottom_type", "bottom_color", "shoes_color", "style",
    "bag_present", "bag_color"
]

class Outfit(BaseModel):
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

    return {"label": pred, "confidence": conf}
from pydantic import BaseModel

FEEDBACK_PATH = Path(__file__).parent / "feedback.csv"

class Feedback(BaseModel):
    agree: bool                 # True = eens, False = niet eens
    predicted_label: int        # wat de AI zei (0/1)
    confidence: Optional[float] = None
    note: str = ""              # optioneel: waarom niet eens / extra uitleg
    payload: dict[str, Any]     # de outfit die gestuurd werd

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