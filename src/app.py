import io
import os
import sys
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from anomaly import detect_anomalies
from clean import clean_transactions
from database import clear_transactions, create_tables, get_all_transactions, insert_transactions
from extract import extract_transactions_from_pdf
from insights import generate_executive_summary, generate_insights, generate_recommendations
from rules import apply_rule_based_categories, category_quality_stats

st.set_page_config(
    page_title="FinPulse - Analyseur bancaire intelligent",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stApp { background: linear-gradient(180deg, #081120 0%, #0d1726 55%, #111827 100%); }
    .main .block-container { max-width: 1400px; padding-top: 1.25rem; padding-bottom: 3rem; }
    h1, h2, h3, h4, h5, h6 { color: #f8fafc !important; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background: #0b1220; border-right: 1px solid rgba(148, 163, 184, 0.14); }
    [data-testid="stSidebar"] * { color: #dbe7f3; }
    .hero { background: linear-gradient(135deg, rgba(15, 23, 42, 0.96) 0%, rgba(22, 35, 58, 0.96) 100%); border: 1px solid rgba(96, 165, 250, 0.18); border-radius: 20px; padding: 1.45rem 1.6rem 1.2rem 1.6rem; box-shadow: 0 20px 50px rgba(2, 6, 23, 0.30); margin-bottom: 1rem; }
    .hero-topline { display: inline-block; padding: 0.35rem 0.75rem; border-radius: 999px; background: rgba(59, 130, 246, 0.14); color: #cfe3ff; font-size: 0.82rem; margin-bottom: 0.8rem; font-weight: 600; }
    .hero-title { font-size: 2.4rem; font-weight: 800; margin: 0; line-height: 1.05; letter-spacing: -0.03em; }
    .hero-subtitle { margin: 0.55rem 0 0 0; color: #9fb3c8; font-size: 1rem; max-width: 930px; }
    .trust-strip, .exec-strip, .pipeline-strip { display: grid; gap: 0.75rem; margin: 1rem 0 1.2rem 0; }
    .trust-strip { grid-template-columns: repeat(4, minmax(0,1fr)); }
    .exec-strip { grid-template-columns: repeat(4, minmax(0,1fr)); }
    .pipeline-strip { grid-template-columns: repeat(4, minmax(0,1fr)); }
    .card-soft { background: rgba(15, 23, 42, 0.62); border: 1px solid rgba(148, 163, 184, 0.12); border-radius: 14px; padding: 0.9rem 1rem; }
    .card-soft h4, .card-soft p { margin: 0; }
    .muted-label { color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.74rem; font-weight: 700; }
    .big-value { margin-top: 0.34rem; color: #f8fafc; font-size: 1.1rem; font-weight: 750; }
    .small-text { margin-top: 0.3rem; color: #c7d3e0; font-size: 0.9rem; line-height: 1.4; }
    .metric-card { background: linear-gradient(180deg, rgba(15, 23, 42, 0.82) 0%, rgba(17, 24, 39, 0.82) 100%); border: 1px solid rgba(148, 163, 184, 0.12); border-radius: 16px; padding: 1rem 1.1rem; min-height: 118px; }
    .metric-label { color: #94a3b8; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; margin: 0; }
    .metric-value { color: #f8fafc; font-size: 1.95rem; font-weight: 800; margin: 0.45rem 0 0.15rem 0; letter-spacing: -0.03em; }
    .metric-note { color: #9fb3c8; font-size: 0.88rem; margin: 0; }
    .section-title { color: #f8fafc; font-size: 1.28rem; font-weight: 750; margin: 1.4rem 0 0.85rem 0; letter-spacing: -0.02em; }
    .insight-card { background: rgba(15, 23, 42, 0.72); border: 1px solid rgba(148, 163, 184, 0.10); border-left: 4px solid; border-radius: 14px; padding: 1rem 1.05rem; margin-bottom: 0.8rem; }
    .insight-title { margin: 0; color: #f8fafc; font-weight: 700; font-size: 1rem; }
    .insight-text { margin: 0.35rem 0 0 0; color: #c7d3e0; line-height: 1.45; font-size: 0.92rem; }
    .insight-info { border-left-color: #60a5fa; }
    .insight-success { border-left-color: #34d399; }
    .insight-warning { border-left-color: #f59e0b; }
    .insight-danger { border-left-color: #ef4444; }
    .footer { text-align: center; padding: 2rem 0 0.5rem 0; color: #72839a; font-size: 0.88rem; margin-top: 2rem; border-top: 1px solid rgba(148, 163, 184, 0.12); }
    a { color: #7cc0ff !important; }
    @media (max-width: 900px) { .trust-strip, .exec-strip, .pipeline-strip { grid-template-columns: 1fr 1fr; } .hero-title { font-size: 2rem; } }
</style>
""",
    unsafe_allow_html=True,
)

create_tables()


def fmt_eur(value: float) -> str:
    return f"{value:,.2f} €".replace(",", " ")


def store_dataframe(df: pd.DataFrame):
    clear_transactions()
    insert_transactions(df)


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = clean_transactions(df)
    df = apply_rule_based_categories(df)
    df = detect_anomalies(df)
    return df


def simulate_scenario(df: pd.DataFrame, restaurants_cut: int, subscriptions_cut: int, shopping_cut: int):
    sim = df.copy()
    sim["amount"] = pd.to_numeric(sim["amount"], errors="coerce")
    expense_mask = sim["amount"] < 0
    for category, pct in {
        "Restaurants": restaurants_cut,
        "Abonnements": subscriptions_cut,
        "Shopping": shopping_cut,
    }.items():
        mask = expense_mask & (sim.get("category", "") == category)
        sim.loc[mask, "amount"] = sim.loc[mask, "amount"] * (1 - pct / 100)
    return sim


def build_report_pdf(df: pd.DataFrame, quality: dict, summary: list, recommendations: list) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    def line(text, size=10, bold=False, gap=14):
        nonlocal y
        if y < 60:
            c.showPage()
            y = height - 50
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(45, y, text)
        y -= gap

    data = df.copy()
    data["amount"] = pd.to_numeric(data["amount"], errors="coerce")
    total_income = float(data[data["amount"] > 0]["amount"].sum()) if not data.empty else 0.0
    total_expenses = abs(float(data[data["amount"] < 0]["amount"].sum())) if not data.empty else 0.0
    net = total_income - total_expenses

    line("FinPulse - Rapport de synthese", 16, True, 22)
    line(f"Genere le {datetime.now().strftime('%d/%m/%Y %H:%M')}", 9)
    line(f"Transactions analysees : {len(df)}", 10)
    line(f"Revenus : {fmt_eur(total_income)}  |  Depenses : {fmt_eur(total_expenses)}  |  Solde net : {fmt_eur(net)}", 10)
    line(f"Taux categorise : {quality['categorised_pct']}%  |  A revoir : {quality['low_confidence_count']}  |  Anomalies : {int((df.get('is_anomaly', 0) == 1).sum())}", 10, gap=18)

    line("Resume executif", 13, True, 18)
    for block in summary:
        line(f"- {block['title']} : {block['value']} - {block['text']}", 10)

    y -= 8
    line("Recommandations", 13, True, 18)
    for rec in recommendations:
        line(f"- {rec['title']} : {rec['text']}", 10)

    y -= 8
    line("Top categories", 13, True, 18)
    expenses = data[data['amount'] < 0].copy()
    if not expenses.empty and 'category' in expenses.columns:
        cat = expenses.groupby('category')['amount'].sum().abs().sort_values(ascending=False).head(5)
        for name, value in cat.items():
            line(f"- {name} : {fmt_eur(float(value))}", 10)

    y -= 8
    line("Transactions atypiques", 13, True, 18)
    anomalies = data[data.get('is_anomaly', 0) == 1].copy()
    if anomalies.empty:
        line("- Aucune anomalie detectee", 10)
    else:
        for _, row in anomalies.head(5).iterrows():
            reason = row.get('anomaly_reason', '')
            line(f"- {str(row.get('date', ''))[:10]} | {row.get('description', '')[:50]} | {fmt_eur(abs(float(row['amount'])))} | {reason}", 9)

    c.save()
    buffer.seek(0)
    return buffer.getvalue()


st.markdown(
    """
<div class="hero">
    <div class="hero-topline">Portfolio data project · Mahdi Ghommam</div>
    <h1 class="hero-title">FinPulse</h1>
    <p class="hero-subtitle">Analyseur de relevés bancaires combinant extraction PDF, normalisation des marchands, catégorisation automatique, contrôle de qualité, simulation budgétaire et rapport exportable.</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Configuration")
    st.markdown("Pipeline local : extraction PDF, règles métier, qualité, anomalies, export PDF.")
    st.markdown("---")
    use_sample = st.button("Générer un relevé démo", type="primary", use_container_width=True)
    uploaded_file = st.file_uploader("Uploader un PDF bancaire", type=["pdf"])
    st.caption("Le mode démo crée un historique synthétique mais réaliste sur trois mois.")
    st.markdown("---")
    if st.button("Effacer les données", use_container_width=True):
        clear_transactions()
        st.success("Base réinitialisée")
        st.rerun()
    st.markdown("---")
    st.markdown("### Liens")
    st.markdown("[GitHub](https://github.com/mahdighommam/finpulse)")
    st.markdown("[Portfolio](https://mahdighommam.github.io)")

if use_sample:
    with st.spinner("Génération et chargement du relevé démo..."):
        from generate_sample import generate_sample_pdf
        pdf_path = generate_sample_pdf("sample_statement.pdf")
        demo_df = extract_transactions_from_pdf(pdf_path)
        demo_df = prepare_dataframe(demo_df)
        store_dataframe(demo_df)
        st.success(f"{len(demo_df)} transactions chargées avec normalisation locale.")
        st.rerun()

if uploaded_file is not None:
    with st.spinner("Extraction des transactions en cours..."):
        with open("temp_upload.pdf", "wb") as f:
            f.write(uploaded_file.read())
        extracted = extract_transactions_from_pdf("temp_upload.pdf")
        extracted = prepare_dataframe(extracted)
        store_dataframe(extracted)
        st.success(f"{len(extracted)} transactions analysées.")
        st.rerun()

df = get_all_transactions()

if df.empty:
    st.markdown(
        """
<div class="trust-strip">
    <div class="card-soft"><p class="muted-label">Positionnement</p><p class="big-value">Projet portfolio finance</p><p class="small-text">Conçu pour des entretiens Data / IA.</p></div>
    <div class="card-soft"><p class="muted-label">Pipeline</p><p class="big-value">PDF → DataFrame → SQLite</p><p class="small-text">Lecture, extraction, normalisation et stockage local.</p></div>
    <div class="card-soft"><p class="muted-label">Analyse</p><p class="big-value">Règles + anomalies</p><p class="small-text">Interprétation métier et signaux explicables.</p></div>
    <div class="card-soft"><p class="muted-label">Objectif</p><p class="big-value">Démo entretien</p><p class="small-text">Montrer ETL, qualité et valeur métier.</p></div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.info("Commence par charger un PDF ou lancer le relevé démo pour afficher l'analyse complète.")
    st.stop()

# Data prep
for col in ["amount"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
if "date" in df.columns:
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["amount"])

expenses = df[df["amount"] < 0].copy()
incomes = df[df["amount"] > 0].copy()
anomalies = df[df.get("is_anomaly", 0) == 1].copy()

total_in = float(incomes["amount"].sum()) if not incomes.empty else 0.0
total_out = float(expenses["amount"].sum()) if not expenses.empty else 0.0
balance = total_in + total_out
stats = category_quality_stats(df)
summary = generate_executive_summary(df)
recommendations = generate_recommendations(df)
insights = generate_insights(df)

if "date" in df.columns and df["date"].notna().any():
    min_date = df["date"].min().strftime("%d/%m/%Y")
    max_date = df["date"].max().strftime("%d/%m/%Y")
    date_range = f"{min_date} → {max_date}"
else:
    date_range = "Période indisponible"

report_bytes = build_report_pdf(df, stats, summary, recommendations)

header_left, header_right = st.columns([4, 1])
with header_left:
    st.markdown(
        f"""
<div class="trust-strip">
    <div class="card-soft"><p class="muted-label">Période analysée</p><p class="big-value">{date_range}</p><p class="small-text">Fenêtre d'analyse active.</p></div>
    <div class="card-soft"><p class="muted-label">Transactions</p><p class="big-value">{len(df)}</p><p class="small-text">Lignes extraites et nettoyées.</p></div>
    <div class="card-soft"><p class="muted-label">Taux catégorisé</p><p class="big-value">{stats['categorised_pct']}%</p><p class="small-text">Qualité de couverture métier.</p></div>
    <div class="card-soft"><p class="muted-label">Anomalies détectées</p><p class="big-value">{len(anomalies)}</p><p class="small-text">Signaux de dépenses atypiques.</p></div>
</div>
""",
        unsafe_allow_html=True,
    )
with header_right:
    st.download_button(
        "Exporter rapport PDF",
        data=report_bytes,
        file_name="finpulse_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

st.markdown("<h2 class='section-title'>Résumé exécutif</h2>", unsafe_allow_html=True)
exec_html = "<div class='exec-strip'>"
for block in summary:
    exec_html += f"<div class='card-soft'><p class='muted-label'>{block['title']}</p><p class='big-value'>{block['value']}</p><p class='small-text'>{block['text']}</p></div>"
exec_html += "</div>"
st.markdown(exec_html, unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"<div class='metric-card'><p class='metric-label'>Balance nette</p><p class='metric-value'>{fmt_eur(balance)}</p><p class='metric-note'>{'Solde final positif' if balance >= 0 else 'Solde final négatif'}</p></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><p class='metric-label'>Revenus</p><p class='metric-value' style='color:#34d399;'>{fmt_eur(total_in)}</p><p class='metric-note'>Flux créditeurs identifiés</p></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-card'><p class='metric-label'>Dépenses</p><p class='metric-value' style='color:#f87171;'>{fmt_eur(abs(total_out))}</p><p class='metric-note'>Somme des débits observés</p></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='metric-card'><p class='metric-label'>Qualité données</p><p class='metric-value' style='color:#7cc0ff;'>{stats['categorised_pct']}%</p><p class='metric-note'>{stats['low_confidence_count']} transaction(s) à revoir</p></div>", unsafe_allow_html=True)

biz_tab, pipe_tab, tx_tab = st.tabs(["Vue métier", "Vue pipeline", "Transactions"])

with biz_tab:
    st.markdown("<h2 class='section-title'>Recommandations et insights</h2>", unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        for rec in recommendations:
            st.markdown(f"<div class='insight-card insight-{rec['type']}'><p class='insight-title'>💡 {rec['title']}</p><p class='insight-text'>{rec['text']}</p></div>", unsafe_allow_html=True)
    with right:
        for ins in insights:
            st.markdown(f"<div class='insight-card insight-{ins['type']}'><p class='insight-title'>{ins['icon']} {ins['title']}</p><p class='insight-text'>{ins['text']}</p></div>", unsafe_allow_html=True)

    st.markdown("<h2 class='section-title'>Analyse visuelle</h2>", unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        if not expenses.empty and "category" in expenses.columns:
            cat_data = expenses.groupby("category")["amount"].sum().abs().reset_index().sort_values("amount", ascending=False)
            fig = px.bar(cat_data, x="amount", y="category", orientation="h", text="amount", color="amount", color_continuous_scale=["#1d4ed8", "#60a5fa"])
            fig.update_traces(texttemplate="%{text:.0f} €", textposition="outside")
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e5eef7", height=390, showlegend=False, xaxis_title="Montant (€)", yaxis_title="", margin=dict(l=0, r=20, t=10, b=0), coloraxis_showscale=False)
            fig.update_xaxes(gridcolor="rgba(255,255,255,0.08)")
            fig.update_yaxes(gridcolor="rgba(255,255,255,0.00)")
            st.plotly_chart(fig, use_container_width=True)
    with right:
        if "date" in df.columns and df["date"].notna().any():
            df_sorted = df.sort_values("date").copy()
            df_sorted["solde_cumule"] = df_sorted["amount"].cumsum()
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df_sorted["date"], y=df_sorted["solde_cumule"], mode="lines+markers", line=dict(color="#7cc0ff", width=3), marker=dict(size=6, color="#7cc0ff"), fill="tozeroy", fillcolor="rgba(124,192,255,0.10)"))
            fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e5eef7", height=390, showlegend=False, xaxis_title="Date", yaxis_title="€", margin=dict(l=0, r=0, t=10, b=0))
            fig2.update_xaxes(gridcolor="rgba(255,255,255,0.08)")
            fig2.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<h2 class='section-title'>Simulation budgétaire</h2>", unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    with s1:
        restaurants_cut = st.slider("Réduction restaurants (%)", 0, 50, 15, 5)
    with s2:
        subscriptions_cut = st.slider("Réduction abonnements (%)", 0, 50, 20, 5)
    with s3:
        shopping_cut = st.slider("Réduction shopping (%)", 0, 50, 10, 5)

    simulated = simulate_scenario(df, restaurants_cut, subscriptions_cut, shopping_cut)
    sim_income = float(simulated[simulated["amount"] > 0]["amount"].sum()) if not simulated.empty else 0.0
    sim_out = float(simulated[simulated["amount"] < 0]["amount"].sum()) if not simulated.empty else 0.0
    sim_balance = sim_income + sim_out
    delta = sim_balance - balance

    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Balance simulée", fmt_eur(sim_balance))
    sc2.metric("Gain potentiel", fmt_eur(delta), delta=fmt_eur(delta))
    sc3.metric("Dépenses simulées", fmt_eur(abs(sim_out)))

with pipe_tab:
    st.markdown("<h2 class='section-title'>Qualité du pipeline</h2>", unsafe_allow_html=True)
    pipeline_html = f"""
<div class='pipeline-strip'>
  <div class='card-soft'><p class='muted-label'>Extraction</p><p class='big-value'>{len(df)} lignes utiles</p><p class='small-text'>Transactions extraites depuis le PDF puis normalisées.</p></div>
  <div class='card-soft'><p class='muted-label'>Règles locales</p><p class='big-value'>{stats['rules_count']}</p><p class='small-text'>Transactions classées via dictionnaire métier.</p></div>
  <div class='card-soft'><p class='muted-label'>À revoir</p><p class='big-value'>{stats['low_confidence_count']}</p><p class='small-text'>Libellés à faible confiance ou non reconnus.</p></div>
  <div class='card-soft'><p class='muted-label'>Anomalies</p><p class='big-value'>{len(anomalies)}</p><p class='small-text'>Dépenses exceptionnelles avec explication.</p></div>
</div>
"""
    st.markdown(pipeline_html, unsafe_allow_html=True)

    pq1, pq2 = st.columns([1.2, 1.8])
    with pq1:
        source_counts = pd.DataFrame({
            "Source": ["Règles locales", "LLM (option)"],
            "Count": [stats["rules_count"], stats["llm_count"]],
        })
        fig_source = px.pie(source_counts, names="Source", values="Count", hole=0.55, color="Source", color_discrete_map={"Règles locales": "#60a5fa", "LLM (option)": "#34d399"})
        fig_source.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#e5eef7", height=320, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_source, use_container_width=True)
    with pq2:
        review_df = df[df.get("category_confidence", "") == "A revoir"].copy()
        if review_df.empty:
            st.success("Aucune transaction à faible confiance sur ce jeu de données.")
        else:
            show = review_df[["date", "description", "merchant_normalized", "category", "category_reason"]].copy()
            show["date"] = show["date"].astype(str).str[:10]
            show.columns = ["Date", "Libellé brut", "Marchand normalisé", "Catégorie", "Pourquoi revoir"]
            st.dataframe(show, use_container_width=True, hide_index=True, height=320)

    st.markdown("<h2 class='section-title'>Anomalies explicables</h2>", unsafe_allow_html=True)
    if anomalies.empty:
        st.info("Aucune anomalie détectée sur la période courante.")
    else:
        expl = anomalies[["date", "description", "amount", "anomaly_score", "anomaly_reason"]].copy()
        expl["date"] = expl["date"].astype(str).str[:10]
        expl["amount"] = expl["amount"].map(lambda x: fmt_eur(abs(float(x))))
        expl.columns = ["Date", "Libellé", "Montant", "Score", "Explication"]
        st.dataframe(expl, use_container_width=True, hide_index=True, height=300)

with tx_tab:
    st.markdown("<h2 class='section-title'>Transactions détaillées</h2>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        cat_filter = st.multiselect("Filtrer par catégorie", options=sorted(df["category"].dropna().unique()) if "category" in df.columns else [])
    with f2:
        type_filter = st.selectbox("Type", ["Toutes", "Dépenses", "Revenus", "Anomalies"])
    with f3:
        search = st.text_input("Rechercher un libellé")

    filtered = df.copy()
    if cat_filter:
        filtered = filtered[filtered["category"].isin(cat_filter)]
    if type_filter == "Dépenses":
        filtered = filtered[filtered["amount"] < 0]
    elif type_filter == "Revenus":
        filtered = filtered[filtered["amount"] > 0]
    elif type_filter == "Anomalies":
        filtered = filtered[filtered["is_anomaly"] == 1]
    if search:
        filtered = filtered[filtered["description"].str.contains(search, case=False, na=False)]

    display_df = filtered.copy()
    display_df["date"] = display_df["date"].astype(str).str[:10]
    display_df["amount"] = display_df["amount"].map(lambda x: fmt_eur(float(x)))
    display_df["is_anomaly"] = display_df["is_anomaly"].map(lambda x: "Oui" if x == 1 else "Non")
    keep_cols = ["date", "description", "merchant_normalized", "category", "category_confidence", "amount", "is_anomaly"]
    display_df = display_df[keep_cols].rename(columns={
        "date": "Date",
        "description": "Libellé brut",
        "merchant_normalized": "Marchand normalisé",
        "category": "Catégorie",
        "category_confidence": "Confiance",
        "amount": "Montant",
        "is_anomaly": "Anomalie",
    })
    st.dataframe(display_df, use_container_width=True, height=450, hide_index=True)

st.markdown(
    """
<div class="footer">
    FinPulse · Streamlit · Plotly · SQLite · Normalisation marchands · Détection d anomalies · Export PDF<br>
    <a href="https://github.com/mahdighommam/finpulse">GitHub</a> ·
    <a href="https://mahdighommam.github.io">Portfolio</a>
</div>
""",
    unsafe_allow_html=True,
)
