import pandas as pd


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if df.empty:
        return df

    df["is_anomaly"] = 0
    df["anomaly_score"] = 0.0
    df["anomaly_reason"] = ""

    expenses = df[df["amount"] < 0].copy()
    if len(expenses) < 4:
        return df

    expenses["abs_amount"] = expenses["amount"].abs()
    mean = float(expenses["abs_amount"].mean())
    std = float(expenses["abs_amount"].std())
    p95 = float(expenses["abs_amount"].quantile(0.95)) if len(expenses) >= 5 else mean

    if std == 0:
        return df

    expenses["zscore"] = (expenses["abs_amount"] - mean) / std
    anomaly_rows = expenses[(expenses["zscore"] >= 1.8) | (expenses["abs_amount"] >= max(p95, mean * 2.2))]

    for idx, row in anomaly_rows.iterrows():
        ratio = row["abs_amount"] / mean if mean else 0
        reason = f"Depense {ratio:.1f}x au-dessus de la moyenne et au-dessus du 95e percentile"
        df.loc[idx, "is_anomaly"] = 1
        df.loc[idx, "anomaly_score"] = round(float(row["zscore"]), 2)
        df.loc[idx, "anomaly_reason"] = reason

    return df
