#!/usr/bin/env python3
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.invoice.routes import (
    _extract_all, _preprocess_image, _TAX_RE, _SERVICE_CHARGE_RE,
    _TOTAL_RE, _SUBTOTAL_RE,
)
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

img_path = r'C:\Users\chanh\.cursor\projects\c-Users-chanh-OneDrive-Tunku-Abdul-Rahman-University-College-FYP-smarthr-app-V3\assets\c__Users_chanh_OneDrive_-_Tunku_Abdul_Rahman_University_College_FYP_smarthr_app_V3_test_inv_IMG_20260529_165035_1_.jpg'

img = _preprocess_image(img_path)
raw = pytesseract.image_to_string(img, config=r'--oem 3 --psm 4')
print('=== RAW OCR ===')
print(raw)
print('=== EXTRACTED ===')
app = create_app()
with app.app_context():
    res = _extract_all(raw)
    for k, v in res.items():
        print(f'{k}: {v}')

print('\n=== TAX MATCHES ===')
for m in _TAX_RE.finditer(raw):
    print(repr(m.group(0)), '->', m.group(1))
print('\n=== SERVICE CHARGE MATCHES ===')
for m in _SERVICE_CHARGE_RE.finditer(raw):
    print(repr(m.group(0)), '->', m.group(1))
print('\n=== TOTAL MATCHES ===')
for m in _TOTAL_RE.finditer(raw):
    print(repr(m.group(0)), '->', m.group(1))
print('\n=== SUBTOTAL MATCHES ===')
for m in _SUBTOTAL_RE.finditer(raw):
    print(repr(m.group(0)), '->', m.group(1))
