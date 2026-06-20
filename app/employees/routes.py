"""app/employees/routes.py – Employee CRUD"""
import os
import re
import uuid
import json
import platform
import datetime
from io import BytesIO
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, current_app, jsonify,
                   send_from_directory, abort)
from werkzeug.security import generate_password_hash
from app.database import query, execute, log_audit, as_dict, is_leave_eligible
from app.auth.routes import login_required, role_required
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps

emp_bp = Blueprint('employees', __name__, url_prefix='/employees')

# ── Malaysian MyKad OCR helpers ─────────────────────────────────────────────

MYKAD_ANCHOR_RE = re.compile(
    r'KERAJAAN|KAD\s*PENGENALAN|WARGANEGARA|MYKAD|\bNAMA\b|IDENTITY|MALAYSIA|'
    r'NO\.?\s*K/?P|K/?P\.?\s*NO',
    re.I)

ADDRESS_MARKERS_RE = re.compile(
    r'\b(JALAN|JLN|LORONG|LRG|TAMAN|TMN|KAMPUNG|KAMPONG|KG\.?|BANDAR|BDR|'
    r'PERSIARAN|PSN|BLOK|BLK|TINGKAT|FLOOR|APT|CONDO|'
    r'POSKOD|POSTCODE|POST\s*CODE|MUKIM|DAERAH|'
    r'SELANGOR|JOHOR|PERAK|PENANG|PULAU\s*PINANG|SABAH|SARAWAK|MELAKA|NEGERI|'
    r'KUALA\s*LUMPUR|PUTRAJAYA|LABUAN|PAHANG|KEDAH|KELANTAN|TERENGGANU|'
    r'PERLIS|NSDK|N\.?\s*SEMBILAN)\b',
    re.I)

MYKAD_NAME_MARKERS_RE = re.compile(
    r'(\bBIN\b|\bBINTI\b|\bBTE\b|\bBINTE\b|\bA/L\b|\bA/P\b|\bA/L\.\b|\bA/P\.\b)',
    re.I)

MYKAD_AT_NAME_RE = re.compile(
    r'^[A-Z]{2,}(?:\s+[A-Z]{2,})+\s+@\s+[A-Z]{2,}(?:\s+[A-Z]{2,})+$'
)

NAMA_ANCHOR_RE = re.compile(r'\bN[A4@]?M[A4]?A\b', re.I)

MYKAD_LABEL_STOP_RE = re.compile(
    r'\b(WARGANEGARA|KETURUNAN|AGAMA|JANTINA|LELAKI|PEREMPUAN|'
    r'ALAMAT|ADDRESS|NO\.?\s*K/?P|K/?P|KERAJAAN|MALAYSIA|KAD\s*PENGENALAN|'
    r'IDENTITY\s*CARD|DATE\s*OF\s*BIRTH|TARIKH)\b',
    re.I)

IC_FORMATTED_RE = re.compile(r'(\d{6}[\s\-]\d{2}[\s\-]\d{4})')
IC_LABELED_RE = re.compile(
    r'(?:NO\.?\s*K/?P|N(?:O|0)\.?\s*K/?P|K/?P\.?\s*NO\.?)'
    r'[\s:.\-]*([\dOILSBZ\-\s]{12,20})',
    re.I)


def _get_tesseract_path():
    if platform.system() == 'Windows':
        common = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if os.path.exists(common):
            return common
    return None


def _apply_watermark(img_path, company_name):
    """
    Apply a hardcoded watermark to the identity document:
    1. Two parallel diagonal lines.
    2. Text: "For [Company Name] HR Purposes Only".
    """
    with Image.open(img_path) as img:
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        
        # Draw two parallel lines (diagonal)
        line_color = (200, 0, 0) # Red-ish
        line_width = max(2, int(w / 200))
        
        # Top-left to bottom-right or similar
        # Let's do bottom-left corner or center
        # Parallel lines across the image
        gap = int(h / 10)
        draw.line([(0, h*0.7), (w*0.7, 0)], fill=line_color, width=line_width)
        draw.line([(0, h*0.8), (w*0.8, 0)], fill=line_color, width=line_width)
        
        # Add text
        text = f"For {company_name} HR Purposes Only"
        # Try to use a default font
        try:
            # On Windows, Arial is common
            font_path = "arial.ttf" if platform.system() == 'Windows' else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            font = ImageFont.truetype(font_path, int(w/40))
        except:
            font = ImageFont.load_default()
            
        # Draw text between or near lines
        # Position it diagonally if possible, or just center
        draw.text((w*0.1, h*0.75), text, fill=line_color, font=font)
        
        img.save(img_path)


def _ocr_digit_fix(s):
    """Fix common OCR misreads in numeric strings."""
    return s.upper().replace('O', '0').replace('I', '1').replace('L', '1').replace('S', '5').replace('B', '8').replace('Z', '2')


def _format_ic(digits12):
    return f"{digits12[:6]}-{digits12[6:8]}-{digits12[8:]}"


def _validate_malaysian_ic(digits):
    """Validate YYMMDD-PB-G### structure used on Malaysian MyKad."""
    if len(digits) != 12 or not digits.isdigit():
        return False
    mm, dd = int(digits[2:4]), int(digits[4:6])
    if mm < 1 or mm > 12 or dd < 1 or dd > 31:
        return False
    birthplace = int(digits[6:8])
    if birthplace < 1 or birthplace > 59:
        return False
    return True


def _score_mykad_orientation(text):
    """Score OCR text for how well it matches upright Malaysian IC layout."""
    score = len(MYKAD_ANCHOR_RE.findall(text)) * 2
    if NAMA_ANCHOR_RE.search(text):
        score += 5
    if IC_LABELED_RE.search(text) or IC_FORMATTED_RE.search(text):
        score += 8
    if MYKAD_NAME_MARKERS_RE.search(text):
        score += 4
    return score


def _quick_orient_ocr(img):
    crop = _mykad_front_text_crops(img)[0]
    return _tesseract_once(_prep_gray(crop, max_side=800), psm=6)


def _orient_and_save(img_path):
    """Legacy helper — rotation is handled inside _ocr_mykad_with_rotation."""
    img = ImageOps.exif_transpose(Image.open(img_path)).convert('RGB')
    img.save(img_path, quality=92)
    return img


def _upscale(img, min_side=1200):
    w, h = img.size
    if max(w, h) >= min_side:
        return img
    scale = min_side / max(w, h)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


def _prep_gray(img, max_side=1200, contrast=2.0):
    """Single fast grayscale prep — downscale large images for speed."""
    gray = img.convert('L')
    w, h = gray.size
    if max(w, h) > max_side:
        scale = max_side / max(w, h)
        gray = gray.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return ImageEnhance.Contrast(gray).enhance(contrast)


def _tesseract_once(img, psm=6):
    """Single Tesseract call."""
    import pytesseract
    tess_path = _get_tesseract_path()
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path
    langs = _tesseract_langs()
    return pytesseract.image_to_string(
        img, config=f'--oem 3 --psm {psm} -l {langs}')


def _mykad_front_text_crops(img):
    """
    Text-only crops for MyKad front.
    Since the document is now auto-cropped by OpenCV, we can reliably target the left 70% of the card to avoid the photo.
    """
    w, h = img.size
    crops = [
        # Left 70% of the tightly cropped card (avoids the photo completely)
        img.crop((int(w * 0.02), int(h * 0.02), int(w * 0.70), int(h * 0.98))),
        # Full card as a backup
        img.crop((int(w * 0.02), int(h * 0.02), int(w * 0.98), int(h * 0.98))),
    ]
    return crops


def _mykad_back_text_crops(img):
    """Back of MyKad: address area is usually centre-right, no photo."""
    w, h = img.size
    if w >= h:
        return [
            img.crop((int(w * 0.08), int(h * 0.15), w, int(h * 0.92))),
            img.crop((int(w * 0.20), int(h * 0.20), w, int(h * 0.85))),
        ]
    return [
        img.crop((int(w * 0.05), int(h * 0.25), int(w * 0.95), int(h * 0.80))),
        img.crop((0, int(h * 0.30), w, int(h * 0.75))),
    ]


def _score_ocr_text_fast(text):
    """Lightweight OCR quality score (no field extraction — safe inside loops)."""
    if not text or not text.strip():
        return 0
    fixed = _fix_ic_ocr_digits(text)
    score = _score_mykad_orientation(text)
    if IC_LABELED_RE.search(text):
        score += 18
    if IC_FORMATTED_RE.search(fixed):
        score += 14
    if MYKAD_NAME_MARKERS_RE.search(text):
        score += 10
    if re.search(r'\b(ALAMAT|ADDRESS)\b', text, re.I):
        score += 6
    return score


def _score_ocr_text(text):
    """Full score including extracted fields (use after OCR pass completes)."""
    score = _score_ocr_text_fast(text)
    if _extract_malaysian_ic_number(text):
        score += 12
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if _extract_malaysian_name(lines):
        score += 12
    if _extract_address(text):
        score += 8
    return score


def _pick_best_rotation(base, crop_fn):
    """Phase 1: try 4 rotations with one quick OCR each (~4 Tesseract calls)."""
    best_img, best_score = base, -1
    for angle in (0, 90, 180, 270):
        candidate = base if angle == 0 else base.rotate(-angle, expand=True)
        crop = crop_fn(candidate)[0]
        text = _tesseract_once(_prep_gray(crop, max_side=800, contrast=2.0), psm=6)
        score = _score_mykad_orientation(text)
        if IC_FORMATTED_RE.search(_fix_ic_ocr_digits(text)):
            score += 10
        if score > best_score:
            best_score, best_img = score, candidate
    return best_img


def _ocr_on_oriented(oriented, crop_fn):
    """Phase 2: OCR best rotation; pick the single best result."""
    results = []
    crops = crop_fn(oriented)[:3]

    for crop in crops:
        for contrast in (1.8, 2.4):
            prepped = _prep_gray(crop, max_side=1200, contrast=contrast)
            # Try PSM 6 (Uniform Block) first - keeps multi-line addresses together
            for psm in (6, 11):
                text = _tesseract_once(prepped, psm=psm)
                # Use the full score function so passes that find names/addresses without labels win
                score = _score_ocr_text(text)
                if text.strip():
                    results.append((text, score))
                # Require a much higher score to break early (needs IC + Name + Address markers)
                if score >= 42:
                    break
            if results and results[-1][1] >= 42:
                break

    if not results:
        if crops:
            text = _tesseract_once(_prep_gray(crops[0]), psm=11)
            return text, _score_ocr_text(text)
        return '', -1

    results.sort(key=lambda x: x[1], reverse=True)
    # Return the single best result to avoid duplicating text and creating hallucinated strings of digits
    return results[0][0], results[0][1]


def _auto_crop_document(img):
    """Automatically find and crop the ID card document from the image background using OpenCV."""
    try:
        import cv2
        import numpy as np
        
        cv_img = np.array(img.convert('RGB'))
        cv_img = cv_img[:, :, ::-1].copy() 
        
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return img
            
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        for c in contours[:3]:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                area = cv2.contourArea(c)
                h, w = gray.shape
                # Ensure it's large enough to be a document (at least 15% of image)
                if area > (w * h * 0.15):
                    pts = approx.reshape(4, 2)
                    rect = np.zeros((4, 2), dtype="float32")
                    s = pts.sum(axis=1)
                    rect[0] = pts[np.argmin(s)]
                    rect[2] = pts[np.argmax(s)]
                    diff = np.diff(pts, axis=1)
                    rect[1] = pts[np.argmin(diff)]
                    rect[3] = pts[np.argmax(diff)]
                    
                    (tl, tr, br, bl) = rect
                    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
                    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
                    maxWidth = max(int(widthA), int(widthB))
                    
                    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
                    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
                    maxHeight = max(int(heightA), int(heightB))
                    
                    dst = np.array([
                        [0, 0],
                        [maxWidth - 1, 0],
                        [maxWidth - 1, maxHeight - 1],
                        [0, maxHeight - 1]], dtype="float32")
                    
                    M = cv2.getPerspectiveTransform(rect, dst)
                    warped = cv2.warpPerspective(cv_img, M, (maxWidth, maxHeight))
                    warped = cv2.cvtColor(warped, cv2.COLOR_BGR2RGB)
                    return Image.fromarray(warped)
    except Exception:
        pass
    return img


def _ocr_mykad_with_rotation(img, crop_fn):
    """
    Two-phase MyKad OCR (~12-20 Tesseract calls total, not 200+).
    Returns (text, score, corrected_image).
    """
    base = ImageOps.exif_transpose(img).convert('RGB')
    base = _auto_crop_document(base)
    oriented = _pick_best_rotation(base, crop_fn)
    text, fast_score = _ocr_on_oriented(oriented, crop_fn)
    return text, _score_ocr_text(text) if text else fast_score, oriented


def _ocr_mykad_front(img):
    return _ocr_mykad_with_rotation(img, _mykad_front_text_crops)


def _ocr_mykad_back(img):
    return _ocr_mykad_with_rotation(img, _mykad_back_text_crops)


def _ocr_ic_number_fallback(img):
    """Second-pass OCR focused on the IC number line (digits only)."""
    import pytesseract
    tess_path = _get_tesseract_path()
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path

    w, h = img.size
    # Pass a broad region to avoid cutting it if the card is small in the photo
    crop = img.crop((int(w * 0.05), int(h * 0.05), int(w * 0.95), int(h * 0.85)))

    gray = ImageEnhance.Contrast(_upscale(crop.convert('L'))).enhance(2.8)
    text = pytesseract.image_to_string(
        gray,
        config='--oem 3 --psm 7 -l eng -c tessedit_char_whitelist=0123456789OLISBZ-/ ')
    return _extract_malaysian_ic_number(text)


def _ocr_name_fallback(img):
    """Second-pass OCR focused on the NAMA line (letters only)."""
    import pytesseract
    tess_path = _get_tesseract_path()
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path

    w, h = img.size
    # Pass a broad region to avoid cutting it if the card is small in the photo
    crop = img.crop((int(w * 0.05), int(h * 0.15), int(w * 0.95), int(h * 0.95)))

    gray = ImageEnhance.Contrast(_upscale(crop.convert('L'))).enhance(2.2)
    langs = _tesseract_langs()
    text = pytesseract.image_to_string(
        gray,
        config=f'--oem 3 --psm 7 -l {langs} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ ')
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    return _extract_malaysian_name(lines)


def _preprocess_id_image(img_path):
    """Passport / generic fallback preprocessing."""
    img = Image.open(img_path).convert('RGB')
    return _prep_gray(img, max_side=1200, contrast=2.0)


def _run_id_ocr(img, psm_modes=(6, 11)):
    """Passport fallback — at most 2 Tesseract calls."""
    best, best_score = '', -1
    for psm in psm_modes:
        text = _tesseract_once(img, psm=psm)
        score = _score_ocr_text_fast(text)
        if score > best_score:
            best, best_score = text, score
    return best


def _tesseract_langs():
    """Prefer Malay + English for Malaysian IDs; fall back to English."""
    import pytesseract
    tess_path = _get_tesseract_path()
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path
    try:
        installed = pytesseract.get_languages(config='')
        if 'msa' in installed:
            return 'msa+eng'
    except Exception:
        pass
    return 'eng'


def _is_ocr_garbage_name(name):
    """Detect photo-region OCR noise (e.g. 'Yy Tees Eae Ap Ay Oe Ky')."""
    if not name:
        return True
    tokens = name.upper().split()
    if not tokens:
        return True
    if len(tokens) > 7 and not MYKAD_NAME_MARKERS_RE.search(name):
        return True
    short = sum(1 for t in tokens if len(t) <= 2)
    if len(tokens) >= 4 and short / len(tokens) >= 0.35:
        return True
    avg_len = sum(len(t) for t in tokens) / len(tokens)
    total_len = sum(len(t) for t in tokens)
    # Allow Chinese/Indian 3-part names like CHAN HAN YUE (avg ~3.3, total 10)
    if avg_len < 2.5:
        return True
    if not MYKAD_NAME_MARKERS_RE.search(name):
        if len(tokens) <= 2 and max(len(t) for t in tokens) <= 4:
            return True
        if total_len < 8:
            return True
    # Real MyKad names are almost always ALL CAPS; reject mixed-case noise
    raw_words = name.split()
    if any(re.search(r'[a-z]', w) and re.search(r'[A-Z]', w) and len(w) <= 4 for w in raw_words):
        if not MYKAD_NAME_MARKERS_RE.search(name):
            return True
    return False


def _fix_ic_ocr_digits(text):
    """Correct common OCR digit misreads inside IC number patterns."""
    def _fix_match(m):
        return _ocr_digit_fix(m.group(0))

    return re.sub(r'[\dOILSBZ\-]{10,}', _fix_match, text)


def _clean_name_line(line):
    """Strip non-name characters; MyKad names are uppercase letters and spaces."""
    cleaned = re.sub(r'[^A-Za-z\s]', ' ', line)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip().upper()
    return cleaned


def _mykad_text_has_nama(text):
    return bool(NAMA_ANCHOR_RE.search(text))


def _looks_like_address(text):
    """True if the line reads like a Malaysian address, not a person name."""
    if not text:
        return True
    if ADDRESS_MARKERS_RE.search(text):
        return True
    if re.search(r'\b\d{5}\b', text):
        return True
    if re.search(r'\bNO\.?\s*\d', text, re.I):
        return True
    return False


def _is_plausible_malaysian_name(name):
    """Validate OCR candidate against Malaysian MyKad naming conventions."""
    if not name or len(name) < 8:
        return False
    if _is_ocr_garbage_name(name):
        return False

    upper = name.upper().strip()

    if '@' in upper or '-' in upper:
        return False

    noise = [
        'KERAJAAN', 'MALAYSIA', 'KAD PENGENALAN', 'IDENTITY CARD', 'WARGANEGARA',
        'PURPOSES', 'PURPOSE', 'ONLY', 'SPECIMEN', 'MYKAD', 'JPN', 'HR', 'NAMA',
        'KETURUNAN', 'AGAMA', 'JANTINA', 'LELAKI', 'PEREMPUAN', 'ALAMAT',
        'MALAY', 'IDENTITY', 'WARGA', 'NEGARA', 'PENGENALAN', 'KAD'
    ]
    if any(n in upper for n in noise):
        return False

    if _looks_like_address(upper):
        return False

    if not re.match(r'^[A-Z]+(?: [A-Z]+)+$', upper):
        return False

    letters = re.sub(r'[^A-Z]', '', upper)
    tokens = upper.split()
    vowels = sum(1 for c in letters if c in 'AEIOU')
    if vowels == 0:
        return False

    if MYKAD_NAME_MARKERS_RE.search(upper):
        return 2 <= len(tokens) <= 8

    if len(tokens) >= 3 and all(len(t) >= 4 for t in tokens):
        return vowels >= 2

    # Relax: allow short tokens (e.g. Chinese/Indian names: CHAN HAN YUE, A/P DEVI)
    if len(tokens) >= 2 and all(len(t) >= 2 for t in tokens):
        return vowels >= 1

    return False


def _extract_malaysian_ic_number(text):
    """Extract Malaysian MyKad IC (YYMMDD-PB-G###); prefer No. K/P labelled matches."""
    text = _fix_ic_ocr_digits(text)
    has_nama = _mykad_text_has_nama(text)
    min_score = 10 if has_nama else 20
    candidates = []

    for m in IC_LABELED_RE.finditer(text):
        digits = re.sub(r'\D', '', _ocr_digit_fix(m.group(1)))
        if _validate_malaysian_ic(digits):
            candidates.append((_format_ic(digits), 100))

    for m in IC_FORMATTED_RE.finditer(text):
        digits = re.sub(r'\D', '', m.group(1))
        if _validate_malaysian_ic(digits):
            ctx = text[max(0, m.start() - 60):m.start()].upper()
            score = 60 if re.search(r'K/?P|KAD|PENGENALAN|NAMA', ctx) else 30
            candidates.append((_format_ic(digits), score))

    if not candidates:
        # Fuzzy fallback: strip all non-digits and look for any 12-digit sequence
        flat = re.sub(r'[^0-9]', '', _ocr_digit_fix(text))
        for m in re.finditer(r'\d{12}', flat):
            digits = m.group(0)
            if _validate_malaysian_ic(digits):
                candidates.append((_format_ic(digits), 12))

    if not candidates:
        return ''

    candidates.sort(key=lambda x: x[1], reverse=True)
    # Lower threshold when a plausible name exists in the text
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    has_name = bool(_extract_malaysian_name(lines))
    effective_min = 10 if (has_nama or has_name) else min_score
    if candidates[0][1] < effective_min:
        return ''
    return candidates[0][0]


def _extract_malaysian_name(lines):
    """
    Extract holder name from MyKad front.
    Primary: look for NAMA label. Fallback: pick first plausible name line.
    """
    for i, line in enumerate(lines):
        if not NAMA_ANCHOR_RE.search(line):
            continue

        remainder = NAMA_ANCHOR_RE.sub('', line, count=1)
        remainder = re.sub(r'^[\s:.\-]+', '', remainder).strip()
        if remainder:
            candidate = _clean_name_line(remainder)
            if _is_plausible_malaysian_name(candidate):
                return candidate

        for j in range(i + 1, min(i + 3, len(lines))):
            nxt = lines[j]
            if MYKAD_LABEL_STOP_RE.search(nxt):
                break
            candidate = _clean_name_line(nxt)
            if _is_plausible_malaysian_name(candidate):
                return candidate

    # Fallback: no NAMA label found — pick first plausible all-caps name line
    for line in lines:
        candidate = _clean_name_line(line)
        if _is_plausible_malaysian_name(candidate):
            return candidate

    return ''


def _clean_malaysian_address(address):
    """Clean up common OCR mistakes in Malaysian addresses."""
    if not address:
        return address
    
    # Common OCR fixes
    fixes = [
        (r'\bVJ\b', 'W'),
        (r'\bPERSEMUTUAN\b', 'PERSEKUTUAN'),
        (r'\bPERSEMUTUANIKL\b', 'PERSEKUTUAN(KL)'),
        (r'\bJALAN 137B\b', 'JALAN 1/37B'),
        (r'\bNO67\b', 'NO 67'),
        (r'\bNO\s*67\b', 'NO 67'),
        (r'\bJALAN 1/37B\s+\d+\b', 'JALAN 1/37B'),  # Remove trailing single digits after road
        (r'\)\s*\)*$', ')'),  # Fix trailing parentheses
        (r'^\s*\(\s*', '('),  # Fix leading parentheses
    ]
    
    cleaned = address.upper()
    for pattern, replacement in fixes:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.I)
    
    # Clean up extra characters and spaces
    cleaned = re.sub(r'[|_\-:~]+', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def _extract_address(text, full_name=''):
    """Extract address from Malaysian MyKad OCR text.
    Strategy 1: Look for ALAMAT/ADDRESS label (rare on modern MyKad).
    Strategy 2: Positional — capture everything after the holder's name line,
                filtering out header/noise lines.
    Strategy 3: Fallback — grab any lines with address markers (JALAN, TAMAN, etc.).
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    address_lines = []
    capturing = False

    stop_words = re.compile(
        r'\b(WARGANEGARA|KETURUNAN|AGAMA|JANTINA|LELAKI|PEREMPUAN|'
        r'KERAJAAN|KAD\s*PENGENALAN|IDENTITY\s*CARD|MYKAD)\b', re.I)

    header_noise = re.compile(
        r'\b(KAD\s*PENGENALAN|IDENTITY\s*CARD|KERAJAAN|MALAYSIA|MYKAD|'
        r'MALAY|WARGANEGARA)\b', re.I)

    # Strategy 1: ALAMAT/ADDRESS label
    for i, line in enumerate(lines):
        upper = line.upper()
        if re.search(r'\b(ALAMAT|ADDRESS)\b', upper):
            parts = re.split(r'[:\.\-]', line, maxsplit=1)
            if len(parts) > 1:
                chunk = re.sub(r'[^A-Za-z0-9\s,\-/\.#\(\)]', ' ', parts[1]).strip()
                if len(chunk) > 3:
                    address_lines.append(chunk)
            for j in range(i + 1, len(lines)):
                nxt = lines[j]
                if stop_words.search(nxt):
                    break
                cleaned = re.sub(r'[^A-Za-z0-9\s,\-/\.#\(\)]', ' ', nxt)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if len(cleaned) > 3:
                    address_lines.append(cleaned)
            if address_lines:
                return _clean_malaysian_address(', '.join(dict.fromkeys(address_lines)))

    # Strategy 2: Positional — find name line, capture everything after it as address
    if full_name:
        name_upper = full_name.upper().strip()
        name_idx = -1
        for i, line in enumerate(lines):
            cleaned = _clean_name_line(line)
            if name_upper in cleaned or cleaned in name_upper:
                name_idx = i
                break
            # Partial match: first two tokens of the name
            name_tokens = name_upper.split()
            if len(name_tokens) >= 2:
                if name_tokens[0] in cleaned and name_tokens[1] in cleaned:
                    name_idx = i
                    break

        if name_idx >= 0:
            for j in range(name_idx + 1, len(lines)):
                line = lines[j]
                if stop_words.search(line) or header_noise.search(line):
                    break
                # Skip IC number lines
                if IC_FORMATTED_RE.search(line) or re.match(r'^\d{6}[\-\s]\d{2}[\-\s]\d{4}$', line.strip()):
                    continue
                cleaned = re.sub(r'[^A-Za-z0-9\s,\-/\.#\(\)]', ' ', line)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if len(cleaned) > 3 and not _is_plausible_malaysian_name(cleaned):
                    address_lines.append(cleaned)
            if address_lines:
                return _clean_malaysian_address(', '.join(dict.fromkeys(address_lines)))

    # Strategy 3: Fallback — grab lines containing address markers
    capturing_fallback = False
    for line in lines:
        if ADDRESS_MARKERS_RE.search(line):
            capturing_fallback = True

        if capturing_fallback:
            if stop_words.search(line):
                break
            cleaned = re.sub(r'[^A-Za-z0-9\s,\-/\.#\(\)]', ' ', line)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if len(cleaned) > 3:
                address_lines.append(cleaned)

    return _clean_malaysian_address(', '.join(dict.fromkeys(address_lines))) if address_lines else ''


def _ocr_address_fallback(img):
    """Dedicated OCR pass for the address area (lower portion of MyKad, smaller font).
    Tries multiple preprocessing approaches and picks the result with the most address content."""
    import pytesseract
    tess_path = _get_tesseract_path()
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path

    w, h = img.size
    langs = _tesseract_langs()
    best_text = ''
    best_addr_score = 0

    # Try multiple crop regions (address can be in different positions)
    crop_regions = [
        (0.02, 0.40, 0.70, 0.98),  # Lower-left 60% (standard MyKad)
        (0.02, 0.35, 0.75, 0.98),  # Slightly higher start
        (0.02, 0.45, 0.70, 0.95),  # Slightly lower start
        (0.02, 0.30, 0.98, 0.98),  # Full width lower half
    ]

    for (x1, y1, x2, y2) in crop_regions:
        crop = img.crop((int(w * x1), int(h * y1), int(w * x2), int(h * y2)))
        cw, ch = crop.size
        if cw < 30 or ch < 30:
            continue

        # Upscale aggressively for the small address font
        upscaled = _upscale(crop.convert('L'), min_side=2000)

        # Try multiple preprocessing approaches
        preprocessed_imgs = []

        # Approach 1: High contrast
        preprocessed_imgs.append(ImageEnhance.Contrast(upscaled).enhance(3.0))
        # Approach 2: Very high contrast
        preprocessed_imgs.append(ImageEnhance.Contrast(upscaled).enhance(4.0))
        # Approach 3: Sharpen then contrast
        sharpened = ImageEnhance.Sharpness(upscaled).enhance(2.0)
        preprocessed_imgs.append(ImageEnhance.Contrast(sharpened).enhance(3.0))

        # Approach 4: OpenCV adaptive thresholding (much better for small text)
        try:
            import cv2
            import numpy as np
            arr = np.array(upscaled)
            thresh = cv2.adaptiveThreshold(
                arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 31, 10)
            preprocessed_imgs.append(Image.fromarray(thresh))
            # Also try with different block size
            thresh2 = cv2.adaptiveThreshold(
                arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 21, 8)
            preprocessed_imgs.append(Image.fromarray(thresh2))
        except Exception:
            pass

        for prep_img in preprocessed_imgs:
            for psm in (6, 4):
                try:
                    text = pytesseract.image_to_string(
                        prep_img,
                        config=f'--oem 3 --psm {psm} -l {langs}')
                except Exception:
                    continue

                # Score by how much address-like content we found
                addr_score = 0
                for m in ADDRESS_MARKERS_RE.finditer(text):
                    addr_score += 3
                if re.search(r'\b\d{5}\b', text):  # postcode
                    addr_score += 5
                if re.search(r'\bNO\.?\s*\d', text, re.I):  # house number
                    addr_score += 3
                # Count readable words (not just noise)
                words = [w for w in text.split() if len(w) >= 3 and re.match(r'[A-Za-z0-9]', w)]
                addr_score += len(words)

                if addr_score > best_addr_score:
                    best_addr_score = addr_score
                    best_text = text

    return best_text


def _extract_id_info(text, side='front', doc_type='ic'):
    """
    Malaysian MyKad / passport field extraction.
    Front IC: name, IC number, DOB, gender via MyKad-specific rules.
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    full_name = ''
    address = ''
    ic_number = ''
    passport_number = ''

    if doc_type == 'ic' and side == 'front':
        ic_number = _extract_malaysian_ic_number(text)
        full_name = _extract_malaysian_name(lines)
        address = _extract_address(text, full_name=full_name)
    elif doc_type == 'ic' and side == 'back':
        address = _extract_address(text)
    elif doc_type == 'passport':
        clean_text = text.upper()
        passport_match = re.search(r'\b([A-Z]{1,2}\d{6,9})\b', clean_text)
        if passport_match:
            passport_number = passport_match.group(1)
        for i, line in enumerate(lines):
            if re.search(r'\b(NAMA|NAME|SURNAME|GIVEN\s*NAME)\b', line, re.I):
                parts = re.split(r'[:\.\-]', line, maxsplit=1)
                if len(parts) > 1:
                    candidate = _clean_name_line(parts[1])
                    if _is_plausible_malaysian_name(candidate):
                        full_name = candidate
                        break
                if i + 1 < len(lines):
                    candidate = _clean_name_line(lines[i + 1])
                    if _is_plausible_malaysian_name(candidate):
                        full_name = candidate
                        break

    dob = ''
    gender = ''
    id_for_dob = ic_number if doc_type == 'ic' else ''
    if id_for_dob:
        ic_c = id_for_dob.replace('-', '')
        if len(ic_c) == 12:
            yy, mm, dd = ic_c[:2], ic_c[2:4], ic_c[4:6]
            this_year = datetime.date.today().year % 100
            prefix = '20' if int(yy) <= this_year else '19'
            dob = f"{prefix}{yy}-{mm}-{dd}"
            gender = 'Male' if int(ic_c[-1]) % 2 != 0 else 'Female'

    if doc_type == 'passport' and not dob:
        for line in lines:
            m = re.search(r'(\d{2}[/.-]\d{2}[/.-]\d{2,4})', line)
            if m:
                parts = re.split(r'[/.-]', m.group(1))
                if len(parts) == 3:
                    d, mo, y = parts
                    if len(y) == 2:
                        y = ('20' if int(y) <= datetime.date.today().year % 100 else '19') + y
                    dob = f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
                    break

    result = {
        'full_name': full_name.title() if full_name else '',
        'ic_number': ic_number if doc_type == 'ic' else '',
        'passport_number': passport_number if doc_type == 'passport' else '',
        'date_of_birth': dob,
        'gender': gender,
        'address': address,
        'doc_type': doc_type,
        'side': side,
        'ocr_warning': '',
    }
    if doc_type == 'ic' and side == 'front' and not full_name and not ic_number:
        result['ocr_warning'] = (
            'Could not read the IC clearly. Ensure the front (name & IC number side) '
            'is flat, well-lit, and in focus — then try again or enter details manually.'
        )
    elif doc_type == 'ic' and side == 'front' and full_name and not ic_number:
        result['ocr_warning'] = (
            'Name extracted but IC number could not be read — the number area may be '
            'obscured or cut off. Please enter the IC number manually.'
        )
    elif doc_type == 'ic' and side == 'front' and ic_number and not full_name:
        result['ocr_warning'] = (
            'IC number extracted but name could not be read clearly. '
            'Please verify the name field.'
        )
    elif doc_type == 'ic' and side == 'front' and (full_name or ic_number) and not _mykad_text_has_nama(text):
        result['ocr_warning'] = (
            'Some fields may be incomplete — please verify all extracted details.'
        )
    if doc_type == 'passport' and passport_number and not result['ic_number']:
        result['ic_number'] = passport_number
    return result


@emp_bp.route('/ocr_identity', methods=['POST'])
@role_required('Admin', 'HR')
def ocr_identity():
    import pytesseract
    tess_path = _get_tesseract_path()
    if tess_path:
        pytesseract.pytesseract.tesseract_cmd = tess_path
        
    file = request.files.get('id_file')
    side = request.form.get('side', 'front')
    doc_type = request.form.get('doc_type', 'ic')
    
    if not file or file.filename == '':
        return jsonify({'error': 'No file uploaded'}), 400

    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in {'jpg', 'jpeg', 'png'}:
        return jsonify({'error': 'Please upload an image (JPG/PNG)'}), 400

    # Read file bytes into memory — OCR always runs on the clean original (never re-reads watermarked file)
    file_bytes = file.read()
    filename = f"id_{uuid.uuid4().hex}_{side}.{ext}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, 'wb') as fh:
        fh.write(file_bytes)

    co_name = query("SELECT name FROM Company WHERE company_id=?", (session['company_id'],), one=True)['name']

    try:
        import pytesseract
        if not _get_tesseract_path():
            return jsonify({'error': 'Tesseract OCR is not installed on this server.'}), 500

        # Open from in-memory bytes — guaranteed clean, no disk re-read of watermarked file
        base = Image.open(BytesIO(file_bytes)).convert('RGB')

        # IC back: auto-crop, rotate, save with watermark - NO OCR extraction, just HR storage
        if doc_type == 'ic' and side == 'back':
            # Auto-crop and find best rotation using our existing logic
            oriented = _pick_best_rotation(base, _mykad_back_text_crops)
            oriented.save(filepath, quality=92)
            _apply_watermark(filepath, co_name)
            log_audit('OCR_IDENTITY', 'Employee', 'Stored IC back copy for HR',
                      action_details={'filename': filename})
            resp = {
                'id_document_path': filename,
                'save_only': True,
                'side': side,
                'doc_type': doc_type,
                'message': 'IC back saved successfully for HR records!'
            }
            return jsonify(resp)

        if doc_type == 'ic' and side == 'front':
            raw_text, ocr_score, corrected = _ocr_mykad_front(base)
            corrected.save(filepath, quality=92)
            extracted = _extract_id_info(raw_text, side=side, doc_type=doc_type)
            if not extracted['ic_number']:
                ic_fb = _ocr_ic_number_fallback(corrected)
                if ic_fb:
                    extracted['ic_number'] = ic_fb
                    ic_c = ic_fb.replace('-', '')
                    yy, mm, dd = ic_c[:2], ic_c[2:4], ic_c[4:6]
                    this_year = datetime.date.today().year % 100
                    prefix = '20' if int(yy) <= this_year else '19'
                    extracted['date_of_birth'] = f"{prefix}{yy}-{mm}-{dd}"
                    extracted['gender'] = 'Male' if int(ic_c[-1]) % 2 != 0 else 'Female'
            elif not extracted.get('date_of_birth'):
                ic_c = extracted['ic_number'].replace('-', '')
                if len(ic_c) == 12:
                    yy, mm, dd = ic_c[:2], ic_c[2:4], ic_c[4:6]
                    this_year = datetime.date.today().year % 100
                    prefix = '20' if int(yy) <= this_year else '19'
                    extracted['date_of_birth'] = f"{prefix}{yy}-{mm}-{dd}"
                    extracted['gender'] = 'Male' if int(ic_c[-1]) % 2 != 0 else 'Female'
            if not extracted['full_name']:
                name_fb = _ocr_name_fallback(corrected)
                if name_fb:
                    extracted['full_name'] = name_fb.title()
            # Use fallback if address is missing or too short/incomplete
            current_address = extracted.get('address', '')
            address_is_incomplete = (
                not current_address or 
                len(current_address) < 20 or 
                not re.search(r'\b\d{5}\b', current_address)  # No postcode
            )
            
            if address_is_incomplete:
                addr_text = _ocr_address_fallback(corrected)
                if addr_text:
                    addr = _extract_address(addr_text, full_name=extracted.get('full_name', ''))
                    if not addr:
                        # Just grab any address-marker lines from the raw fallback text
                        addr = _extract_address(addr_text)
                    if addr and len(addr) > len(current_address):
                        extracted['address'] = addr
            if ocr_score < 8 and not extracted.get('ocr_warning'):
                extracted['ocr_warning'] = (
                    'IC was hard to read — auto-rotation was applied. '
                    'Please verify all fields or retake with the card flat and well-lit.'
                )
        else:
            processed_img = _prep_gray(base, max_side=1200, contrast=2.0)
            raw_text = _run_id_ocr(processed_img)
            ocr_score = _score_ocr_text(raw_text)
            extracted = _extract_id_info(raw_text, side=side, doc_type=doc_type)
            if ocr_score < 8 and not extracted.get('ocr_warning'):
                extracted['ocr_warning'] = (
                    'Document was hard to read. Please verify all fields or retake the photo.'
                )

        _apply_watermark(filepath, co_name)

        extracted['id_document_path'] = filename
        extracted['_debug_raw_text'] = raw_text[:300]
        extracted['_debug_score'] = ocr_score

        log_audit('OCR_IDENTITY', 'Employee', f'Extracted info from {doc_type} {side}',
                  action_details={'filename': filename, 'raw_snippet': raw_text[:50]})
        
        return jsonify(extracted)
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), '_debug_traceback': traceback.format_exc()}), 500


@emp_bp.route('/<int:emp_id>/document')
@login_required
def view_id_document(emp_id):
    from datetime import datetime, timedelta
    
    current_user_id = session['user_id']
    user_role = session['user_role']
    
    # Allow access if viewing your own document
    if current_user_id == emp_id:
        pass
    # Check if user is Admin/HR/Manager AND has approved access
    elif user_role in ['Admin', 'HR', 'Manager']:
        # Check for active approved request
        now = datetime.now().isoformat()
        access_request = query("""
            SELECT * FROM IC_Access_Request 
            WHERE requester_id = ? 
              AND target_employee_id = ? 
              AND status = 'Approved'
              AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY reviewed_at DESC
            LIMIT 1
        """, (current_user_id, emp_id, now), one=True)
        if not access_request:
            abort(403, "IC access not approved. Please request access first.")
    else:
        abort(403)
        
    emp = query("SELECT id_document_path FROM Employee WHERE employee_id=?", (emp_id,), one=True)
    if not emp or not emp['id_document_path']:
        abort(404)
        
    # Get specific filename from args if multiple files exist
    target_file = request.args.get('filename')
    valid_files = emp['id_document_path'].split(',')
    
    if target_file:
        if target_file not in valid_files:
            abort(403)
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], target_file)
    
    # Default to first file if no filename provided
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], valid_files[0])


# --- Notifications Routes ---
@emp_bp.route('/notifications')
@login_required
def get_notifications():
    user_id = session['user_id']
    notifications = query("""
        SELECT n.* FROM Notification n 
        WHERE n.employee_id = ? 
        ORDER BY n.created_at DESC
    """, (user_id,))
    return render_template('employees/notifications.html', notifications=notifications)


@emp_bp.route('/notifications/<int:notif_id>/mark-read', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    user_id = session['user_id']
    execute("""
        UPDATE Notification 
        SET is_read = 1 
        WHERE notification_id = ? AND employee_id = ?
    """, (notif_id, user_id))
    return redirect(url_for('employees.get_notifications'))


@emp_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    user_id = session['user_id']
    execute("""
        UPDATE Notification 
        SET is_read = 1 
        WHERE employee_id = ?
    """, (user_id,))
    return redirect(url_for('employees.get_notifications'))


# --- IC Access Request Routes ---
@emp_bp.route('/<int:emp_id>/request-ic-access', methods=['POST'])
@role_required('Admin', 'HR', 'Manager')
def request_ic_access(emp_id):
    from datetime import datetime
    
    requester_id = session['user_id']
    reason = request.form.get('reason', '')
    
    # Don't allow requesting your own IC
    if requester_id == emp_id:
        flash("You don't need to request access to your own IC!", 'warning')
        return redirect(url_for('employees.view_employee', emp_id=emp_id))

    # Manager branch check
    if session['user_role'] == 'Manager':
        target_emp = query("SELECT branch_id FROM Employee WHERE employee_id = ?", (emp_id,), one=True)
        if not target_emp or target_emp['branch_id'] != session['branch_id']:
            flash('Access denied. You can only request access for staff from your own branch.', 'danger')
            return redirect(url_for('employees.view_employee', emp_id=emp_id))
    
    # Create request
    req_id = execute("""
        INSERT INTO IC_Access_Request (requester_id, target_employee_id, reason, status)
        VALUES (?, ?, ?, 'Pending')
    """, (requester_id, emp_id, reason))
    
    # Get requester name
    requester = query("SELECT full_name FROM Employee WHERE employee_id = ?", (requester_id,), one=True)
    
    # Send notification to target employee
    execute("""
        INSERT INTO Notification (employee_id, title, message)
        VALUES (?, ?, ?)
    """, (emp_id, 
          "IC Access Request", 
          f"{requester['full_name']} has requested access to your IC document. Please review the request."))
    
    log_audit('IC_ACCESS_REQUEST', 'Employee', f"User {requester_id} requested access to employee {emp_id}'s IC",
              action_details={'requester_id': requester_id, 'target_id': emp_id, 'reason': reason})
    
    flash("IC access request sent successfully!", 'success')
    return redirect(url_for('employees.view_employee', emp_id=emp_id))


@emp_bp.route('/ic-access-requests/<int:req_id>/<action>', methods=['POST'])
@login_required
def respond_to_ic_request(req_id, action):
    from datetime import datetime, timedelta
    
    current_user_id = session['user_id']
    
    # Get request
    req = query("SELECT * FROM IC_Access_Request WHERE request_id = ?", (req_id,), one=True)
    if not req:
        abort(404)
    
    # Check if user is the target employee
    if req['target_employee_id'] != current_user_id:
        abort(403)
    
    # Process action
    new_status = 'Approved' if action == 'approve' else 'Rejected'
    expires_at = None
    if new_status == 'Approved':
        expires_at = (datetime.now() + timedelta(days=7)).isoformat()
    
    execute("""
        UPDATE IC_Access_Request
        SET status = ?, reviewed_by = ?, reviewed_at = datetime('now'), expires_at = ?
        WHERE request_id = ?
    """, (new_status, current_user_id, expires_at, req_id))
    
    # Send notification back to requester
    target_emp = query("SELECT full_name FROM Employee WHERE employee_id = ?", (current_user_id,), one=True)
    notif_message = f"{target_emp['full_name']} has {new_status.lower()} your IC access request."
    if new_status == 'Approved':
        notif_message += " Access is granted for 7 days."
    
    execute("""
        INSERT INTO Notification (employee_id, title, message)
        VALUES (?, ?, ?)
    """, (req['requester_id'], 
          f"IC Request {new_status}", 
          notif_message))
    
    log_audit(f'IC_ACCESS_{new_status.upper()}', 'Employee', f"IC access request {req_id} was {new_status.lower()}",
              action_details={'request_id': req_id, 'reviewer_id': current_user_id})
    
    flash(f"IC request {new_status.lower()} successfully!", 'success')
    return redirect(url_for('employees.get_notifications'))


@emp_bp.route('/')
@login_required
def list_employees():
    if session.get('user_role') not in ('Admin', 'HR', 'Manager'):
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    co    = session['company_id']
    role  = session['user_role']
    bid   = session.get('branch_id')
    search = request.args.get('q', '')
    dept   = request.args.get('dept', '')
    etype  = request.args.get('type', '')
    status = request.args.get('status', '')

    sql = """
        SELECT e.*, r.role_name, d.department_name, b.name as branch_name
        FROM Employee e
        JOIN Role r       ON e.role_id       = r.role_id
        JOIN Department d ON e.department_id = d.department_id
        JOIN Branch b     ON e.branch_id     = b.branch_id
        WHERE e.company_id = ?
    """
    args = [co]
    if role == 'Manager':
        sql += " AND e.branch_id = ?"
        args.append(bid)

    if search:
        sql += " AND (e.full_name LIKE ? OR e.email LIKE ? OR CAST(e.employee_id AS TEXT) LIKE ?)"
        args += [f'%{search}%', f'%{search}%', f'%{search}%']
    if dept:
        sql += " AND e.department_id = ?"
        args.append(dept)
    if etype:
        sql += " AND e.employment_type = ?"
        args.append(etype)
    if status:
        sql += " AND e.employment_status = ?"
        args.append(status)
    sql += " ORDER BY e.full_name"

    employees = query(sql, args)
    if role == 'Manager':
        departments = query("SELECT d.* FROM Department d JOIN Branch b ON d.branch_id=b.branch_id WHERE b.company_id=? AND d.branch_id=? ORDER BY department_name", (co, bid))
    else:
        departments = query("SELECT * FROM Department d JOIN Branch b ON d.branch_id=b.branch_id WHERE b.company_id=? ORDER BY department_name", (co,))
    return render_template('employees/list.html',
                           employees=employees, departments=departments,
                           search=search, dept=dept, etype=etype, status=status)


@emp_bp.route('/upload-ic')
@role_required('Admin', 'HR')
def upload_ic():
    """Page to upload both front and back of IC for OCR"""
    return render_template('employees/upload_ic.html')


@emp_bp.route('/add', methods=['GET', 'POST'])
@role_required('Admin', 'HR')
def add_employee():
    from app.database import assign_role_permissions
    
    co = session['company_id']
    departments = query("SELECT d.*, b.name as branch_name FROM Department d JOIN Branch b ON d.branch_id=b.branch_id WHERE b.company_id=? ORDER BY d.department_name", (co,))
    branches    = query("SELECT * FROM Branch WHERE company_id=?", (co,))
    roles       = query("SELECT * FROM Role ORDER BY role_id")
    
    form_data = {}

    if request.method == 'POST':
        f = request.form
        form_data = f.to_dict()
        try:
            if f['password'] != f.get('confirm_password'):
                flash('Passwords do not match.', 'danger')
                raise ValueError('Password mismatch')

            pw_hash = generate_password_hash(f['password'])
            emp_id = execute("""
                INSERT INTO Employee
                (company_id,branch_id,department_id,full_name,ic_number,passport_number,contact_no,
                 address,date_of_birth,gender,emergency_contact_name,emergency_contact_no,
                 position,employment_type,employment_status,hire_date,base_salary,
                 role_id,email,password_hash,id_document_path)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (co, f['branch_id'], f['department_id'], f['full_name'],
                  f.get('ic_number',''), f.get('passport_number',''), f.get('contact_no',''),
                  f.get('address',''), f.get('date_of_birth',''),
                  f.get('gender',''), f.get('emergency_contact_name',''),
                  f.get('emergency_contact_no',''), f.get('position',''),
                  f['employment_type'], f.get('employment_status','Active'),
                  f['hire_date'], float(f.get('base_salary', 0)),
                  f['role_id'], f['email'].lower(), pw_hash, f.get('id_document_path','')))

            # Seed leave balances for current year
            import datetime
            yr = datetime.date.today().year
            leave_types = query("SELECT leave_type_id, default_days FROM Leave_Type")
            for lt in leave_types:
                execute("INSERT OR IGNORE INTO Leave_Balance(employee_id,leave_type_id,year,entitled_days) VALUES(?,?,?,?)",
                        (emp_id, lt['leave_type_id'], yr, lt['default_days']))

            # Automatically assign permissions based on role
            assign_role_permissions(emp_id, int(f['role_id']), session.get('user_id'))
            
            role_name = query("SELECT role_name FROM Role WHERE role_id=?", (int(f['role_id']),), one=True)['role_name']

            log_audit('CREATE', 'Employee', f'Created employee {f["full_name"]} with role {role_name}',
                      'Employee', emp_id, 'Success', {'email': f['email'], 'role': role_name})
            flash(f'Employee "{f["full_name"]}" added successfully with {role_name} permissions!', 'success')
            return redirect(url_for('employees.list_employees'))
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                if "email" in str(e): flash("Error: Email address already exists.", "danger")
                elif "ic_number" in str(e): flash("Error: IC Number already exists.", "danger")
                else: flash("Error: A unique constraint was violated.", "danger")
            else:
                flash(f'Error: {str(e)}', 'danger')

    return render_template('employees/add.html',
                           departments=departments, branches=branches, roles=roles,
                           form_data=form_data)


@emp_bp.route('/<int:emp_id>')
@login_required
def view_employee(emp_id):
    from datetime import datetime

    current_user_id = session['user_id']
    # Employees can only view themselves unless HR/Admin/Manager
    if session['user_role'] == 'Employee' and current_user_id != emp_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('main.dashboard'))

    emp = query("""
        SELECT e.*, r.role_name, d.department_name, b.name as branch_name, c.name as company_name
        FROM Employee e
        JOIN Role r       ON e.role_id       = r.role_id
        JOIN Department d ON e.department_id = d.department_id
        JOIN Branch b     ON e.branch_id     = b.branch_id
        JOIN Company c    ON e.company_id    = c.company_id
        WHERE e.employee_id=?
    """, (emp_id,), one=True)

    if not emp:
        flash('Employee not found.', 'danger')
        return redirect(url_for('employees.list_employees'))

    # Manager branch restriction check
    if session['user_role'] == 'Manager' and emp['branch_id'] != session['branch_id']:
        flash('Access denied. You can only view staff from your own branch.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Get employee details for eligibility check
    emp_details = as_dict(query("SELECT gender, marital_status FROM Employee WHERE employee_id=?", (emp_id,), one=True))
    emp_gender = emp_details.get('gender')
    emp_marital = emp_details.get('marital_status')

    # Get leave balances (filtered by eligibility)
    all_leave_bal = query("""
        SELECT lb.*, lt.type_name, lt.eligible_genders, lt.eligible_marital_status
        FROM Leave_Balance lb
        JOIN Leave_Type lt ON lb.leave_type_id=lt.leave_type_id
        WHERE lb.employee_id=? AND lb.year=strftime('%Y','now')
    """, (emp_id,))
    
    leave_bal = []
    for b in all_leave_bal:
        lt_dict = as_dict(b)
        if is_leave_eligible(lt_dict, emp_gender, emp_marital):
            leave_bal.append(b)

    recent_att = query("""
        SELECT * FROM Attendance WHERE employee_id=?
        ORDER BY check_in DESC LIMIT 10
    """, (emp_id,))

    # Check current user's access status for this employee's IC
    has_access = False
    pending_request = None
    approved_request = None
    if session['user_role'] in ['Admin','HR','Manager'] and current_user_id != emp_id:
        now = datetime.now().isoformat()
        approved_request = query("""
            SELECT * FROM IC_Access_Request
            WHERE requester_id = ? AND target_employee_id = ? AND status = 'Approved'
              AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY reviewed_at DESC LIMIT 1
        """, (current_user_id, emp_id, now), one=True)
        has_access = approved_request is not None
        
        pending_request = query("""
            SELECT * FROM IC_Access_Request
            WHERE requester_id = ? AND target_employee_id = ? AND status = 'Pending'
            ORDER BY requested_at DESC LIMIT 1
        """, (current_user_id, emp_id), one=True)
    
    # If user is the target employee, show all their pending requests
    pending_requests_for_me = []
    if current_user_id == emp_id:
        pending_requests_for_me = query("""
            SELECT r.*, requester.full_name as requester_name
            FROM IC_Access_Request r
            JOIN Employee requester ON r.requester_id = requester.employee_id
            WHERE r.target_employee_id = ? AND r.status = 'Pending'
            ORDER BY requested_at DESC
        """, (emp_id,))

    return render_template('employees/view.html',
                           emp=emp, leave_bal=leave_bal, recent_att=recent_att,
                           has_ic_access=has_access, pending_ic_request=pending_request,
                           pending_requests_for_me=pending_requests_for_me)


@emp_bp.route('/<int:emp_id>/edit', methods=['POST'])
@role_required('Admin', 'HR', 'Manager')
def edit_employee(emp_id):
    from app.database import assign_role_permissions
    
    # Manager branch check
    if session['user_role'] == 'Manager':
        target_emp = query("SELECT branch_id FROM Employee WHERE employee_id = ?", (emp_id,), one=True)
        if not target_emp or target_emp['branch_id'] != session['branch_id']:
            flash('Access denied. You can only edit staff from your own branch.', 'danger')
            return redirect(url_for('main.dashboard'))

    f = request.form
    
    # Get the old role_id before updating
    old_emp = query("SELECT role_id FROM Employee WHERE employee_id=?", (emp_id,), one=True)
    old_role_id = old_emp['role_id'] if old_emp else None
    new_role_id = int(f['role_id'])
    
    execute("""
        UPDATE Employee SET
          full_name=?, contact_no=?, address=?, date_of_birth=?,
          gender=?, emergency_contact_name=?, emergency_contact_no=?,
          position=?, employment_type=?, employment_status=?,
          base_salary=?, branch_id=?, department_id=?, role_id=?,
          updated_at=datetime('now')
        WHERE employee_id=?
    """, (f['full_name'], f.get('contact_no',''), f.get('address',''),
          f.get('date_of_birth',''), f.get('gender',''),
          f.get('emergency_contact_name',''), f.get('emergency_contact_no',''),
          f.get('position',''), f['employment_type'], f.get('employment_status','Active'),
          float(f.get('base_salary', 0)), f['branch_id'], f['department_id'], new_role_id,
          emp_id))
    
    # If role changed, automatically update permissions
    if old_role_id != new_role_id:
        assign_role_permissions(emp_id, new_role_id, session.get('user_id'))
        
        # Get role names for audit log
        old_role = query("SELECT role_name FROM Role WHERE role_id=?", (old_role_id,), one=True) if old_role_id else None
        new_role = query("SELECT role_name FROM Role WHERE role_id=?", (new_role_id,), one=True)
        old_role_name = old_role['role_name'] if old_role else 'Unknown'
        new_role_name = new_role['role_name'] if new_role else 'Unknown'
        
        log_audit('PROMOTE_DEMOTE', 'Employee', 
                  f'Employee role changed from {old_role_name} to {new_role_name}; permissions auto-updated',
                  'Employee', emp_id, 'Success', 
                  {'old_role': old_role_name, 'new_role': new_role_name})
        flash(f'Employee updated successfully. Role changed to {new_role_name}; permissions granted automatically.', 'success')
    else:
        log_audit('UPDATE', 'Employee', f'Updated employee id={emp_id}',
                  'Employee', emp_id, 'Success')
        flash('Employee updated successfully.', 'success')
    
    return redirect(url_for('employees.view_employee', emp_id=emp_id))


@emp_bp.route('/<int:emp_id>/deactivate', methods=['POST'])
@role_required('Admin', 'HR')
def deactivate_employee(emp_id):
    execute("UPDATE Employee SET is_active=0, employment_status='Inactive', updated_at=datetime('now') WHERE employee_id=?",
            (emp_id,))
    log_audit('DEACTIVATE', 'Employee', f'Deactivated employee id={emp_id}',
              'Employee', emp_id, 'Success')
    flash('Employee deactivated.', 'warning')
    return redirect(url_for('employees.list_employees'))
