#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.invoice.routes import _extract_all
import pytesseract
from app.invoice.routes import _preprocess_image
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = create_app()

img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_inv', 'test1.jpg'))
img = _preprocess_image(img_path)
raw = pytesseract.image_to_string(img, config=r'--oem 3 --psm 4')

with app.app_context():
    res = _extract_all(raw)
    print("=== EXTRACTED DATA ===")
    for k, v in res.items():
        print(f"{k:15}: {v}")
