from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
        scores["casual"] += 3
        scores["sporty"] += 1
        scores["netjes"] -= 1
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
    shoes_color = (data.get("shoes_color") or "").strip().lower()
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
    

    if style == "netjes" and garment_type == "hoodie":
       score -= 3
       reasons.append("Een hoodie maakt een outfit meestal minder netjes.")
       tips.append("Kies voor netjes liever een blouse, overhemd of een fijner bovenstuk.")


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

    if actual_vibe == "mixed":
        reasons.append("De outfit heeft een gemixte vibe in plaats van één duidelijke richting.")
        if style in {"casual", "netjes", "sporty"}:
            score -= 1
            tips.append("Maak de outfit iets duidelijker in één stijlrichting.")

    if shoe_type == "sneakers":
        if style in {"casual", "sporty", "netjes"}:
            score += 1
            reasons.append("Sneakers kunnen goed werken bij deze stijl als de rest van de outfit klopt.")

        if style in {"business", "chique"}:
            score -= 1
            reasons.append("Sneakers kunnen bij deze stijl, maar alleen als ze rustig en verzorgd zijn.")
            tips.append("Kies bij business of chique liever rustige sneakers, zoals wit of zwart.")

        if shoes_color in {"rood", "lichtrood", "donkerrood", "multicolor"} and style in {"netjes", "business", "chique"}:
            score -= 2
            reasons.append("De sneakers vallen sterk op voor deze nette stijl.")
            tips.append("Kies rustigere sneakers, zoals wit, zwart of grijs.")

        if style == "netjes" and garment_type == "hoodie":
            score -= 2
            reasons.append("Sneakers met een hoodie maken de outfit extra casual.")
    
    if outer_layer == "colbert" and shoe_type == "sportschoenen":
        score -= 3
        reasons.append("Sportschoenen botsen meestal met de nette uitstraling van een colbert.")
        tips.append("Kies bij een colbert liever rustige sneakers, hakken of veterschoenen.")

    if outer_layer == "colbert" and bottom_subtype == "korte_broek":
        score -= 3
        reasons.append("Een colbert met een korte broek voelt vaak minder in balans.")
        tips.append("Combineer een colbert liever met een pantalon, jeans of stofbroek.")
    
    if bottom_subtype == "jeans" and style in {"business", "chique"}:
        score -= 1
        reasons.append("Jeans maken de outfit iets minder formeel.")

    if bottom_subtype == "jeans" and outer_layer == "colbert":
        score += 1
        reasons.append("Jeans kunnen goed werken met een colbert als de outfit rustig blijft.")

    if garment_type == "hoodie" and outer_layer in {"colbert", "opengewerkt vest"}:
        score -= 4
        reasons.append("Een hoodie botst met de nette uitstraling van deze buitenlaag.")

    if garment_type == "overhemd" and style in {"netjes", "business"}:
        score += 2
        reasons.append("Een overhemd ondersteunt een nette en verzorgde uitstraling.")

    if garment_type == "overhemd" and style == "sporty":
        score -= 2
        reasons.append("Een overhemd voelt meestal minder sporty aan.")

    if garment_type == "overhemd" and shoe_type == "sportschoenen":
        score -= 2
        reasons.append("Sportschoenen botsen vaak met de nette uitstraling van een overhemd.")

    if garment_type == "overhemd" and bottom_subtype == "jeans":
        score += 1
        reasons.append("Een overhemd kan goed werken met jeans in een smart casual outfit.")

    if outer_layer == "bomberjack" and style in {"business", "chique"}:
        score -= 3
        reasons.append("Een bomberjack voelt meestal te casual of sporty voor deze stijl.")
        tips.append("Kies voor business of chique liever een colbert of rustigere buitenlaag.")

    if outer_layer == "bomberjack" and shoe_type in {"sneakers", "sportschoenen"}:
        score += 1
        reasons.append("Een bomberjack werkt goed met sneakers of sportschoenen in een casual of sporty outfit.")

    if outer_layer == "bomberjack" and garment_type in {"blouse", "overhemd"}:
        score -= 1
        reasons.append("Een bomberjack maakt een blouse of overhemd minder netjes.")

    if garment_type == "jurk" and style in {"netjes", "chique"}:
        score += 2
        reasons.append("Een jurk ondersteunt goed een nette of elegante uitstraling.")

    if garment_type == "jurk" and shoe_type == "sportschoenen":
        score -= 3
        reasons.append("Sportschoenen botsen vaak met de uitstraling van een jurk.")

    if garment_type == "jurk" and shoe_type == "sneakers":
        score += 1
        reasons.append("Sneakers kunnen een jurk een moderne en casual uitstraling geven.")

    if garment_type == "jurk" and outer_layer == "bomberjack":
        score -= 1
        reasons.append("Een bomberjack maakt een jurk sportiever en minder elegant.")

    if garment_type == "blouse" and style in {"netjes", "business", "chique"}:
        score += 2
        reasons.append("Een blouse ondersteunt een nette, verzorgde uitstraling.")

    if garment_type == "blouse" and bottom_subtype in {"jeans", "pantalon", "stofbroek", "plisse_rok", "maxi_rok"}:
        score += 1
        reasons.append("Een blouse werkt goed met dit onderstuk en houdt de outfit verzorgd.")

    if garment_type == "blouse" and shoe_type in {"sneakers", "hakken", "laarzen", "veterschoenen"}:
        score += 1
        reasons.append("Deze schoenen passen goed bij een blouse.")

    if garment_type == "blouse" and outer_layer == "bomberjack" and shoe_type == "sportschoenen":
       score -= 3
       reasons.append("Een blouse met bomberjack én sportschoenen voelt te veel gemixt.")
       tips.append("Kies rustigere schoenen of een nettere buitenlaag.")

    if bottom_subtype == "pantalon" and style in {"netjes", "business", "chique"}:
        score += 2
        reasons.append("Een pantalon ondersteunt een nette en verzorgde uitstraling.")

    if bottom_subtype == "pantalon" and garment_type in {"blouse", "overhemd"}:
        score += 2
        reasons.append("Deze combinatie vormt een sterke nette basis.")

    if bottom_subtype == "pantalon" and shoe_type == "sportschoenen":
        score -= 3
        reasons.append("Sportschoenen botsen vaak met de nette uitstraling van een pantalon.")
        tips.append("Kies rustigere schoenen voor meer balans.")

    if bottom_subtype == "pantalon" and garment_type == "hoodie":
        score -= 2
        reasons.append("Een hoodie maakt de uitstraling van een pantalon veel casualer.")

    if shoe_type == "laarzen" and style in {"casual", "netjes"}:
        score += 1
        reasons.append("Laarzen kunnen goed werken binnen deze stijl.")

    if shoe_type == "laarzen" and bottom_subtype in {"jeans", "pantalon", "plisse_rok"}:
        score += 1
        reasons.append("De laarzen passen goed bij het onderstuk.")

    if shoe_type == "laarzen" and style == "sporty":
        score -= 2
        reasons.append("Laarzen voelen meestal minder sporty aan.")

    if shoe_type == "laarzen" and garment_type == "hoodie" and outer_layer == "bomberjack":
        score -= 2
        reasons.append("Deze combinatie voelt te zwaar casual en gemixt.")

    if garment_type == "trui" and style in {"casual", "sporty"}:
        score += 2
        reasons.append("Een trui ondersteunt een comfortabele casual uitstraling.")

    if garment_type == "trui" and bottom_subtype in {"jeans", "korte_broek"}:
        score += 1
        reasons.append("Deze combinatie voelt ontspannen en goed in balans.")

    if garment_type == "trui" and style in {"business", "chique"}:
        score -= 2
        reasons.append("Een trui voelt meestal minder strak en formeel voor deze stijl.")

    if garment_type == "trui" and outer_layer == "colbert" and bottom_subtype == "pantalon":
        score -= 2
        reasons.append("De combinatie voelt te gemixt tussen cozy en formeel.")

    if garment_type == "tshirt" and style in {"casual", "sporty"}:
        score += 2
        reasons.append("Een T-shirt ondersteunt goed een casual of ontspannen uitstraling.")

    if garment_type == "tshirt" and bottom_subtype in {"jeans", "stofbroek"}:
        score += 1
        reasons.append("Deze combinatie voelt modern en goed in balans.")

    if garment_type == "tshirt" and outer_layer in {"bomberjack", "leren_jasje"}:
        score += 1
        reasons.append("Het T-shirt werkt goed met deze casual buitenlaag.")

    if garment_type == "tshirt" and style == "chique":
        score -= 2
        reasons.append("Een T-shirt voelt meestal te simpel voor een echt chique uitstraling.")

    if shoe_type == "sportschoenen" and style in {"sporty", "casual"}:
        score += 2
        reasons.append("Sportschoenen ondersteunen een sporty en ontspannen uitstraling.")

    if shoe_type == "sportschoenen" and garment_type in {"hoodie", "tshirt"}:
        score += 1
        reasons.append("Deze combinatie voelt logisch en sporty aan.")

    if shoe_type == "sportschoenen" and style in {"netjes", "chique"}:
        score -= 3
        reasons.append("Sportschoenen botsen meestal met een nette of elegante uitstraling.")

    if shoe_type == "sportschoenen" and outer_layer == "colbert":
        score -= 3
        reasons.append("Sportschoenen passen meestal minder goed bij een colbert.")

    if shoe_type == "hakken" and style in {"netjes", "business", "chique"}:
        score += 2
        reasons.append("Hakken ondersteunen een verzorgde en elegante uitstraling.")

    if shoe_type == "hakken" and bottom_subtype in {"jeans", "pantalon"}:
        score += 1
        reasons.append("Hakken geven deze combinatie een stijlvolle uitstraling.")

    if shoe_type == "hakken" and style == "sporty":
        score -= 3
        reasons.append("Hakken passen meestal niet goed bij een sporty uitstraling.")

    if shoe_type == "hakken" and garment_type == "hoodie" and style == "sporty":
        score -= 3
        reasons.append("Deze combinatie voelt te tegenstrijdig tussen sporty en elegant.")

    if garment_type == "jurk" and outer_layer == "colbert" and shoe_type == "hakken":
        score -= 1
        reasons.append("De combinatie voelt erg formeel en strak aan.")

    if style == "preppy" and garment_type in {"blouse", "overhemd", "trui"}:
        score += 2
        reasons.append("Dit bovenstuk ondersteunt goed een preppy uitstraling.")

    if style == "preppy" and bottom_subtype in {"pantalon", "stofbroek"}:
        score += 2
        reasons.append("Dit onderstuk past goed bij een verzorgde preppy stijl.")

    if style == "preppy" and outer_layer in {"colbert", "opengewerkt vest"}:
        score += 2
        reasons.append("Deze buitenlaag ondersteunt een klassieke preppy uitstraling.")

    if style == "preppy" and garment_type == "hoodie":
        score -= 2
        reasons.append("Een hoodie voelt meestal te sporty voor preppy.")

    if style == "preppy" and shoe_type == "sportschoenen":
        score -= 3
        reasons.append("Sportschoenen passen meestal minder goed bij preppy.")

    if style == "preppy" and shoe_type == "sneakers":
        score += 1
        reasons.append("Rustige sneakers kunnen goed werken binnen een moderne preppy outfit.")

    if garment_type == "longsleeve":
        score += 1
        reasons.append("Een longsleeve is een flexibel kledingstuk dat goed combineert.")

    if garment_type == "longsleeve" and style in {"casual", "preppy", "sporty"}:
        score += 1
        reasons.append("De longsleeve ondersteunt deze stijl goed.")

    if garment_type == "longsleeve" and outer_layer in {"colbert", "bomberjack", "opengewerkt vest"}:
        score += 1
        reasons.append("De longsleeve werkt goed als basislaag in deze combinatie.")

    if garment_type == "longsleeve" and shoe_type in {"sneakers", "laarzen", "veterschoenen"}:
        score += 1
        reasons.append("Deze schoenen passen goed bij een longsleeve outfit.")

    if bottom_subtype == "stofbroek" and style in {"casual", "netjes", "sporty", "chique", "preppy"}:
        score += 1
        reasons.append("Een stofbroek geeft de outfit een verzorgde maar flexibele uitstraling.")

    if bottom_subtype == "stofbroek" and style in {"casual", "netjes", "sporty", "chique", "preppy"}:
        score += 1
        reasons.append("Een stofbroek geeft de outfit een verzorgde maar flexibele uitstraling.")

    if bottom_subtype == "stofbroek" and style in {"casual", "netjes", "sporty", "chique", "preppy"}:
       score += 1
       reasons.append("Een stofbroek geeft de outfit een verzorgde maar flexibele uitstraling.")

    if bottom_subtype == "stofbroek" and outer_layer == "colbert":
        score += 1
        reasons.append("Een stofbroek en colbert kunnen goed werken in een moderne outfit.")

    if bottom_subtype == "stofbroek" and outer_layer == "bomberjack":
        score -= 2
        reasons.append("Een bomberjack botst wat meer met de rustige uitstraling van een stofbroek.")

    if bottom_subtype == "stofbroek" and garment_type == "trui" and shoe_type == "laarzen":
        score -= 2
        reasons.append("Deze combinatie voelt wat zwaar en minder in balans.")

    if style == actual_vibe:
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

    vibe_reason = next((r for r in reasons if "vibe" in r.lower()), None)

    if vibe_reason:
        final_reason = vibe_reason
    else:
        final_reason = " ".join(reasons[:2]) if reasons else "De outfit is beoordeeld op kleur, stijl en balans."

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

@app.get("/")
def home():
    return {"status": "ok", "mode": "chatgpt"}


@app.post("/predict")
def predict(outfit: Outfit):
    data = outfit.model_dump()
    return rule_based_outfit_check(data)

FEEDBACK_PATH = Path(__file__).parent / "feedback.csv"

class Feedback(BaseModel):
    agree: bool
    predicted_label: int
    confidence: Optional[float] = None
    note: str = ""
    payload: dict[str, Any]

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