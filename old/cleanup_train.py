import pandas as pd

df = pd.read_csv("train.csv")
before = len(df)

# Spaties opruimen in alle tekstkolommen
for col in df.columns:
    if df[col].dtype == object:
        df[col] = df[col].astype(str).str.strip()

# TESTTEST rij(en) weg
mask = df.apply(lambda row: row.astype(str).str.contains("TESTTEST").any(), axis=1)
df = df[~mask]

# Duplicaten weg (exact gelijke rijen)
df = df.drop_duplicates()

after = len(df)

df.to_csv("train.csv", index=False)

print(f"✅ Opschonen klaar. Rijen: {before} -> {after}")
print(f"✅ Verwijderd: {before - after} rijen (TESTTEST/spaties/duplicaten)")