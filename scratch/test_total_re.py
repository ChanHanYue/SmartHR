#!/usr/bin/env python3
import re

raw = """1595553) SUMMARY
VAT [%] Net worth VAT Gross worth
10% 5640.17 564.02 6204.19
Total $5640.17 $ 564.02 $6204.19"""

_TOTAL_RE = re.compile(
    r'(?i)'
    r'(?<!tax\s)(?<!tax)(?<!vat\s)(?<!vat)(?<!sub)'
    r'(?:grand\s*total|total\s*paid|(?:s)?total\s*amt|total\s*(?:amount|payable|due)?|'
    r'amount\s*(?:due|payable)?|balance\s*(?:due)?|total\s*due|'
    r'jumlah(?:\s*keseluruhan|\s*bayaran)?|amt\s*due|net\s*(?:total|payable)?|gross\s*worth)'
    r'(?!\s*(?:tax|discount|sst|gst|vat|service|charge|excluding|incl))'
    r'[\s.:RM$\-]*(?:[A-Z]{2,4}\s*)?'
    # Greedily match any numbers and whitespace/symbols up to the LAST number
    r'(?:(?:[0-9]{1,3}(?:,\d{3})*(?:\.\d{2})|\d+(?:\.\d{2})?)[\s$\-]*)*'
    r'([0-9]{1,3}(?:,\d{3})*(?:\.\d{2})|\d+(?:\.\d{2})?)'
)

for m in _TOTAL_RE.finditer(raw):
    print("TOTAL MATCH:", m.group(0), "->", m.group(1))

_SUBTOTAL_RE = re.compile(
    r'(?i)(?<!adjust\s)(?:sub\s*total|subtotal|merchandise\s*subtotal|amount\s*before\s*tax|'
    r'before\s*(?:gst|sst|tax)|net\s*worth)'
    r'[\s.:RM$\-]*(?:[A-Z]{2,4}\s*)?'
    r'(?:(?:[0-9]{1,3}(?:,\d{3})*(?:\.\d{2})|\d+(?:\.\d{2})?)[\s$\-]*)*'
    r'([0-9]{1,3}(?:,\d{3})*(?:\.\d{2})|\d+(?:\.\d{2})?)'
)
for m in _SUBTOTAL_RE.finditer(raw):
    print("SUBTOTAL MATCH:", m.group(0), "->", m.group(1))
