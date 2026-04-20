import pandas as pd


def _fmt_eur(value: float) -> str:
    return f"{value:,.0f} €".replace(",", " ")


def _safe_ratio(a: float, b: float) -> float:
    return (a / b * 100) if b else 0.0


def generate_executive_summary(df: pd.DataFrame):
    if df.empty:
        return []

    data = df.copy()
    data["amount"] = pd.to_numeric(data["amount"], errors="coerce")
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["amount"])

    expenses = data[data["amount"] < 0].copy()
    incomes = data[data["amount"] > 0].copy()
    total_income = float(incomes["amount"].sum()) if not incomes.empty else 0.0
    total_expenses = abs(float(expenses["amount"].sum())) if not expenses.empty else 0.0
    net = total_income - total_expenses

    blocks = []
    situation = "excédentaire" if net >= 0 else "déficitaire"
    blocks.append({
        "title": "Situation globale",
        "value": f"Budget {situation}",
        "text": f"Solde net de {_fmt_eur(net)} sur la période analysée.",
        "type": "success" if net >= 0 else "danger",
    })

    if not expenses.empty and "category" in expenses.columns:
        cat_totals = expenses.groupby("category")["amount"].sum().abs().sort_values(ascending=False)
        if not cat_totals.empty:
            top_cat = cat_totals.index[0]
            top_amt = float(cat_totals.iloc[0])
            blocks.append({
                "title": "Poste de coût majeur",
                "value": top_cat,
                "text": f"{top_cat} pèse {_fmt_eur(top_amt)}, soit {_safe_ratio(top_amt, total_expenses):.1f}% des dépenses.",
                "type": "info",
            })

    anomalies = data[data.get("is_anomaly", 0) == 1]
    blocks.append({
        "title": "Surveillance",
        "value": f"{len(anomalies)} anomalie(s)",
        "text": "Transactions à revoir manuellement pour distinguer dépense exceptionnelle et signal faible.",
        "type": "warning" if len(anomalies) else "success",
    })

    subs = expenses[expenses["category"] == "Abonnements"] if "category" in expenses.columns else pd.DataFrame()
    subs_total = abs(float(subs["amount"].sum())) if not subs.empty else 0.0
    blocks.append({
        "title": "Abonnements",
        "value": _fmt_eur(subs_total),
        "text": f"Les services récurrents représentent {_safe_ratio(subs_total, total_expenses):.1f}% des dépenses.",
        "type": "warning" if subs_total > 50 else "info",
    })
    return blocks


def generate_recommendations(df: pd.DataFrame):
    recs = []
    if df.empty:
        return recs

    data = df.copy()
    data["amount"] = pd.to_numeric(data["amount"], errors="coerce")
    expenses = data[data["amount"] < 0].copy()
    if expenses.empty:
        return recs

    total_expenses = abs(float(expenses["amount"].sum()))

    subs = expenses[expenses["category"] == "Abonnements"] if "category" in expenses.columns else pd.DataFrame()
    subs_total = abs(float(subs["amount"].sum())) if not subs.empty else 0.0
    if subs_total > 0:
        recs.append({
            "title": "Rationaliser les abonnements",
            "text": f"Une réduction de 20% des abonnements libérerait environ {_fmt_eur(subs_total * 0.2)} sur la période.",
            "type": "warning",
        })

    restaurants = expenses[expenses["category"] == "Restaurants"] if "category" in expenses.columns else pd.DataFrame()
    resto_total = abs(float(restaurants["amount"].sum())) if not restaurants.empty else 0.0
    if resto_total > 0:
        recs.append({
            "title": "Maîtriser la restauration",
            "text": f"Une baisse de 15% des repas à l'extérieur représenterait {_fmt_eur(resto_total * 0.15)} d'économies potentielles.",
            "type": "info",
        })

    uncategorised = int((data.get("category", pd.Series(dtype=str)) == "Non categorise").sum())
    if uncategorised > 0:
        recs.append({
            "title": "Améliorer la qualité de données",
            "text": f"{uncategorised} transaction(s) restent non catégorisées. Ajouter des règles de normalisation augmentera la fiabilité métier.",
            "type": "danger",
        })

    anomalies = data[data.get("is_anomaly", 0) == 1]
    if len(anomalies):
        biggest = anomalies.assign(abs_amount=anomalies["amount"].abs()).sort_values("abs_amount", ascending=False).iloc[0]
        recs.append({
            "title": "Analyser la dépense atypique",
            "text": f"La transaction « {biggest['description']} » mérite une revue, car elle pèse {_safe_ratio(abs(float(biggest['amount'])), total_expenses):.1f}% des dépenses.",
            "type": "warning",
        })

    return recs[:4]


def generate_insights(df: pd.DataFrame):
    insights = []
    if df.empty:
        return insights

    data = df.copy()
    data["amount"] = pd.to_numeric(data["amount"], errors="coerce")
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["amount", "date"])
    expenses = data[data["amount"] < 0].copy()
    income = data[data["amount"] > 0].copy()

    total_expenses = abs(float(expenses["amount"].sum())) if not expenses.empty else 0.0
    total_income = float(income["amount"].sum()) if not income.empty else 0.0

    if not expenses.empty and "category" in expenses.columns:
        cat_totals = expenses.groupby("category")["amount"].sum().abs().sort_values(ascending=False)
        if not cat_totals.empty:
            top_cat = cat_totals.index[0]
            top_amt = float(cat_totals.iloc[0])
            insights.append({
                "icon": "📊",
                "title": "Structure des dépenses",
                "text": f"La catégorie {top_cat} domine avec {_fmt_eur(top_amt)}, soit {_safe_ratio(top_amt, total_expenses):.1f}% des débits.",
                "type": "info",
            })

    if not expenses.empty:
        monthly = expenses.assign(month=expenses["date"].dt.to_period("M")).groupby("month")["amount"].sum().abs()
        if len(monthly) >= 2:
            last = float(monthly.iloc[-1])
            prev = float(monthly.iloc[-2])
            if prev:
                change = ((last - prev) / prev) * 100
                insights.append({
                    "icon": "📈" if change > 0 else "📉",
                    "title": "Tendance récente",
                    "text": f"Les dépenses {'progressent' if change > 0 else 'reculent'} de {abs(change):.1f}% entre les deux derniers mois.",
                    "type": "warning" if abs(change) >= 10 else "info",
                })

    subs = expenses[expenses.get("category") == "Abonnements"] if "category" in expenses.columns else pd.DataFrame()
    if not subs.empty:
        subs_total = abs(float(subs["amount"].sum()))
        insights.append({
            "icon": "🔁",
            "title": "Poids des coûts récurrents",
            "text": f"Les abonnements représentent {_fmt_eur(subs_total)}, soit {_safe_ratio(subs_total, total_expenses):.1f}% des dépenses.",
            "type": "warning" if subs_total > 75 else "info",
        })

    anomalies = data[data.get("is_anomaly", 0) == 1]
    if not anomalies.empty:
        biggest = anomalies.nlargest(1, "amount").iloc[0]
        reason = biggest.get("anomaly_reason") or "Transaction au-dessus du comportement habituel"
        label = biggest.get("description") or "libellé indisponible"
        insights.append({
            "icon": "⚠️",
            "title": "Anomalie explicable",
            "text": f"{reason} · libellé {label}",
            "type": "danger",
            })

    if total_income > 0 and total_expenses > 0:
        savings_rate = ((total_income - total_expenses) / total_income) * 100
        insights.append({
            "icon": "💡",
            "title": "Taux d'épargne",
            "text": f"Le taux d'épargne estimé ressort à {savings_rate:.1f}%. {'Profil sain' if savings_rate >= 15 else 'Une optimisation reste possible'}.",
            "type": "success" if savings_rate >= 15 else "warning",
        })

    return insights[:5]
