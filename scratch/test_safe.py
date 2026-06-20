#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import re

raw = """Total Due $93.50
Sub Total $85.00
Tax $8.50
Total $93.50"""

_TOTAL_RE = re.compile(
    r'(?i)'
    r'(?<!tax\s)(?<!tax)(?<!vat\s)(?<!vat)(?<!sub)'
    r'(?:grand\s*total|total\s*paid|(?:s)?total\s*amt|total\s*(?:amount|payable|due)?|'
    r'amount\s*(?:due|payable)?|balance\s*(?:due)?|total\s*due|'
    r'jumlah(?:\s*keseluruhan|\s*bayaran)?|amt\s*due|net\s*(?:total|payable)?|gross\s*worth)'
    r'(?!\s*(?:tax|discount|sst|gst|vat|service|charge|excluding|incl))'
    r'[\s.:RM$\-]*(?:[A-Z]{2,4}\s*)?'
    r'([0-9]{1,3}(?:,\d{3})*(?:\.\d{2})|\d+(?:\.\d{2})?)'
)

_SUBTOTAL_RE = re.compile(
    r'(?i)(?<!adjust\s)(?:sub\s*total|subtotal|merchandise\s*subtotal|amount\s*before\s*tax|'
    r'before\s*(?:gst|sst|tax)|net\s*worth)'
    r'[\s.:RM$\-]*(?:[A-Z]{2,4}\s*)?'
    r'([0-9]{1,3}(?:,\d{3})*(?:\.\d{2})|\d+(?:\.\d{2})?)'
)

for m in _TOTAL_RE.finditer(raw):
    print("TOTAL:", m.group(0), "->", m.group(1))

for m in _SUBTOTAL_RE.finditer(raw):
    print("SUBTOTAL:", m.group(0), "->", m.group(1))
