# Face Recognition Integration Guide - Phase 1: Face Registration

## 🎯 Overview

This guide covers **Phase 1: Face Registration**, which allows HR/Admin users to capture and register employee faces for the facial recognition attendance system.

---

## 📋 Prerequisites

### 1. Install Dependencies
Run the updated requirements.txt:

```bash
pip install -r requirements.txt
```

Key additions:
- `face-recognition` – Face detection & encoding
- `numpy` – Array operations for encodings
- `opencv-python-headless` – Image processing

### 2. Tesseract Installation (Optional for Phase 1, Required for Phase 2)
- **Windows**: Download from [GitHub Tesseract releases](https://github.com/UB-Mannheim/tesseract/wiki)
- **Linux**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`

---

## 🚀 Quick Start

### 1. Prepare Database
```bash
# Initialize database with demo data
python init_db.py
```

This creates the SQLite database and seeds it with 10 test employees (ID: 1-10).

### 2. Start Application
```bash
python run.py
```

Access at: `http://localhost:5000`

### 3. Login as HR Admin
- **Email**: `hr@smarthr.my`
- **Password**: `Hr@123`

(System Admin: `admin@smarthr.my` / `Admin@123`)

---

## 🎥 How to Register a Face

### Step 1: Navigate to Face Registration

From the **Employees** module:
1. Click "List Employees"
2. Find the target employee
3. Click "Register Face" button (🎥 icon)

OR direct URL:
```
http://localhost:5000/face/register/<employee_id>
```

### Step 2: Capture Face Photo

1. **Allow camera access** when browser prompts
2. **Position face** clearly in the video frame
3. **Ensure good lighting** (no shadows)
4. **Remove accessories** (sunglasses, hats) if possible
5. Click **"📸 Capture Photo"** button

### Step 3: Register Face

1. Review the captured photo
2. Click **"✅ Register Face"** to submit
3. System validates and stores the face encoding
4. **Success message** confirms registration
5. Auto-redirects to Employees list after 2 seconds

### Step 4: Retake if Needed

If capture failed or quality is poor:
1. Click **"🔄 Retake Photo"** button
2. Repeat capture steps
3. **Max 5 attempts** per session (then refresh page)

---

## 🔍 Common Issues & Fixes

### Issue 1: "No face detected"
**Solutions:**
- Ensure face is clearly visible
- Move closer to camera
- Improve lighting (avoid backlighting)
- Remove sunglasses/masks
- Look directly at camera

### Issue 2: "Multiple faces detected"
**Solution:**
- Only one person should be in frame
- Ensure no mirrors or others in background

### Issue 3: Camera not working
**Solutions:**
- Check browser permissions (Settings → Permissions → Camera)
- Try different browser (Chrome/Firefox work best)
- Ensure webcam is connected and enabled
- Restart browser

### Issue 4: "Failed to decode image"
**Solutions:**
- Ensure good internet connection (for data transmission)
- Try capturing again
- Clear browser cache (Ctrl+Shift+Delete)

### Issue 5: Error on submit
**Check:**
- Employee ID exists in database
- You are logged in as HR/Admin
- Network connection is stable
- Server is running (`python run.py`)

---

## 🗂️ File Structure

```
app/
├── face/                          # NEW: Face recognition module
│   ├── __init__.py               # Blueprint initialization
│   └── routes.py                 # Face registration endpoints
│       ├── @face_bp.route('/register/<emp_id>')  # Registration page
│       ├── @face_bp.route('/api/register')       # Upload & process face
│       └── @face_bp.route('/api/status/<emp_id>') # Check registration status

templates/
└── face/                          # NEW: Face templates
    └── register_face.html         # Webcam + capture UI
```

---

## 🔌 API Reference

### 1. Get Registration Page
```
GET /face/register/<employee_id>
```
**Access:** HR/Admin only  
**Returns:** HTML registration page with webcam

**Example:**
```
GET /face/register/4
```

### 2. Register Face Encoding
```
POST /face/api/register
```
**Access:** HR/Admin only  
**Content-Type:** `application/json`

**Request Body:**
```json
{
  "employee_id": 4,
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**Response (Success):**
```json
{
  "success": true,
  "msg": "Face registered successfully"
}
```

**Response (Error - No Face):**
```json
{
  "success": false,
  "msg": "No face detected. Please ensure your face is clearly visible."
}
```

**Response (Error - Multiple Faces):**
```json
{
  "success": false,
  "msg": "Multiple faces detected (2). Please ensure only one person is in the frame."
}
```

### 3. Check Registration Status
```
GET /face/api/status/<employee_id>
```
**Access:** HR/Admin only  
**Returns:** JSON with registration status

**Response (Registered):**
```json
{
  "has_face": true,
  "updated_at": "2026-04-21 14:30:00"
}
```

**Response (Not Registered):**
```json
{
  "has_face": false
}
```

---

## 💾 Database Storage

Face encodings are stored securely in the `Face_Encoding` table:

| Column | Type | Description |
|--------|------|-------------|
| `face_encoding_id` | INTEGER | Primary key (auto-increment) |
| `employee_id` | INTEGER | FK to Employee |
| `face_encoding_blob` | BLOB | 128-dim numpy array (1024 bytes) |
| `registered_by` | INTEGER | FK to Employee (HR/Admin who registered) |
| `updated_at` | TIMESTAMP | Last registration/update time |

**SQL Query to view all registered faces:**
```sql
SELECT e.employee_id, e.full_name, f.updated_at, reg.full_name as registered_by
FROM Face_Encoding f
JOIN Employee e ON f.employee_id = e.employee_id
LEFT JOIN Employee reg ON f.registered_by = reg.employee_id
ORDER BY f.updated_at DESC;
```

---

## 🔒 Security Notes

### Access Control
- ✅ Only **HR** and **Admin** roles can register faces
- ✅ Session-based authentication required
- ✅ All endpoints protected with `@login_required` and `@role_required` decorators

### Data Privacy
- ✅ Face encodings stored **locally only** (not cloud)
- ✅ Encrypted in BLOB format (not human-readable)
- ✅ SQLite database file encrypted at rest (optional with `sqlcipher`)
- ✅ HTTPS recommended for production (add SSL certificate)

### Before Production
- [ ] Change `SECRET_KEY` in `app/__init__.py`
- [ ] Enable HTTPS (add SSL certificate)
- [ ] Implement rate limiting on `/api/register`
- [ ] Add CSRF protection to forms
- [ ] Audit face registrations (already logged in AuditLog)
- [ ] Implement data retention policy (e.g., re-register annually)

---

## 📊 Testing Checklist

- [ ] Install all dependencies (`pip install -r requirements.txt`)
- [ ] Initialize database (`python init_db.py`)
- [ ] Start server (`python run.py`)
- [ ] Login as HR (`hr@smarthr.my` / `Hr@123`)
- [ ] Navigate to Employees list
- [ ] Select an employee (e.g., Elizabeth Lopez - ID 4)
- [ ] Click "Register Face" button
- [ ] Allow camera access in browser
- [ ] Capture a photo (face clearly visible)
- [ ] Click "Register Face" to submit
- [ ] See success message
- [ ] Verify in database: `SELECT COUNT(*) FROM Face_Encoding;`
- [ ] Retake registration for same employee (should update, not duplicate)

---

## 🚀 Next Steps (Phase 2)

After Phase 1 is tested and working:

**Phase 2: Real-Time Face Attendance**
- Employee login + webcam-based check-in/out
- Real-time face matching (strict tolerance 0.4)
- Automatic attendance logging
- Manual fallback entry
- Real-time feedback UI

---

## 📞 Support

### Debugging

Enable detailed logging in `app/face/routes.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check browser console (F12 → Console tab) for JavaScript errors.

### Common Error Codes

| Error | Cause | Fix |
|-------|-------|-----|
| 400 Bad Request | Missing employee_id or image | Ensure both fields in JSON |
| 403 Forbidden | Not HR/Admin role | Login as correct user |
| 404 Not Found | Employee doesn't exist | Verify employee_id in database |
| 500 Server Error | Face detection failed | Check server logs, improve image quality |

---

## 📝 Notes

- Face encodings are **128-dimensional vectors** created by the `face_recognition` library
- Tolerance for matching is **0.6 for registration** (can re-register), **0.4 for real-time matching** (strict for security)
- Each face registration takes ~500ms-1s
- Database stores ~1024 bytes per face encoding (compact BLOB)

---

## 🎓 Recommended Reading

- [face_recognition Library Docs](https://face-recognition.readthedocs.io/)
- [WebRTC getUserMedia API](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)
- [dlib Face Detection](http://dlib.net/python/index.html)

---

**Version:** Phase 1.0  
**Date:** June 15, 2026  
**Status:** ✅ Ready for Testing
