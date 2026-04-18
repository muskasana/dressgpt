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

def detect_outfit_vibe(data: dict) -> str:
    garment_type = (data.get("garment_type") or "").strip().lower()
    outer_layer = (data.get("outer_layer") or "").strip().lower()
    bottom_type = (data.get("bottom_type") or "").strip().lower()
    bottom_subtype = (data.get("bottom_subtype") or "").strip().lower()
    shoe_type = (data.get("shoe_type") or "").strip().lower()

    scores = {
        "casual": 0,
        "netjes": 0,
        "sporty": 0,
    }

    # TOP
    if garment_type == "hoodie":
        scores["casual"] += 2
        scores["sporty"] += 1
    elif garment_type == "tshirt":
        scores["casual"] += 2
    elif garment_type == "longsleeve":
        scores["casual"] += 1
    elif garment_type == "trui":
        scores["casual"] += 1
    elif garment_type in {"blouse", "overhemd"}:
        scores["netjes"] += 2
    elif garment_type == "jurk":
        scores["netjes"] += 1

    # OUTER LAYER
    if outer_layer == "bomberjack":
        scores["sporty"] += 2
        scores["casual"] += 1
    elif outer_layer == "spijkerjasje":
        scores["casual"] += 2
    elif outer_layer == "leren_jasje":
        scores["casual"] += 1
    elif outer_layer == "colbert":
        scores["netjes"] += 3
    elif outer_layer == "opengewerkt vest":
        scores["netjes"] += 1
        scores["casual"] += 1

    # BOTTOM
    if bottom_type == "broek":
        if bottom_subtype == "jeans":
            scores["casual"] += 2
        elif bottom_subtype == "stofbroek":
            scores["casual"] += 1
            scores["netjes"] += 1
        elif bottom_subtype == "pantalon":
            scores["netjes"] += 2
        elif bottom_subtype == "korte_broek":
            scores["casual"] += 2
            scores["sporty"] += 1
    elif bottom_type == "rok":
        if bottom_subtype == "plisse_rok":
            scores["netjes"] += 2
        elif bottom_subtype == "maxi_rok":
            scores["netjes"] += 1
            scores["casual"] += 1
        elif bottom_subtype == "laagjesrok":
            scores["casual"] += 1

    # SHOES
    if shoe_type == "sneakers":
        scores["casual"] += 1
    elif shoe_type == "sportschoenen":
        scores["sporty"] += 2
    elif shoe_type in {"hakken", "veterschoenen"}:
        scores["netjes"] += 2
    elif shoe_type == "laarzen":
        scores["casual"] += 1
        scores["netjes"] += 1
    elif shoe_type in {"sandalen", "slippers"}:
        scores["casual"] += 1

    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_vibe, top_score = ordered[0]
    second_score = ordered[1][1]

    if top_score == 0:
        return "mixed"

    if top_score - second_score <= 1:
        return "mixed"

    return top_vibe


def rule_based_outfit_check(data: dict) -> dict:
    style = (data.get("style") or "").strip().lower()
    garment_type = (data.get("garment_type") or "").strip().lower()
    outer_layer = (data.get("outer_layer") or "").strip().lower()
    bottom_type = (data.get("bottom_type") or "").strip().lower()
    bottom_subtype = (data.get("bottom_subtype") or "").strip().lower()
    shoe_type = (data.get("shoe_type") or "").strip().lower()
    actual_vibe = detect_outfit_vibe(data)

    color_info = {
        "top": {
            "color": (data.get("top_color") or "none").strip().lower(),
            "type": get_color_type(data.get("top_color")),
        },
        "bottom": {
            "color": (data.get("bottom_color") or "none").strip().lower(),
            "type": get_color_type(data.get("bottom_color")),
        },
        "shoes": {
            "color": (data.get("shoes_color") or "none").strip().lower(),
            "type": get_color_type(data.get("shoes_color")),
        },
        "outer": {
            "color": (data.get("outer_layer_color") or "none").strip().lower(),
            "type": get_color_type(data.get("outer_layer_color"))
            if (data.get("outer_layer") or "none").strip().lower() != "none"
            else "none",
        },
    }

    used_colors = []
    used_types = []

    for _, info in color_info.items():
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

    if style == "netjes" and outer_layer == "leren_jasje":
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

    if style == "business" and outer_layer in {"bomberjack", "spijkerjasje", "leren_jasje"}:
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

    # -------- VIBE MATCH --------

    if actual_vibe == "mixed":
        reasons.append("De outfit heeft een gemixte vibe in plaats van één duidelijke richting.")
        if style in {"casual", "netjes", "sporty"}:
            score -= 1
            tips.append("Maak de outfit iets duidelijker in één stijlrichting.")

    elif style == actual_vibe:
        score += 2
        reasons.append(f"De gekozen stijl past goed bij de echte vibe van de outfit: {actual_vibe}.")

    elif style == "netjes" and actual_vibe == "casual" and shoe_type == "sneakers":
        score -= 1
        reasons.append("De outfit oogt iets meer casual dan netjes, vooral door de combinatie als geheel.")

    elif style == "casual" and actual_vibe == "sporty":
        reasons.append("De outfit zit tussen casual en sporty in.")

    else:
        score -= 2
        reasons.append(f"De gekozen stijl ({style}) past niet goed bij de echte vibe van de outfit ({actual_vibe}).")
        tips.append(f"Maak de outfit meer {style} of kies een stijl die beter past bij de combinatie.")

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
        "tips": final_tips,
        "vibe": actual_vibe,
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

    if style == "netjes" and outer_layer == "leren_jasje":
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

    if style == "business" and outer_layer in {"bomberjack", "spijkerjasje", "leren_jasje"}:
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

    # -------- VIBE MATCH --------

    if actual_vibe == "mixed":
        reasons.append("De outfit heeft een gemixte vibe in plaats van één duidelijke richting.")
        if style in {"casual", "netjes", "sporty"}:
            score -= 1
            tips.append("Maak de outfit iets duidelijker in één stijlrichting.")

    elif style == actual_vibe:
        score += 2
        reasons.append(f"De gekozen stijl past goed bij de echte vibe van de outfit: {actual_vibe}.")

    elif style == "netjes" and actual_vibe == "casual" and shoe_type == "sneakers":
        score -= 1
        reasons.append("De outfit oogt iets meer casual dan netjes, vooral door de combinatie als geheel.")

    elif style == "casual" and actual_vibe == "sporty":
        reasons.append("De outfit zit tussen casual en sporty in.")

    else:
        score -= 2
        reasons.append(f"De gekozen stijl ({style}) past niet goed bij de echte vibe van de outfit ({actual_vibe}).")
        tips.append(f"Maak de outfit meer {style} of kies een stijl die beter past bij de combinatie.")

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
        "tips": final_tips,
        "vibe": actual_vibe,
    }