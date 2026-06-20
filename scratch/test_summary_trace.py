#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import re
import pytesseract
from app.invoice.routes import _preprocess_image

img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_inv', 'test1.jpg'))
img = _preprocess_image(img_path)
raw = pytesseract.image_to_string(img, config=r'--oem 3 --psm 4')

text = raw
# Normalize EU numbers (space for thousands, comma for decimals) to US standard
text = re.sub(r'\b(\d{1,3})\s(\d{3}),(\d{2})\b', r'\1\2.\3', text)
text = re.sub(r'\b(\d{1,3})\.(\d{3}),(\d{2})\b', r'\1\2.\3', text)
text = re.sub(r'(?<![.,\d])(\d+),(\d{2})(?!\d)', r'\1.\2', text)

print("=== Normalized Summary ===")
for line in text.split('\n'):
    if "SUMMARY" in line or "%" in line or "Total" in line:
        print(line)

_summary_row_re = re.compile(r'(?im)^\s*(?:\d{1,3}%?)\s+\S[^\n]*$')
_summary_num_re = re.compile(r'\b([0-9]{1,4}(?:[.,]\d{3})*[.,]\d{2})\b')
_confirmed_summary_total = 0.0   # save for math-validator guard
_confirmed_summary_tax = 0.0     # save for calc_taxes
summary_rows = []
for sm in _summary_row_re.finditer(text):
    print("Match:", sm.group(0))
    raw_nums = []
    for tok in _summary_num_re.findall(sm.group(0)):
        if '.' not in tok and re.search(r',\d{2}$', tok):
            val = float(tok.replace(',', '.'))
        else:
            val = float(tok.replace(',', ''))
        raw_nums.append(val)
    if len(raw_nums) >= 2:
        summary_rows.append(raw_nums)

raw_total = 0
raw_subtotal = 0

if summary_rows:
    best_row = max(summary_rows, key=len)
    price_nums = [n for n in best_row if n >= 50]
    print("price_nums:", price_nums)
    if price_nums:
        summary_grand_total = price_nums[-1]
        summary_tax_val     = price_nums[-2] if len(price_nums) >= 2 else 0
        summary_subtotal    = price_nums[-3] if len(price_nums) >= 3 else 0
        _confirmed_summary_total = summary_grand_total
        print("sg:", summary_grand_total, "st:", summary_tax_val, "ss:", summary_subtotal)
        if raw_total > summary_grand_total * 1.5 or raw_total < summary_grand_total * 0.5:
            raw_total = summary_grand_total
        if raw_subtotal == 0 and summary_subtotal >= summary_grand_total * 0.2:
            raw_subtotal = summary_subtotal
        if summary_tax_val > 0:
            _confirmed_summary_tax = summary_tax_val

print("raw_subtotal:", raw_subtotal)
print("raw_total:", raw_total)
print("_confirmed_summary_tax:", _confirmed_summary_tax)
