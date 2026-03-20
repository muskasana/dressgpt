import pandas as pd
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier

df = pd.read_csv("train.csv")

# ✅ Alleen velden die je website echt invult (simpeler, minder "alles goed")
USE_COLS = [
    "top_color", "top_type", "is_dress", "dress_color",
    "bottom_type", "bottom_color", "shoes_color", "style",
    "bag_present", "bag_color",
    "label"
]

df = df[USE_COLS]

X = df.drop(columns=["label"])
y = df["label"]

preprocess = ColumnTransformer(
    [("cat", OneHotEncoder(handle_unknown="ignore"), X.columns.tolist())]
)

rf = RandomForestClassifier(n_estimators=300, random_state=42)

model = Pipeline(steps=[("prep", preprocess), ("rf", rf)])
model.fit(X, y)

joblib.dump(model, "model.joblib")
print("✅ Saved model.joblib")