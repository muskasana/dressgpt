from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from pathlib import Path
import csv
import json
from datetime import datetime
from typing import Any, Optional
import os

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_color_type(color: str) -> str:
    color = (color or "none").strip().lower()

    neutral = {
        "zwart", "wit", "grijs", "bruin", "zwart-wit"
    }

    subtle = {
        "blauw", "lichtblauw", "donkerblauw",
        "groen", "lichtgroen", "donkergroen",
        "rood", "lichtrood", "donkerrood",
        "oranje", "lichtoranje", "donkeroranje",
        "geel", "lichtgeel", "donkergeel",
        "paars", "lichtpaars", "donkerpaars",
        "roze", "lichtroze", "donkerroze"
    }

    colorful = {
        "rood-wit", "blauw-wit", "roze-wit", "groen-wit", "multicolor"
    }

    if color in neutral:
        return "neutraal"
    if color in colorful:
        return "kleurrijk"
    if color in subtle:
        return "subtiel"
    return "subtiel"


def rule_based_outfit_check(data: dict) -> dict:
    style = (data.get("style") or "").strip().lower()
    garment_type = (data.get("garment_type") or "").strip().lower()
    outer_layer = (data.get("outer_layer") or "").strip().lower()
    bottom_type = (data.get("bottom_type") or "").strip().lower()
    bottom_subtype = (data.get("bottom_subtype") or "").strip().lower()
    shoe_type = (data.get("shoe_type") or "").strip().lower()

    color_info = {
        "top": {
            "color": (data.get("top_color") or "none").strip().lower(),
            "type": get_color_type(data.get("top_color"))
        },
        "bottom": {
            "color": (data.get("bottom_color") or "none").strip().lower(),
            "type": get_color_type(data.get("bottom_color"))
        },
        "shoes": {
            "color": (data.get("shoes_color") or "none").strip().lower(),
            "type": get_color_type(data.get("shoes_color"))
        },
        "outer": {
            "color": (data.get("outer_layer_color") or "none").strip().lower(),
            "type": get_color_type(data.get("outer_layer_color"))
            if (data.get("outer_layer") or "none").strip().lower() != "none"
            else "none"
        },
    }

    used_colors = []
    used_types = []

    for part, info in color_info.items():
        if info["color"] != "none":
            used_colors.append(info["color"])
        if info["type"] != "none":
            used_types.append(info["type"])

    unique_colors = set(used_colors)
    non_neutral_types = {t for t in used_types if t != "neutraal"}

    score = 0
    reasons = []
    tips = []

    # -------- KLEURREGELS --------

    if len(unique_colors) <= 3:
        score += 2
        reasons.append("De outfit gebruikt niet te veel kleuren en oogt daardoor meer in balans.")
    else:
        score -= 2
        reasons.append("Er zitten veel verschillende kleuren in de outfit.")
        tips.append("Kies wat minder verschillende kleuren voor meer rust.")

    if len(non_neutral_types) <= 2:
        score += 1
        reasons.append("De kleurtypes blijven redelijk consistent.")
    else:
        score -= 2
        reasons.append("De outfit mixt te veel verschillende kleurtypes.")
        tips.append("Probeer het bij maximaal twee kleurtypes te houden.")

    colorful_count = used_types.count("kleurrijk")
    if colorful_count == 1:
        score += 1
        reasons.append("Er is één kleurrijk accent, wat de outfit levendig kan maken.")
    elif colorful_count >= 2:
        score -= 2
        reasons.append("Er zijn meerdere kleurrijke onderdelen, waardoor de outfit sneller druk oogt.")
        tips.append("Gebruik liever één kleurrijk accent.")

    if (
        color_info["top"]["type"] == "neutraal"
        and color_info["bottom"]["type"] == "neutraal"
    ):
        score += 1
        reasons.append("Het bovenstuk en onderstuk vormen een rustige neutrale basis.")

    if all(t in {"neutraal", "subtiel"} for t in used_types):
        score += 1
        reasons.append("De kleuren zijn rustig en subtiel gecombineerd.")

    if (
        color_info["outer"]["type"] == "kleurrijk"
        and color_info["shoes"]["type"] == "kleurrijk"
    ):
        score -= 1
        reasons.append("De buitenlaag en schoenen trekken allebei veel aandacht.")
        tips.append("Maak de jas of schoenen rustiger voor meer balans.")

    # -------- STIJLREGELS --------

    if style == "netjes" and outer_layer == "bomberjack":
        score -= 3
        reasons.append("Een bomberjack past meestal beter bij casual of sporty dan bij netjes.")
        tips.append("Kies bij netjes liever geen bomberjack.")

    if style == "netjes" and outer_layer == "spijkerjasje":
        score -= 2
        reasons.append("Een spijkerjasje maakt de outfit sneller casual dan netjes.")
        tips.append("Kies een rustigere buitenlaag als je voor netjes gaat.")

    if style == "netjes" and outer_layer == "leren jasje":
        score -= 2
        reasons.append("Een leren jasje geeft eerder een stoerdere dan nette uitstraling.")

    if style == "netjes" and outer_layer == "opengewerkt vest":
        score += 1
        reasons.append("Een opengewerkt vest kan goed werken bij netjes als de rest rustig blijft.")

    if style == "netjes" and shoe_type == "sneakers":
        score += 1
        reasons.append("Sneakers kunnen bij netjes als de rest van de outfit rustig en verzorgd is.")

    if style == "casual" and outer_layer == "colbert":
        score -= 2
        reasons.append("Een colbert maakt de outfit netter dan casual.")
        tips.append("Laat het colbert weg of kies een casualere buitenlaag.")

    if style == "business" and shoe_type == "sneakers":
        score -= 2
        reasons.append("Sneakers passen meestal minder goed bij business.")
        tips.append("Kies bij business liever een nettere schoen.")

    if style == "business" and outer_layer in {"bomberjack", "spijkerjasje", "leren jasje"}:
        score -= 3
        reasons.append("Deze buitenlaag past minder goed bij een zakelijke stijl.")

    if style == "sporty" and shoe_type not in {"sneakers", "sportschoenen"}:
        score -= 2
        reasons.append("De schoenkeuze voelt minder sporty aan dan de gekozen stijl.")

    if style == "chique" and garment_type == "hoodie":
        score -= 3
        reasons.append("Een hoodie past meestal niet bij een chique stijl.")

    if style == "preppy" and garment_type == "hoodie":
        score -= 1
        reasons.append("Een hoodie voelt vaak sportiever dan preppy.")

    # -------- MIX / LOGICA --------

    vibe_markers = []

    if garment_type == "hoodie":
        vibe_markers.append("casual")
    if outer_layer == "bomberjack":
        vibe_markers.append("sporty")
    if outer_layer == "spijkerjasje":
        vibe_markers.append("casual")
    if outer_layer == "leren jasje":
        vibe_markers.append("stoer")
    if outer_layer == "colbert":
        vibe_markers.append("netjes")
    if outer_layer == "opengewerkt vest":
        vibe_markers.append("zacht")
    if garment_type in {"blouse", "overhemd"}:
        vibe_markers.append("netjes")
    if shoe_type in {"sportschoenen"}:
        vibe_markers.append("sporty")
    if shoe_type in {"hakken", "veterschoenen"}:
        vibe_markers.append("netjes")

    if len(set(vibe_markers)) >= 3:
        score -= 2
        reasons.append("De outfit mixt veel verschillende vibes door elkaar.")
        tips.append("Kies iets meer één richting: casual, netjes of sporty.")

    if garment_type == "hoodie" and outer_layer != "none":
        score -= 1
        reasons.append("Een hoodie met nog een extra laag erover kan snel zwaar of onpraktisch voelen.")

    if bottom_type == "broek" and bottom_subtype == "jeans" and style == "business":
        score -= 2
        reasons.append("Jeans passen meestal minder goed bij business.")

    # -------- EINDOORDEEL --------

    label = 1 if score >= 1 else 0

    confidence = 0.75
    if score >= 4:
        confidence = 0.9
    elif score >= 1:
        confidence = 0.8
    elif score == 0:
        confidence = 0.65
    else:
        confidence = 0.85

    # Houd reasons/tips netjes kort
    final_reason = " ".join(reasons[:3]) if reasons else "De outfit is beoordeeld op kleur, stijl en balans."
    final_tips = tips[:2]

    if not final_tips and label == 0:
        final_tips = ["Probeer minder stijlen of kleuren tegelijk te combineren."]
    elif not final_tips and label == 1:
        final_tips = ["De outfit is mooi in balans."]

    return {
        "label": label,
        "confidence": confidence,
        "reason": final_reason,
        "tips": final_tips
    }




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
    return rule_based_outfit_check(data)

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