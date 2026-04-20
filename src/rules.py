import re
import pandas as pd

MERCHANT_RULES = [
    {"merchant": "SALAIRE", "category": "Salaire", "patterns": [r"\bSALAIRE\b", r"\bPAYROLL\b", r"\bPAIE\b", r"\bBOURSE\b"]},
    {"merchant": "LOYER", "category": "Logement", "patterns": [r"\bLOYER\b", r"RESIDENCE", r"\bRENT\b"]},
    {"merchant": "EDF", "category": "Logement", "patterns": [r"\bEDF\b", r"ELECTRICITE"]},
    {"merchant": "ENGIE", "category": "Logement", "patterns": [r"\bENGIE\b", r"\bGAZ\b"]},
    {"merchant": "FREE MOBILE", "category": "Abonnements", "patterns": [r"FREE MOBILE", r"\bORANGE\b", r"\bSFR\b"]},
    {"merchant": "NETFLIX", "category": "Abonnements", "patterns": [r"NETFLIX"]},
    {"merchant": "SPOTIFY", "category": "Abonnements", "patterns": [r"SPOTIFY"]},
    {"merchant": "BASIC FIT", "category": "Abonnements", "patterns": [r"BASIC FIT"]},
    {"merchant": "AMAZON PRIME", "category": "Abonnements", "patterns": [r"AMAZON PRIME", r"YOUTUBE PREMIUM", r"ADOBE", r"GITHUB", r"OPENAI"]},
    {"merchant": "CARREFOUR", "category": "Alimentation", "patterns": [r"CARREFOUR"]},
    {"merchant": "LIDL", "category": "Alimentation", "patterns": [r"\bLIDL\b"]},
    {"merchant": "FRANPRIX", "category": "Alimentation", "patterns": [r"FRANPRIX"]},
    {"merchant": "MONOPRIX", "category": "Alimentation", "patterns": [r"MONOPRIX"]},
    {"merchant": "LECLERC", "category": "Alimentation", "patterns": [r"LECLERC"]},
    {"merchant": "AUCHAN", "category": "Alimentation", "patterns": [r"AUCHAN"]},
    {"merchant": "BOULANGERIE", "category": "Alimentation", "patterns": [r"BOULANGERIE"]},
    {"merchant": "UBER EATS", "category": "Restaurants", "patterns": [r"UBER EATS"]},
    {"merchant": "DELIVEROO", "category": "Restaurants", "patterns": [r"DELIVEROO"]},
    {"merchant": "MCDONALDS", "category": "Restaurants", "patterns": [r"MCDONALDS"]},
    {"merchant": "STARBUCKS", "category": "Restaurants", "patterns": [r"STARBUCKS"]},
    {"merchant": "SUSHI SHOP", "category": "Restaurants", "patterns": [r"SUSHI"]},
    {"merchant": "CAFE", "category": "Restaurants", "patterns": [r"\bCAFE\b", r"RESTAURANT", r"BURGER KING", r"\bKFC\b"]},
    {"merchant": "SNCF", "category": "Transport", "patterns": [r"\bSNCF\b", r"TRANSILIEN", r"CONNECT"]},
    {"merchant": "RATP", "category": "Transport", "patterns": [r"\bRATP\b", r"NAVIGO"]},
    {"merchant": "UBER", "category": "Transport", "patterns": [r"UBER TRIP"]},
    {"merchant": "TOTAL ENERGIES", "category": "Transport", "patterns": [r"TOTAL", r"ESSENCE"]},
    {"merchant": "SHELL", "category": "Transport", "patterns": [r"\bSHELL\b", r"\bBP\b"]},
    {"merchant": "PHARMACIE", "category": "Sante", "patterns": [r"PHARMACIE"]},
    {"merchant": "DOCTOLIB", "category": "Sante", "patterns": [r"DOCTOLIB", r"MEDECIN", r"DENTISTE"]},
    {"merchant": "OPTICIEN", "category": "Sante", "patterns": [r"OPTICIEN"]},
    {"merchant": "AMAZON", "category": "Shopping", "patterns": [r"AMAZON MARKETPLACE", r"AMAZON"]},
    {"merchant": "FNAC", "category": "Shopping", "patterns": [r"\bFNAC\b"]},
    {"merchant": "ZARA", "category": "Shopping", "patterns": [r"\bZARA\b"]},
    {"merchant": "DECATHLON", "category": "Shopping", "patterns": [r"DECATHLON"]},
    {"merchant": "IKEA", "category": "Shopping", "patterns": [r"\bIKEA\b"]},
    {"merchant": "H&M", "category": "Shopping", "patterns": [r"H&M", r"\bHM\b"]},
    {"merchant": "LIBRAIRIE", "category": "Education", "patterns": [r"LIBRAIRIE"]},
    {"merchant": "UDEMY", "category": "Education", "patterns": [r"UDEMY", r"\bCOURS\b", r"LIVRES"]},
    {"merchant": "PATHE", "category": "Loisirs", "patterns": [r"PATHE", r"CINEMA"]},
    {"merchant": "UGC", "category": "Loisirs", "patterns": [r"\bUGC\b"]},
    {"merchant": "STEAM", "category": "Loisirs", "patterns": [r"STEAM"]},
    {"merchant": "CONCERT", "category": "Loisirs", "patterns": [r"CONCERT"]},
    {"merchant": "REMBOURSEMENT", "category": "Autre", "patterns": [r"REMBOURSEMENT"]},
    {"merchant": "VIREMENT", "category": "Autre", "patterns": [r"\bVIREMENT\b"]},
]

GENERIC_PREFIXES = [
    r"\bCB\b", r"\bPRLV\b", r"\bPAIEMENT\b", r"\bVIR\b", r"\bVIR SEPA\b", r"\bCARTE\b"
]
GENERIC_SUFFIXES = [
    r"REF\s+[A-Z0-9]+", r"\bPARIS\b", r"\bCERGY\b", r"\bLA DEFENSE\b", r"\bPONTOISE\b", r"\bNANTERRE\b", r"\bCOURBEVOIE\b"
]


def _cleanup_description(desc: str) -> str:
    text = str(desc).upper().strip()
    for pattern in GENERIC_PREFIXES:
        text = re.sub(pattern, " ", text)
    for pattern in GENERIC_SUFFIXES:
        text = re.sub(pattern, " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text


def _guess_from_cleaned(cleaned: str) -> tuple[str, str, str, str]:
    if not cleaned:
        return "Non categorise", "Inconnu", "A revoir", "Libelle vide"

    for rule in MERCHANT_RULES:
        if any(re.search(pattern, cleaned) for pattern in rule["patterns"]):
            return rule["category"], rule["merchant"], "Elevee", f"Regle locale sur {rule['merchant']}"

    first_words = " ".join(cleaned.split()[:2]) if cleaned.split() else cleaned
    return "Non categorise", first_words or "Inconnu", "A revoir", "Aucune regle locale correspondante"


def apply_rule_based_categories(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()
    if "description" not in result.columns:
        return result

    result["description"] = result["description"].fillna("").astype(str)
    result["merchant_normalized"] = result["description"].map(_cleanup_description)

    categories = []
    merchants = []
    sources = []
    confidences = []
    reasons = []

    for raw_desc, cleaned in zip(result["description"], result["merchant_normalized"]):
        category, merchant, confidence, reason = _guess_from_cleaned(cleaned)
        categories.append(category)
        merchants.append(merchant)
        confidences.append(confidence)
        reasons.append(reason)
        sources.append("Regles locales")

    result["category"] = categories
    result["merchant_normalized"] = merchants
    result["category_source"] = sources
    result["category_confidence"] = confidences
    result["category_reason"] = reasons
    return result



def category_quality_stats(df: pd.DataFrame) -> dict:
    if df.empty or "category" not in df.columns:
        return {
            "categorised_pct": 0.0,
            "uncategorised_count": 0,
            "low_confidence_count": 0,
            "rules_count": 0,
            "llm_count": 0,
        }

    total = len(df)
    uncategorised = int((df["category"] == "Non categorise").sum())
    low_conf = int((df.get("category_confidence", "") == "A revoir").sum())
    source_series = df.get("category_source", pd.Series(dtype=str)).fillna("")
    rules_count = int((source_series == "Regles locales").sum())
    llm_count = int((source_series == "LLM").sum())
    categorised_pct = round(((total - uncategorised) / total) * 100, 1) if total else 0.0
    return {
        "categorised_pct": categorised_pct,
        "uncategorised_count": uncategorised,
        "low_confidence_count": low_conf,
        "rules_count": rules_count,
        "llm_count": llm_count,
    }
