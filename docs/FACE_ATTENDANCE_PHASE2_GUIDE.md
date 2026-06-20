# Face Recognition - Phase 2: Real-Time Face Attendance

## 🎯 Overview

Phase 2 implements **real-time facial recognition-based attendance** where employees can automatically check in/out by showing their face to a webcam. This includes:

✅ Employee login + face attendance page  
✅ Real-time face matching (strict tolerance 0.4)  
✅ Automatic check-in/out recording  
✅ Manual fallback entry (if face fails)  
✅ Today's attendance viewing  

---

## 📋 Prerequisites

### Phase 1 Must Be Complete
- ✅ Face registration module working
- ✅ At least 1 employee with registered face
- ✅ `requirements.txt` updated with `face-recognition`

### Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Quick Start

### 1. Verify Phase 1 Setup
Ensure you have registered faces for test employees:
```bash
python init_db.py  # Initialize database
```

### 2. Start Application
```bash
python run.py
```
Access: `http://localhost:5000`

### 3. Test Face Attendance

#### Step 1: Register a Face (if not done yet)
- Login as HR: `hr@smarthr.my` / `Hr@123`
- Go to Employees → Select employee
- Click "Register Face" → Capture photo

#### Step 2: Employee Face Check-In
- Login as employee: `elizabeth@smarthr.my` / `Employee@123`
- Navigate to the **Attendance** module (or direct URL: `/face/attendance`)
- If face registered: Shows real-time attendance page
- If not registered: Shows "Face Not Registered" warning

#### Step 3: Automatic Check-In/Out
1. **Position face** in webcam frame (centered, well-lit)
2. System captures frame every **2-3 seconds**
3. **Match found** → Auto record check-in
4. **Same face again** → Auto record check-out
5. **View today's records** in "Today's Attendance" panel

---

## 📁 Files Created/Modified

### New Files (Phase 2)
```
app/face/
├── matcher.py              ← Face matching cache & logic
├── routes.py               ← ENHANCED with real-time endpoints
│   ├── /face/attendance    ← Face attendance page
│   ├── /face/api/match_and_record  ← Real-time matching
│   ├── /face/api/record_manual     ← Fallback entry
│   └── /face/api/today_attendance  ← Get today's records

templates/face/
├── face_attendance.html    ← Real-time attendance UI
└── no_face_registered.html ← Warning page (no face)
```

### Modified Files
```
app/face/__init__.py        ← Initialize face cache on import
app/__init__.py             ← Face blueprint already registered
```

---

## 🔌 API Endpoints (Phase 2)

### 1. Face Attendance Page
```
GET /face/attendance
```
**Requires:** Employee login  
**Returns:** HTML page with webcam + manual entry form

**Logic:**
- If face registered → Show attendance page
- If not registered → Show "Register face" warning

---

### 2. Real-Time Face Matching + Attendance Record
```
POST /face/api/match_and_record
```
**Requires:** Employee login + registered face  
**Content-Type:** `application/json`

**Request:**
```json
{
  "image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**Response (Success - Face Matched):**
```json
{
  "success": true,
  "msg": "✅ Checked in at 09:15:30",
  "attendance": {
    "action": "check_in",
    "time": "09:15:30",
    "msg": "✅ Checked in at 09:15:30"
  },
  "confidence": 0.95
}
```

**Response (Success - Check Out):**
```json
{
  "success": true,
  "msg": "✅ Checked out at 18:30:45 (9.25h)",
  "attendance": {
    "action": "check_out",
    "time": "18:30:45",
    "hours_worked": 9.25,
    "msg": "✅ Checked out at 18:30:45 (9.25h)"
  },
  "confidence": 0.92
}
```

**Response (Failure - Face Not Recognized):**
```json
{
  "success": false,
  "msg": "Face not recognized (distance: 0.52, tolerance: 0.4)",
  "confidence": 0.48
}
```

**Response (Error - No Face Detected):**
```json
{
  "success": false,
  "msg": "No face detected. Please position your face in the camera."
}
```

---

### 3. Manual Attendance Entry (Fallback)
```
POST /face/api/record_manual
```
**Requires:** Employee login  
**Content-Type:** `application/json`

**Request:**
```json
{
  "check_in_time": "09:00",
  "check_out_time": "18:00",
  "reason": "Camera was not available"
}
```

**Response (Success):**
```json
{
  "success": true,
  "msg": "Manual entry recorded (pending HR approval)"
}
```

**Response (Error - Already Exists):**
```json
{
  "success": false,
  "msg": "Manual entry already exists for today"
}
```

---

### 4. Get Today's Attendance Records
```
GET /face/api/today_attendance
```
**Requires:** Employee login  
**Returns:** All attendance records for today (check-ins/outs)

**Response:**
```json
{
  "success": true,
  "date": "2026-06-15",
  "records": [
    {
      "check_in": "09:15:30",
      "check_out": "13:00:00",
      "hours_worked": 3.75,
      "status": "Approved",
      "manual": false
    },
    {
      "check_in": "14:00:00",
      "check_out": "Still logged in",
      "hours_worked": null,
      "status": "Pending",
      "manual": false
    }
  ]
}
```

---

## 🤖 Real-Time Matching Logic

### Tolerance System
- **Strict Matching (Attendance)**: `tolerance = 0.4`
  - Reduces false positives
  - Only exact/near-exact matches recorded
  - Security-focused

- **Lenient Matching (Registration)**: `tolerance = 0.6`
  - Allows re-registration with slight variations
  - User-friendly

### Matching Workflow

```
Employee starts face attendance page
    ↓
System loads all registered face encodings in memory (cache)
    ↓
Camera captures frame every 2-3 seconds
    ↓
Extract face from frame
    ↓
Compare against all cached encodings
    ↓
Find best match (minimum distance)
    ↓
Distance <= 0.4 tolerance?
    ├─ YES: Match found!
    │   └─ Record check-in or check-out
    │   └─ Return success + confidence score
    └─ NO: No match
        └─ Confidence too low
        └─ Suggest manual entry
```

### Check-In/Check-Out Logic

```
Query today's attendance for employee
    ↓
Is there a record with check_out = NULL?
    ├─ YES: Already checked in
    │   └─ Record check-out time
    │   └─ Calculate hours: check_out - check_in
    │   └─ Update Attendance record
    └─ NO: Not checked in
        └─ Create new Attendance record
        └─ Set check_in time
        └─ Set status = 'Pending' (HR approval)
```

---

## 🎨 User Interface

### Real-Time Attendance Page

```
┌─────────────────────────────┬─────────────────┐
│   📹 LIVE CAMERA            │     STATUS      │
│                             │                 │
│   [Webcam Stream]           │  🟢 Ready       │
│   (480x360)                 │  ⏳ Processing  │
│                             │  ✅ Success     │
│                             │  ❌ Error       │
│                             │                 │
│                             │  Confidence: 95%│
│                             │  Attempts: 2/10 │
├─────────────────────────────┴─────────────────┤
│📋 Instructions:                              │
│ • Position face centered in camera           │
│ • Good lighting (no shadows)                 │
│ • First match = check-in, Second = checkout  │
├──────────────────┬──────────────────────────┤
│  🤖 Auto Mode    │  📝 Manual Entry         │
│ ⏸ Pause          │ 🕐 Enter time            │
│ ▶ Resume         │ (fallback option)        │
├──────────────────┴──────────────────────────┤
│📊 Today's Attendance                        │
│ Check-in: 09:15   | Check-out: 13:00        │
│ Hours: 3.75h      | Status: Approved        │
└───────────────────────────────────────────────┘
```

### Manual Entry Modal

```
┌────────────────────────────────────────┐
│ 📝 MANUAL TIME ENTRY                  │
├────────────────────────────────────────┤
│                                        │
│ Check-In Time *: [09:00]               │
│ Check-Out Time:  [18:00]               │
│ Reason:          [Face not recognized] │
│                                        │
│ ⓘ Note: Manual entries pending HR     │
│                                        │
│              [Cancel] [Submit]         │
└────────────────────────────────────────┘
```

---

## 🧪 Testing Checklist

### Test Case 1: Successful Auto Check-In/Out
- [ ] Login as employee with registered face
- [ ] Go to `/face/attendance`
- [ ] Position face in camera
- [ ] Face detected & matched → Check-in recorded
- [ ] Wait 2-3 seconds, show face again → Check-out recorded
- [ ] Verify in "Today's Attendance" panel
- [ ] Check database: `SELECT * FROM Attendance WHERE employee_id=4 AND date(check_in)=date('now');`

### Test Case 2: No Face Registered
- [ ] Login as new employee (no face)
- [ ] Go to `/face/attendance`
- [ ] See "Face Not Registered" warning page
- [ ] Option to contact HR for registration

### Test Case 3: Manual Fallback Entry
- [ ] Go to face attendance page
- [ ] Don't show face (camera not working, etc.)
- [ ] Click "Manual Entry" button
- [ ] Enter check-in time (e.g., 09:00)
- [ ] Click "Submit"
- [ ] See "Manual entry recorded (pending HR approval)"
- [ ] Verify in Today's Attendance (manual flag)

### Test Case 4: Face Not Recognized
- [ ] Go to face attendance page
- [ ] Show someone else's face (different person)
- [ ] System shows: "Face not recognized"
- [ ] Suggest manual entry
- [ ] After max attempts (10), disable auto mode

### Test Case 5: Mobile/Device Compatibility
- [ ] Open face attendance on desktop (Chrome/Firefox)
- [ ] Open on mobile phone (iOS/Android browser)
- [ ] Test with front camera (phone/laptop)
- [ ] Verify responsive UI adapts

---

## 🔒 Security Considerations

### Access Control
✅ Only logged-in employees can access `/face/attendance`  
✅ Employee can only record their own face (checked against `session['user_id']`)  
✅ Matched employee ID must equal logged-in employee ID

### Face Matching Security
✅ **Strict tolerance (0.4)** prevents spoofing  
✅ **Real-time matching** (not one-time) ensures person present  
✅ Cache invalidated on app restart  
✅ Face encodings stored locally (not cloud)

### Data Privacy
✅ Face encodings **not human-readable** (128-dim float64 vectors)  
✅ **BLOB storage only** (no images stored)  
✅ Employee can't see other employees' face data  
✅ Audit log tracks all attendance changes

### Before Production
- [ ] Enable HTTPS (SSL certificate)
- [ ] Implement rate limiting on endpoints
- [ ] Add CSRF protection to forms
- [ ] Change `SECRET_KEY` in `app/__init__.py`
- [ ] Implement face cache refresh policy (e.g., hourly)
- [ ] Add data retention policy (delete encodings after X years)
- [ ] Require HR approval for sensitive attendance changes
- [ ] Audit all manual entries monthly

---

## 🐛 Common Issues & Fixes

| Issue | Cause | Solution |
|-------|-------|----------|
| "No face detected" | Face not visible or poor lighting | Move closer, improve lighting, remove sunglasses |
| "Multiple faces detected" | Other people in frame | Ensure only employee in frame |
| "Face not recognized" | Different angle/lighting than registration | Re-register with varied angles, better lighting |
| Can't access `/face/attendance` | Not logged in, or not an employee | Login first, verify employee account |
| "Face not registered" warning | Face encoding doesn't exist | Contact HR to register face |
| Manual entry fails | Already has manual entry for today | HR must delete/approve existing entry first |
| Slow matching | Large number of registered faces | Cache may be outdated, restart server |

---

## 📊 Database Changes

No schema changes from Phase 1. Uses existing:
- **Attendance** table: Records check-in/out times
- **Face_Encoding** table: Stores face encodings
- **Employee** table: Links employee to face data

### Query to View Today's Attendance
```sql
SELECT 
    e.full_name, 
    a.check_in, 
    a.check_out,
    a.hours_worked,
    a.status,
    a.is_manual_entry
FROM Attendance a
JOIN Employee e ON a.employee_id = e.employee_id
WHERE date(a.check_in) = date('now')
ORDER BY a.check_in DESC;
```

### Query to Find Matched Faces
```sql
SELECT 
    e.employee_id,
    e.full_name,
    COUNT(a.attendance_id) as check_ins_today
FROM Attendance a
JOIN Employee e ON a.employee_id = e.employee_id
WHERE date(a.check_in) = date('now')
    AND a.is_manual_entry = 0
GROUP BY e.employee_id;
```

---

## 🚀 Performance Tips

### Face Cache Optimization
- Face encodings cached **in-memory** on app start
- Refresh triggered: App restart, or manual call
- **Ideal for 1000+ employees**

### Timeout Configuration
Adjust capture frequency based on device:
```javascript
// Current: 2 seconds per capture (default)
setTimeout(startContinuousCapture, 2000);  // Lazy devices

// Faster: 1 second (powerful devices)
setTimeout(startContinuousCapture, 1000);

// Slower: 3 seconds (minimize CPU)
setTimeout(startContinuousCapture, 3000);
```

### Database Indexing
Recommended indexes for faster queries:
```sql
CREATE INDEX idx_attendance_emp_date ON Attendance(employee_id, check_in);
CREATE INDEX idx_face_emp_id ON Face_Encoding(employee_id);
```

---

## 📝 Notes

- **Real-time processing**: Frames sent to server for processing (Python handles image processing, not JavaScript)
- **BLOB storage**: 128-dimensional face encoding = ~1024 bytes per employee
- **Stateless design**: Each request independent (no session state on server for matching)
- **Fallback mode**: Manual entry always available if face fails
- **Audit trail**: All attendance auto-recorded in AuditLog

---

## 🎓 Recommended Reading

- [Face Recognition Library](https://face-recognition.readthedocs.io/)
- [WebRTC getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)
- [SQLite BLOB](https://www.sqlite.org/datatype3.html)
- [dlib](http://dlib.net/) (underlying library)

---

## 📞 Support & Debugging

### Enable Debug Logging
Add to `app/face/matcher.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug(f"Face distance: {distance}, tolerance: {tolerance}")
```

### Check Face Cache Status
```python
from app.face.matcher import _face_cache
print(f"Cached faces: {_face_cache.get_active_count()}")
```

### Test Matching Locally
```python
import numpy as np
from app.face.matcher import match_face
# Load a test encoding from database
test_encoding = np.random.randn(128)  # Placeholder
result = match_face(test_encoding, tolerance=0.4)
print(result)
```

---

## ✅ Phase 2 Complete Checklist

- [ ] All Phase 1 prerequisites complete
- [ ] `matcher.py` created (face matching logic)
- [ ] Real-time attendance endpoints implemented
- [ ] Manual fallback form working
- [ ] Face attendance HTML templates created
- [ ] Face cache initialized on app startup
- [ ] Database stores/retrieves attendance correctly
- [ ] Tested with at least 2 registered employees
- [ ] Manual entry fallback tested
- [ ] Mobile device compatibility tested
- [ ] Error messages clear and helpful
- [ ] Security checks in place (access control, matching validation)

---

## 🎯 Next Steps (Phase 3)

Future enhancements:
- **Attendance Reports**: Dashboard with charts
- **Biometric Analytics**: Confidence scores, retry counts
- **Email Notifications**: Send payslip after payroll
- **API Integration**: Third-party time tracking systems
- **Liveness Detection**: Prevent face spoofing with photos
- **Multi-face Support**: Group check-in (family companies)

---

**Version:** Phase 2.0  
**Date:** June 15, 2026  
**Status:** ✅ Ready for Testing
