#!/usr/bin/env python3
import re

raw = """Invoice
Payment is due within 30 days from date of invoice. Late payment is subject to fees of 5% per month.
Thanks for choosing DEMO - Sliced Invoices  | admin@slicedinvoices.com
Page 1/1From:
DEMO - Sliced Invoices
Suite 5A-1204
123 Somewhere Street
Your City AZ 12345
admin@slicedinvoices.comInvoice Number INV-3337
Order Number 12345
Invoice Date January 25, 2016
Due Date January 31, 2016
Total Due $93.50
To:
Test Business
123 Somewhere St
Melbourne, VIC 3000
test@test.com
Hrs/Qty Service Rate/Price Adjust Sub Total
1.00Web Design
This is a sample description...$85.00 0.00% $85.00
Sub Total $85.00
Tax $8.50
Total $93.50
ANZ Bank
ACC # 1234 1234
BSB # 4321 432Paid"""

_TOTAL_RE = re.compile(
    r'(?i)'
    r'(?<!tax\s)(?<!tax)(?<!vat\s)(?<!vat)(?<!sub)'
    r'(?:grand\s*total|total\s*paid|(?:s)?total\s*amt|total\s*(?:amount|payable|due)?|'
    r'amount\s*(?:due|payable)?|balance\s*(?:due)?|total\s*due|'
    r'jumlah(?:\s*keseluruhan|\s*bayaran)?|amt\s*due|net\s*(?:total|payable)?|gross\s*worth)'
    r'(?!\s*(?:tax|discount|sst|gst|vat|service|charge|excluding|incl))'
    r'[\s.:RM$\-]*(?:[A-Z]{2,4}\s*)?'
    r'(?:(?:[0-9]{1,3}(?:,\d{3})*(?:\.\d{2})|\d+(?:\.\d{2})?)[\s$\-]*)*'
    r'([0-9]{1,3}(?:,\d{3})*(?:\.\d{2})|\d+(?:\.\d{2})?)'
)

_SUBTOTAL_RE = re.compile(
    r'(?i)(?<!adjust\s)(?:sub\s*total|subtotal|merchandise\s*subtotal|amount\s*before\s*tax|'
    r'before\s*(?:gst|sst|tax)|net\s*worth)'
    r'[\s.:RM$\-]*(?:[A-Z]{2,4}\s*)?'
    r'(?:(?:[0-9]{1,3}(?:,\d{3})*(?:\.\d{2})|\d+(?:\.\d{2})?)[\s$\-]*)*'
    r'([0-9]{1,3}(?:,\d{3})*(?:\.\d{2})|\d+(?:\.\d{2})?)'
)

for m in _TOTAL_RE.finditer(raw):
    print("TOTAL:", m.group(0), "->", m.group(1))

for m in _SUBTOTAL_RE.finditer(raw):
    print("SUBTOTAL:", m.group(0), "->", m.group(1))
