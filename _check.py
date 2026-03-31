import pandas as pd
df = pd.read_csv("sp500_fundamental_dataset.csv")

print("TRAIN/VAL/TEST SPLIT:")
for name, mask in [("Train (<=2019)", df["year"] <= 2019),
                   ("Val (2020-2021)", df["year"].between(2020, 2021)),
                   ("Test (2022+)", df["year"] >= 2022)]:
    sub = df[mask]
    n1 = sub["excess_return_1y"].notna().sum()
    n3 = sub["excess_return_3y"].notna().sum()
    print(f"  {name:25s}: {len(sub):6d} rows, {sub['ticker'].nunique():3d} co, target_1y={n1:5d}, target_3y={n3:5d}")

print("\nSECTOR COUNTS:")
print(df["sector"].value_counts().to_string())
