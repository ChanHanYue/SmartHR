"""
Face Registration Module
- Admin/HR captures employee faces
- Encodings stored in Face_Encoding table as encrypted BLOB (AES-256-GCM)
"""
import cv2
import numpy as np
import face_recognition
import base64
from io import BytesIO
from app.crypto_utils import encrypt_face_encoding, decrypt_face_encoding, is_encrypted
from datetime import datetime
from flask import render_template, request, jsonify, session, redirect, url_for
from app.face import face_bp
from app.database import get_db
from functools import wraps

# ─────────────────────────────────────────────────────────────────────────────
# DECORATORS
# ─────────────────────────────────────────────────────────────────────────────

def login_required(f):
    """Check if user is logged in"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    """Check if user has required role"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            
            conn = get_db()
            user = conn.execute(
                "SELECT role_id FROM Employee WHERE employee_id = ?",
                (session['user_id'],)
            ).fetchone()
            
            if not user:
                return redirect(url_for('auth.login'))
            
            # Get role name
            conn = get_db()
            role = conn.execute(
                "SELECT role_name FROM Role WHERE role_id = ?",
                (user['role_id'],)
            ).fetchone()
            
            if role['role_name'] not in roles:
                return jsonify({'success': False, 'msg': 'Access denied. Admin or HR role required.'}), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def encoding_to_blob(face_encoding):
    """Convert numpy array face encoding to BLOB (bytes)"""
    return face_encoding.astype(np.float64).tobytes()

def blob_to_encoding(blob):
    """Convert BLOB (bytes) back to numpy array face encoding"""
    return np.frombuffer(blob, dtype=np.float64)

def process_base64_image(image_data):
    """
    Decode base64 image to OpenCV format (BGR)
    
    Args:
        image_data: "data:image/png;base64,..." format string
    
    Returns:
        BGR image (numpy array) or None if decode fails
    """
    try:
        # Remove data URI prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        
        # Decode as image
        img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return img_bgr
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@face_bp.route('/register/<int:emp_id>', methods=['GET'])
@login_required
@role_required('Admin', 'HR')
def register_face_page(emp_id):
    """Show face registration page for an employee"""
    conn = get_db()
    
    # Get employee details
    employee = conn.execute(
        "SELECT employee_id, full_name, email FROM Employee WHERE employee_id = ?",
        (emp_id,)
    ).fetchone()
    
    # Check if face already registered
    existing = conn.execute(
        "SELECT face_encoding_blob FROM Face_Encoding WHERE employee_id = ?",
        (emp_id,)
    ).fetchone()
    
    conn.close()
    
    if not employee:
        return jsonify({'success': False, 'msg': 'Employee not found'}), 404
    
    return render_template('face/register_face.html', 
                          employee=employee,
                          already_registered=bool(existing))

@face_bp.route('/api/register', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def api_register_face():
    """
    Capture and register a face encoding
    
    Expected JSON:
    {
        "employee_id": 4,
        "image": "data:image/jpeg;base64,..." // from canvas.toDataURL()
    }
    """
    try:
        data = request.get_json()
        emp_id = data.get('employee_id')
        image_data = data.get('image')
        
        if not emp_id or not image_data:
            return jsonify({'success': False, 'msg': 'Missing employee_id or image'}), 400
        
        # Decode image
        img_bgr = process_base64_image(image_data)
        if img_bgr is None:
            return jsonify({'success': False, 'msg': 'Failed to decode image'}), 400
        
        # Convert BGR to RGB for face_recognition
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(img_rgb, model='hog')
        
        if len(face_locations) == 0:
            return jsonify({
                'success': False, 
                'msg': 'No face detected. Please ensure your face is clearly visible.'
            }), 400
        
        if len(face_locations) > 1:
            return jsonify({
                'success': False,
                'msg': f'Multiple faces detected ({len(face_locations)}). Please ensure only one person is in the frame.'
            }), 400
        
        # Extract face encoding
        face_encodings = face_recognition.face_encodings(img_rgb, face_locations)
        if not face_encodings:
            return jsonify({'success': False, 'msg': 'Could not extract face encoding'}), 400
        
        face_encoding = face_encodings[0]
        encoding_blob = encoding_to_blob(face_encoding)
        
        # Encrypt the encoding before storing
        encrypted_blob = encrypt_face_encoding(encoding_blob)
        
        # Store in database (upsert to handle re-registration)
        conn = get_db()
        
        # Verify employee exists
        emp_check = conn.execute(
            "SELECT employee_id FROM Employee WHERE employee_id = ?",
            (emp_id,)
        ).fetchone()
        
        if not emp_check:
            conn.close()
            return jsonify({'success': False, 'msg': 'Employee not found'}), 404
        
        # Check if already exists and update, or insert new
        existing = conn.execute(
            "SELECT face_encoding_id FROM Face_Encoding WHERE employee_id = ?",
            (emp_id,)
        ).fetchone()
        
        if existing:
            # Update existing
            conn.execute("""
                UPDATE Face_Encoding
                SET face_encoding_blob = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    registered_by = ?
                WHERE employee_id = ?
            """, (encrypted_blob, session['user_id'], emp_id))
            msg = 'Face updated successfully'
        else:
            # Insert new
            conn.execute("""
                INSERT INTO Face_Encoding (employee_id, face_encoding_blob, registered_by, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (emp_id, encrypted_blob, session['user_id']))
            msg = 'Face registered successfully'
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'msg': msg
        })
    
    except Exception as e:
        print(f"Face registration error: {e}")
        return jsonify({
            'success': False,
            'msg': f'Error: {str(e)}'
        }), 500

@face_bp.route('/api/status/<int:emp_id>', methods=['GET'])
@login_required
@role_required('Admin', 'HR')
def get_face_status(emp_id):
    """Check if employee has a registered face"""
    conn = get_db()
    
    face = conn.execute("""
        SELECT face_encoding_id, updated_at
        FROM Face_Encoding
        WHERE employee_id = ?
    """, (emp_id,)).fetchone()
    
    conn.close()
    
    if face:
        return jsonify({
            'has_face': True,
            'updated_at': face['updated_at']
        })
    else:
        return jsonify({'has_face': False})

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 2: REAL-TIME FACE ATTENDANCE
# ═════════════════════════════════════════════════════════════════════════════

@face_bp.route('/attendance', methods=['GET'])
@login_required
def face_attendance_page():
    """Show real-time face attendance page for logged-in employee"""
    emp_id = session.get('user_id')
    
    conn = get_db()
    employee = conn.execute(
        "SELECT employee_id, full_name, branch_id FROM Employee WHERE employee_id = ?",
        (emp_id,)
    ).fetchone()
    
    face_registered = conn.execute(
        "SELECT face_encoding_id FROM Face_Encoding WHERE employee_id = ?",
        (emp_id,)
    ).fetchone()
    
    conn.close()
    
    if not employee:
        return redirect(url_for('auth.login'))
    
    if not face_registered:
        return render_template('face/no_face_registered.html', employee=employee)
    
    return render_template('face/face_attendance.html', employee=employee)

@face_bp.route('/api/match_and_record', methods=['POST'])
@login_required
def api_match_and_record():
    """
    Real-time face matching and attendance recording
    
    Expected JSON:
    {
        "image": "data:image/jpeg;base64,..." // from webcam
    }
    
    Returns:
        - Match found: Record check-in/out, return attendance record
        - No match: Return error, show manual fallback option
    """
    from app.face.matcher import match_face, extract_face_encoding, refresh_face_cache
    
    try:
        data = request.get_json()
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'success': False, 'msg': 'No image provided'}), 400
        
        emp_id = session.get('user_id')
        
        # Decode image to RGB
        img_bgr = process_base64_image(image_data)
        if img_bgr is None:
            return jsonify({'success': False, 'msg': 'Failed to decode image'}), 400
        
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        
        # Extract face encoding
        face_encoding, face_count = extract_face_encoding(img_rgb)
        
        if face_encoding is None:
            if face_count == 0:
                return jsonify({
                    'success': False,
                    'msg': 'No face detected. Please position your face in the camera.'
                }), 400
            elif face_count > 1:
                return jsonify({
                    'success': False,
                    'msg': f'Multiple faces detected ({face_count}). Only you should be in frame.'
                }), 400
        
        # Refresh cache if first time
        refresh_face_cache()
        
        # Match against registered faces
        match_result = match_face(face_encoding, tolerance=0.4)  # Strict matching
        
        if not match_result['matched']:
            # Face not recognized - offer manual entry
            return jsonify({
                'success': False,
                'msg': match_result.get('error', 'Face not recognized'),
                'confidence': match_result.get('confidence', 0)
            }), 401
        
        # Verify matched employee is logged-in employee (security)
        if match_result['employee_id'] != emp_id:
            return jsonify({
                'success': False,
                'msg': 'Face does not match logged-in employee'
            }), 403
        
        # Record attendance (check-in or check-out)
        attendance_record = record_attendance(emp_id)
        
        if not attendance_record:
            return jsonify({'success': False, 'msg': 'Failed to record attendance'}), 500
        
        return jsonify({
            'success': True,
            'msg': attendance_record['msg'],
            'attendance': attendance_record,
            'confidence': match_result.get('confidence')
        })
    
    except Exception as e:
        print(f"Match and record error: {e}")
        return jsonify({
            'success': False,
            'msg': f'Error: {str(e)}'
        }), 500

def record_attendance(emp_id):
    """
    Record check-in or check-out for employee.
    
    Logic:
    - If no check-in today: Record check-in
    - If already checked in (no check-out): Record check-out
    - If already checked out: Can only re-check-in tomorrow
    """
    try:
        now = datetime.now()
        today = now.date()
        
        conn = get_db()
        
        # Get last attendance record for today
        last_record = conn.execute("""
            SELECT attendance_id, check_in, check_out
            FROM Attendance
            WHERE employee_id = ? AND date(check_in) = date(?)
            ORDER BY check_in DESC LIMIT 1
        """, (emp_id, now)).fetchone()
        
        if not last_record or last_record['check_out'] is not None:
            # New check-in (no previous record or already checked out)
            conn.execute("""
                INSERT INTO Attendance 
                (employee_id, branch_id, check_in, status, is_manual_entry)
                VALUES (?, (SELECT branch_id FROM Employee WHERE employee_id = ?), ?, 'Pending', 0)
            """, (emp_id, emp_id, now))
            conn.commit()
            conn.close()
            
            return {
                'action': 'check_in',
                'time': now.strftime('%H:%M:%S'),
                'msg': f'✅ Checked in at {now.strftime("%H:%M:%S")}'
            }
        else:
            # Check-out (already checked in, no check-out yet)
            check_in_dt = datetime.fromisoformat(last_record['check_in'])
            hours_worked = (now - check_in_dt).total_seconds() / 3600
            
            conn.execute("""
                UPDATE Attendance
                SET check_out = ?, hours_worked = ?, status = 'Pending'
                WHERE attendance_id = ?
            """, (now, round(hours_worked, 2), last_record['attendance_id']))
            conn.commit()
            conn.close()
            
            return {
                'action': 'check_out',
                'time': now.strftime('%H:%M:%S'),
                'hours_worked': round(hours_worked, 2),
                'msg': f'✅ Checked out at {now.strftime("%H:%M:%S")} ({round(hours_worked, 2)}h)'
            }
    
    except Exception as e:
        print(f"Error recording attendance: {e}")
        return None

@face_bp.route('/api/record_manual', methods=['POST'])
@login_required
def api_record_manual():
    """
    Manual attendance entry (fallback if face recognition fails)
    
    Expected JSON:
    {
        "check_in_time": "09:00",  // HH:MM format
        "check_out_time": "18:00", // HH:MM format (optional)
        "reason": "Face recognition failed"
    }
    """
    try:
        data = request.get_json()
        check_in_time = data.get('check_in_time')
        check_out_time = data.get('check_out_time')
        reason = data.get('reason', '')
        
        if not check_in_time:
            return jsonify({'success': False, 'msg': 'Check-in time required'}), 400
        
        emp_id = session.get('user_id')
        now = datetime.now()
        
        try:
            # Parse times
            check_in_parts = check_in_time.split(':')
            check_in_dt = now.replace(hour=int(check_in_parts[0]), minute=int(check_in_parts[1]), second=0)
            
            conn = get_db()
            
            # Check if manual entry already exists for today
            existing = conn.execute("""
                SELECT attendance_id FROM Attendance
                WHERE employee_id = ? AND date(check_in) = date(?)
                AND is_manual_entry = 1
            """, (emp_id, now)).fetchone()
            
            if existing:
                conn.close()
                return jsonify({'success': False, 'msg': 'Manual entry already exists for today'}), 400
            
            # Insert manual check-in
            conn.execute("""
                INSERT INTO Attendance
                (employee_id, branch_id, check_in, status, is_manual_entry)
                VALUES (?, (SELECT branch_id FROM Employee WHERE employee_id = ?), ?, 'Pending', 1)
            """, (emp_id, emp_id, check_in_dt))
            
            # If check-out provided, add hours
            if check_out_time:
                check_out_parts = check_out_time.split(':')
                check_out_dt = now.replace(hour=int(check_out_parts[0]), minute=int(check_out_parts[1]), second=0)
                hours_worked = (check_out_dt - check_in_dt).total_seconds() / 3600
                
                # Update the attendance record
                conn.execute("""
                    UPDATE Attendance
                    SET check_out = ?, hours_worked = ?
                    WHERE employee_id = ? AND date(check_in) = date(?)
                    AND is_manual_entry = 1
                """, (check_out_dt, round(hours_worked, 2), emp_id, now))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'msg': 'Manual entry recorded (pending HR approval)'
            })
        
        except ValueError:
            return jsonify({'success': False, 'msg': 'Invalid time format. Use HH:MM'}), 400
    
    except Exception as e:
        print(f"Manual entry error: {e}")
        return jsonify({'success': False, 'msg': f'Error: {str(e)}'}), 500

@face_bp.route('/api/today_attendance', methods=['GET'])
@login_required
def get_today_attendance():
    """Get today's attendance records for logged-in employee"""
    try:
        emp_id = session.get('user_id')
        now = datetime.now()
        today = now.date()
        
        conn = get_db()
        
        records = conn.execute("""
            SELECT check_in, check_out, hours_worked, status, is_manual_entry
            FROM Attendance
            WHERE employee_id = ? AND date(check_in) = ?
            ORDER BY check_in ASC
        """, (emp_id, today)).fetchall()
        
        conn.close()
        
        attendance_list = []
        for rec in records:
            check_in = datetime.fromisoformat(rec['check_in'])
            check_out = None
            if rec['check_out']:
                check_out = datetime.fromisoformat(rec['check_out'])
            
            attendance_list.append({
                'check_in': check_in.strftime('%H:%M:%S'),
                'check_out': check_out.strftime('%H:%M:%S') if check_out else 'Still logged in',
                'hours_worked': rec['hours_worked'],
                'status': rec['status'],
                'manual': rec['is_manual_entry'] == 1
            })
        
        return jsonify({
            'success': True,
            'date': today.isoformat(),
            'records': attendance_list
        })
    
    except Exception as e:
        print(f"Get attendance error: {e}")
        return jsonify({
            'success': False,
            'msg': f'Error: {str(e)}'
        }), 500
