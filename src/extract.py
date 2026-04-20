import pdfplumber
import pandas as pd
import re

def extract_transactions_from_pdf(pdf_path):
    transactions = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            for line in text.split("\n"):
                match = re.search(r"(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([-+]?\d+[.,]\d{2})", line)
                if match:
                    date, description, amount = match.groups()
                    amount = float(amount.replace(",", "."))
                    transactions.append({"date": date, "description": description.strip(), "amount": amount, "category": "Non categorise", "is_anomaly": 0})
    return pd.DataFrame(transactions)