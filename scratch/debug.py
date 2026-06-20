#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytesseract
from app import create_app
from app.invoice.routes import _extract_all
from app.invoice.routes import _preprocess_image

app = create_app()

img_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_inv', 'test1.jpg'))
img = _preprocess_image(img_path)
raw = pytesseract.image_to_string(img, config=r'--oem 3 --psm 4')

# Let's monkey-patch _extract_all or insert print statements into the real _extract_all
# But since I can't easily print inside _extract_all, I'll just temporarily add prints to routes.py and run it.
