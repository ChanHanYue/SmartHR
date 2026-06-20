#!/usr/bin/env python3
"""Trace extraction for test1.jpg OCR output."""
import re

raw = """Invoice no: 51109338

Date of issue: 04/13/2013

Seller: Client:

Andrews, Kirby and Valdez Becker Ltd

58861 Gonzalez Prairie 8012 Stewart Summit Apt. 455
Lake Daniellefurt, IN 57228 North Douglas, AZ 95355

Tax Id: 945-82-2137 Tax Id: 942-80-0517

IBAN: GB75MCRL06841367619257

ITEMS

No. Description Qty UM Net price Net worth VAT [%] Gross

worth

1 each 209,00 627,00 10% 689,70

2. HP T520 Thin Client Computer 5,00 each 37,75 188,75 10% 207,63
AMD GX-212JC 1.2GHz 4GB RAM

TESTED !!READ BELOW!!
3. gaming pe desktop computer 1,00 each 400,00 400,00 10% 440,00
4. 12-Core Gaming Computer 3,00 each 464,89 1 394,67 10% 1534,14

Desktop PC Tower Affordable
GAMING PC 8GB.AMD Vega RGB

1595553) SUMMARY

5, Custom Build Dell Opti 5,00 each 1,109,95 10%
i5-4570 i
Computer PC
6. Dell Optiplex 990 MT Computer 4,00 each 269,95 1.079,80 10% 1:187,78
PC Quad Core i7 3.4GHz 16GB
2TB HD Windows 10 Pro
VAT [%] Net worth VAT Gross worth
10% 5 640,17 6 204,19

Total $5 640,17 $ 564,02 $6 204,19
"""

# ── TEST 1: EU number normalization ─────────────────────────────────────────
def _normalize_eu_numbers(text):
    """Convert EU-format numbers to standard US decimal (period) format.
    Handles: 5 640,17 → 5640.17, 1 394,67 → 1394.67, 207,63 → 207.63
    """
    # 1. space-thousands + comma-decimal: e.g. "5 640,17", "1 394,67"
    text = re.sub(r'\b(\d{1,3})\s(\d{3}),(\d{2})\b', r'\1\2.\3', text)
    # 2. dot-thousands + comma-decimal: e.g. "1.079,80"
    text = re.sub(r'\b(\d{1,3})\.(\d{3}),(\d{2})\b', r'\1\2.\3', text)
    # 3. plain comma-decimal (exactly 2 dp, word boundaries): "207,63", "564,02"
    text = re.sub(r'(?<![.,\d])(\d+),(\d{2})(?!\d)', r'\1.\2', text)
    return text

normalized = _normalize_eu_numbers(raw)
print("=== NORMALIZED TEXT (relevant lines) ===")
for line in normalized.splitlines():
    if any(c.isdigit() for c in line):
        print(f"  {line!r}")

# ── TEST 2: Date fix (MM/DD/YYYY) ────────────────────────────────────────────
def _extract_date_fixed(text):
    _DATE_PATTERNS = [
        re.compile(
            r'(?<![a-z0-9])(\d{1,2})[/\-\s](Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|'
            r'Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|'
            r'Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[/\-\s,]*(\d{4})(?![a-z0-9])',
            re.IGNORECASE
        ),
        re.compile(
            r'(?<![a-z0-9])(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|'
            r'Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|'
            r'Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})[,\s]+(\d{4})(?![a-z0-9])',
            re.IGNORECASE
        ),
        re.compile(r'(?<![a-z0-9])(\d{4})[-/](\d{2})[-/](\d{2})(?![a-z0-9])'),
        re.compile(r'(?<![a-z0-9])(\d{1,2})[-/](\d{1,2})[-/](\d{4})(?![a-z0-9])'),
        re.compile(r'(?<![a-z0-9])(\d{1,2})\.(\d{1,2})\.(\d{4})(?![a-z0-9])'),
    ]
    _MONTH_MAP = {
        'jan':'01','january':'01','feb':'02','february':'02','mar':'03','march':'03',
        'apr':'04','april':'04','may':'05','jun':'06','june':'06','jul':'07','july':'07',
        'aug':'08','august':'08','sep':'09','september':'09','oct':'10','october':'10',
        'nov':'11','november':'11','dec':'12','december':'12',
    }
    candidates = []
    for p in _DATE_PATTERNS:
        for m in p.finditer(text):
            g = m.groups()
            if len(g) == 3:
                g1, g2, g3 = g
                if g1.lower()[:3] in _MONTH_MAP:
                    val = f"{g3}-{_MONTH_MAP[g1.lower()[:3]]}-{g2.zfill(2)}"
                elif g2.lower()[:3] in _MONTH_MAP:
                    val = f"{g3}-{_MONTH_MAP[g2.lower()[:3]]}-{g1.zfill(2)}"
                elif len(g1) == 4:  # YYYY-MM-DD
                    val = f"{g1}-{g2}-{g3}"
                else:
                    # Could be DD/MM/YYYY or MM/DD/YYYY
                    d1, d2 = int(g1), int(g2)
                    if d2 > 12:
                        # g2 can't be month → must be MM/DD/YYYY (g1=month, g2=day)
                        val = f"{g3}-{g1.zfill(2)}-{g2.zfill(2)}"
                    elif d1 > 12:
                        # g1 can't be month → must be DD/MM/YYYY (g1=day, g2=month)
                        val = f"{g3}-{g2.zfill(2)}-{g1.zfill(2)}"
                    else:
                        # Ambiguous: default DD/MM/YYYY
                        val = f"{g3}-{g2.zfill(2)}-{g1.zfill(2)}"
            else:
                continue
            score = 50
            ctx = text[max(0,m.start()-30):m.start()].lower()
            if 'date' in ctx or 'issue' in ctx: score += 30
            candidates.append({'val': val, 'score': score})
    if candidates:
        return sorted(candidates, key=lambda x: x['score'], reverse=True)[0]['val']
    return ''

print("\n=== DATE EXTRACTION ===")
print(f"  '04/13/2013' → {_extract_date_fixed('Date of issue: 04/13/2013')!r}  (expected '2013-04-13')")

# ── TEST 3: Total row last-number extraction ─────────────────────────────────
print("\n=== TOTAL ROW EXTRACTION ===")
_total_row_re = re.compile(r'(?im)^[ \t]*\$?\s*(?:grand\s+)?total\b[^\n]+$')
_amount_re    = re.compile(r'(\d{1,4}(?:,\d{3})*\.\d{2}|\d+\.\d{2})')

for m in _total_row_re.finditer(normalized):
    line = m.group(0)
    nums = [float(n.replace(',','')) for n in _amount_re.findall(line)]
    print(f"  line: {line!r}")
    print(f"  nums: {nums}")
    if nums:
        grand = max(nums)
        subtotal = sorted(nums, reverse=True)[1] if len(nums) >= 2 else 0
        tax = sorted(nums, reverse=True)[2] if len(nums) >= 3 else 0
        print(f"  → grand_total={grand}, subtotal={subtotal}, tax={tax}")
        print(f"  expected: 6204.19, 5640.17, 564.02")
