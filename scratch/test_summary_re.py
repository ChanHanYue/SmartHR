#!/usr/bin/env python3
import re

raw = """1595553) SUMMARY
VAT [%] Net worth VAT Gross worth
10% 5640.17 564.02 6204.19
Total $5640.17 $ 564.02 $6204.19"""

_summary_row_re = re.compile(r'(?im)^\s*(?:\d{1,3}%?)\s+\S[^\n]*$')
_summary_num_re = re.compile(r'\b([0-9]{1,4}(?:[.,]\d{3})*[.,]\d{2})\b')

summary_rows = []
for sm in _summary_row_re.finditer(raw):
    raw_nums = []
    for tok in _summary_num_re.findall(sm.group(0)):
        if '.' not in tok and re.search(r',\d{2}$', tok):
            val = float(tok.replace(',', '.'))
        else:
            val = float(tok.replace(',', ''))
        raw_nums.append(val)
    if len(raw_nums) >= 2:
        summary_rows.append(raw_nums)
        print(f"  summary row parsed: {raw_nums}")

if summary_rows:
    best_row = max(summary_rows, key=len)
    price_nums = [n for n in best_row if n >= 50]
    print(f"  price_nums (>=50): {price_nums}")
    if price_nums:
        sg = price_nums[-1]
        st = price_nums[-2] if len(price_nums) >= 2 else 0
        ss = price_nums[-3] if len(price_nums) >= 3 else 0
        print(f"GRAND: {sg}, TAX: {st}, SUB: {ss}")
