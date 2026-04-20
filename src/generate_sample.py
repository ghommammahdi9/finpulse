import random
from datetime import datetime, timedelta
from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

faker = Faker('fr_FR')

RECURRING_TEMPLATES = [
    {"merchant": "SALAIRE CY TECH ALTERNANCE", "category": "Salaire", "kind": "credit", "min": 1825, "max": 1885, "day": 2},
    {"merchant": "LOYER RESIDENCE CERGY", "category": "Logement", "kind": "debit", "min": 680, "max": 680, "day": 4},
    {"merchant": "EDF FACTURE ELECTRICITE", "category": "Logement", "kind": "debit", "min": 62, "max": 79, "day": 6},
    {"merchant": "FREE MOBILE FORFAIT", "category": "Abonnements", "kind": "debit", "min": 19.99, "max": 19.99, "day": 8},
    {"merchant": "NETFLIX ABONNEMENT", "category": "Abonnements", "kind": "debit", "min": 13.49, "max": 13.49, "day": 10},
    {"merchant": "SPOTIFY PREMIUM", "category": "Abonnements", "kind": "debit", "min": 9.99, "max": 9.99, "day": 11},
    {"merchant": "BASIC FIT ABONNEMENT", "category": "Abonnements", "kind": "debit", "min": 24.99, "max": 24.99, "day": 13},
    {"merchant": "SNCF TRANSILIEN NAVIGO", "category": "Transport", "kind": "debit", "min": 86.40, "max": 86.40, "day": 16},
]

VARIABLE_MERCHANTS = {
    "Alimentation": [
        "CARREFOUR MARKET", "LIDL", "FRANPRIX", "MONOPRIX", "LECLERC DRIVE", "AUCHAN SUPERMARCHE", "BOULANGERIE DU COIN"
    ],
    "Transport": [
        "UBER TRIP", "RATP RECHARGE NAVIGO", "TOTAL ENERGIES", "SNCF CONNECT", "SHELL STATION"
    ],
    "Restaurants": [
        "UBER EATS", "DELIVEROO", "MCDONALDS", "STARBUCKS", "SUSHI SHOP", "RESTAURANT LE BISTRO", "CAFE FLORE"
    ],
    "Sante": [
        "PHARMACIE CENTRALE", "DOCTOLIB CONSULTATION", "OPTICIEN KRYS", "DOCTOLIB DENTISTE", "PHARMACIE LAFAYETTE"
    ],
    "Shopping": [
        "AMAZON MARKETPLACE", "FNAC", "ZARA", "DECATHLON", "IKEA", "H&M"
    ],
    "Education": [
        "LIBRAIRIE GIBERT", "UDEMY COURS PYTHON", "LIVRES AMAZON"
    ],
    "Loisirs": [
        "CINEMA PATHE", "CINEMA UGC", "STEAM PURCHASE", "CONCERT LA CIGALE"
    ],
    "Autre": [
        "REMBOURSEMENT AMI", "VIREMENT PARENTS", "REMBOURSEMENT CPAM"
    ],
}

CATEGORY_AMOUNT_RANGES = {
    "Alimentation": (4.20, 92.00, "debit"),
    "Transport": (8.50, 58.00, "debit"),
    "Restaurants": (6.80, 42.00, "debit"),
    "Sante": (12.50, 96.00, "debit"),
    "Shopping": (18.00, 165.00, "debit"),
    "Education": (12.00, 49.00, "debit"),
    "Loisirs": (9.50, 58.00, "debit"),
    "Autre": (25.00, 220.00, "credit"),
}

CITY_POOL = ["CERGY", "PARIS", "LA DEFENSE", "PONTOISE", "NANTERRE", "COURBEVOIE"]


def _amount_between(min_amount: float, max_amount: float) -> float:
    value = round(random.uniform(min_amount, max_amount), 2)
    return value


def _sign_amount(amount: float, kind: str) -> float:
    return round(amount if kind == "credit" else -amount, 2)


def _reference() -> str:
    return f"REF {faker.bothify(text='??####').upper()}"


def _city_suffix(merchant: str) -> str:
    if any(keyword in merchant for keyword in ["PARIS", "CERGY", "DEFENSE", "PONTOISE", "COURBEVOIE", "NANTERRE"]):
        return ""
    return f" {random.choice(CITY_POOL)}"


def _description(merchant: str, kind: str) -> str:
    # Keep deterministic keywords for categorisation while using Faker for realistic references.
    variants = [
        f"CB {merchant}{_city_suffix(merchant)} {_reference()}",
        f"PRLV {merchant}{_city_suffix(merchant)} {_reference()}" if kind == "debit" else f"VIR {merchant} {_reference()}",
        f"PAIEMENT {merchant}{_city_suffix(merchant)} {_reference()}",
    ]
    return random.choice(variants)


def _build_transactions(start_date: datetime):
    transactions = []

    for month_offset in range(3):
        month_start = datetime(start_date.year, start_date.month + month_offset, 1)

        for template in RECURRING_TEMPLATES:
            amount = _amount_between(template["min"], template["max"])
            date = month_start + timedelta(days=template["day"] - 1 + random.randint(0, 1))
            transactions.append(
                {
                    "date": date,
                    "description": _description(template["merchant"], template["kind"]),
                    "amount": _sign_amount(amount, template["kind"]),
                    "category": template["category"],
                }
            )

        counts = {
            "Alimentation": random.randint(8, 11),
            "Transport": random.randint(3, 5),
            "Restaurants": random.randint(5, 8),
            "Sante": random.randint(1, 2),
            "Shopping": random.randint(1, 3),
            "Education": random.randint(0, 2),
            "Loisirs": random.randint(1, 3),
            "Autre": random.randint(1, 2),
        }

        for category, count in counts.items():
            min_amount, max_amount, default_kind = CATEGORY_AMOUNT_RANGES[category]
            for _ in range(count):
                merchant = random.choice(VARIABLE_MERCHANTS[category])
                kind = default_kind
                if category == "Autre" and merchant.startswith("VIREMENT"):
                    kind = "credit"
                amount = _amount_between(min_amount, max_amount)
                date = month_start + timedelta(days=random.randint(0, 27))
                transactions.append(
                    {
                        "date": date,
                        "description": _description(merchant, kind),
                        "amount": _sign_amount(amount, kind),
                        "category": category,
                    }
                )

    anomaly_date = start_date + timedelta(days=78)
    transactions.append(
        {
            "date": anomaly_date,
            "description": f"CB VIREMENT EXCEPTIONNEL BANQUE {faker.bothify(text='######')} {_reference()}",
            "amount": -1200.00,
            "category": "Autre",
        }
    )

    transactions.sort(key=lambda item: item["date"])
    return transactions


def generate_sample_pdf(output_path="sample_statement.pdf"):
    holder_name = faker.name().upper()
    iban_hint = f"FR76 {faker.bothify(text='#### #### #### #### #### #### ###').replace('?', '0')}"
    today = datetime.today()
    start_month = today.month - 2
    start_year = today.year
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start_date = datetime(start_year, start_month, 1)
    transactions = _build_transactions(start_date)
    end_date = transactions[-1]["date"]

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    def draw_page_header(page_number: int):
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 45, "RELEVE DE COMPTE BANCAIRE")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 63, f"Periode: {start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}")
        c.drawString(50, height - 78, f"Titulaire: {holder_name}")
        c.drawString(50, height - 93, f"Compte courant: {iban_hint}")
        c.drawRightString(width - 50, height - 63, f"Page {page_number}")
        c.line(50, height - 105, width - 50, height - 105)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, height - 122, "DATE")
        c.drawString(118, height - 122, "DESCRIPTION")
        c.drawRightString(width - 50, height - 122, "MONTANT")
        c.line(50, height - 128, width - 50, height - 128)

    page_number = 1
    draw_page_header(page_number)
    c.setFont("Helvetica", 9)
    y = height - 145

    for tx in transactions:
        date_str = tx["date"].strftime("%d/%m/%Y")
        desc = tx["description"][:52]
        amount_str = f"{tx['amount']:.2f}"

        c.drawString(50, y, date_str)
        c.drawString(118, y, desc)
        c.drawRightString(width - 50, y, amount_str)
        y -= 14

        if y < 60:
            c.showPage()
            page_number += 1
            draw_page_header(page_number)
            c.setFont("Helvetica", 9)
            y = height - 145

    c.save()
    return output_path
