import pandas as pd

def clean_transactions(df):
    df = df.dropna(subset=["date", "amount"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["amount"])
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y", errors="coerce")
    df = df.dropna(subset=["date"])
    df["description"] = df["description"].str.strip().str.upper()
    return df.reset_index(drop=True)