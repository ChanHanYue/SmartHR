#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.invoice.routes import _extract_all
from PyPDF2 import PdfReader

app = create_app()

pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_inv', 'wordpress-pdf-invoice-plugin-sample.pdf'))

reader = PdfReader(pdf_path)
raw = ""
for i in range(min(2, len(reader.pages))):
    text = reader.pages[i].extract_text()
    if text:
        raw += text + "\n"

print("=== RAW PDF TEXT ===")
print(repr(raw))

with app.app_context():
    res = _extract_all(raw)
    print("\n=== EXTRACTED DATA ===")
    for k, v in res.items():
        print(f"{k:15}: {v}")
