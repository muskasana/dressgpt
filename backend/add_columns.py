import pandas as pd

df = pd.read_csv("train.csv")

# voeg kolommen toe als ze nog niet bestaan
if "outer_layer" not in df.columns:
    df["outer_layer"] = "none"

if "bottom_subtype" not in df.columns:
    # default: als broek -> jeans, als rok -> maxi_rok, als none -> none
    def guess_subtype(row):
        bt = str(row.get("bottom_type", "none")).strip().lower()
        if bt == "broek":
            return "jeans"
        if bt == "rok":
            return "maxi_rok"
        return "none"
    df["bottom_subtype"] = df.apply(guess_subtype, axis=1)

# strip spaties in tekst
for col in df.columns:
    if df[col].dtype == object:
        df[col] = df[col].astype(str).str.strip()

# mooie vaste kolomvolgorde
desired = [
    "top_color","top_type","outer_layer","is_dress","dress_color",
    "bottom_type","bottom_subtype","bottom_color",
    "shoes_color","style",
    "bag_present","bag_color",
    "match_top_shoes","color_family_top","color_family_bottom","contrast_level","match_top_bottom",
    "label"
]
# alleen de kolommen die bestaan (veilig)
desired = [c for c in desired if c in df.columns]
df = df[desired]

df.to_csv("train.csv", index=False)
print("✅ train.csv bijgewerkt: outer_layer + bottom_subtype toegevoegd")