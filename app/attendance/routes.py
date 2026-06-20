"""app/attendance/routes.py – Manual entry, biometric verification, and attendance logs"""
import datetime
import csv
import io
import base64
import numpy as np
from PIL import Image
from flask import (Blueprint, render_template, request, redirect,
                   url_for, session, flash, jsonify, make_response)
from app.database import query, execute, log_audit
from app.auth.routes import login_required, role_required
from app.crypto_utils import decrypt_face_encoding, is_encrypted

att_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

FACE_TOLERANCE = 0.5
VERIFY_THRESHOLD = 55  # aligned with compare_faces tolerance (distance <= 0.5 → confidence >= 50%)


def _import_face_recognition():
    try:
        import face_recognition
        return face_recognition
    except Exception:
        return None


def _decode_image(image_b64):
    """Decode a base64 data-URL image into an RGB numpy array."""
    header, encoded = image_b64.split(',', 1)
    image_data = base64.b64decode(encoded)
    img = Image.open(io.BytesIO(image_data))
    return np.array(img.convert('RGB'))


def _get_stored_encoding(employee_id):
    stored = query(
        "SELECT face_encoding_blob FROM Face_Encoding WHERE employee_id=?",
        (employee_id,), one=True)
    if not stored:
        return None
    
    # Decrypt the stored encoding
    encrypted_blob = stored['face_encoding_blob']
    try:
        if is_encrypted(encrypted_blob):
            # It's encrypted (string)
            decrypted_bytes = decrypt_face_encoding(encrypted_blob)
        else:
            # Fallback for unencrypted legacy data (bytes)
            decrypted_bytes = encrypted_blob
        return np.frombuffer(decrypted_bytes, dtype=np.float64)
    except Exception as e:
        print(f"Error decrypting face encoding for employee {employee_id}: {e}")
        return None


def _verify_face_for_user(img_np, employee_id):
    """
    Verify webcam face against the logged-in employee only.
    If it does not match, detect whether another registered employee's face was used.
    Returns dict: matched, confidence, error, wrong_person, wrong_person_name
    """
    fr = _import_face_recognition()
    if not fr:
        return {
            'matched': False, 'confidence': 0,
            'error': 'Face recognition module is not properly installed on the server.',
        }

    encodings = fr.face_encodings(img_np)
    if not encodings:
        return {
            'matched': False, 'confidence': 0,
            'error': 'No face detected. Please position your face in the frame.',
        }

    live_encoding = encodings[0]
    stored_encoding = _get_stored_encoding(employee_id)
    if stored_encoding is None:
        return {
            'matched': False, 'confidence': 0, 'registered': False,
            'error': 'Face not registered. Please register your face first.',
        }

    distance = fr.face_distance([stored_encoding], live_encoding)[0]
    confidence = round((1 - distance) * 100, 2)
    matched = fr.compare_faces([stored_encoding], live_encoding, tolerance=FACE_TOLERANCE)[0]

    if matched:
        return {'matched': True, 'confidence': confidence, 'error': None}

    # Reject if the scanned face matches a different registered employee
    others = query("""
        SELECT f.employee_id, e.full_name, f.face_encoding_blob
        FROM Face_Encoding f
        JOIN Employee e ON f.employee_id = e.employee_id
        WHERE f.employee_id != ? AND e.is_active = 1
    """, (employee_id,))

    for row in others:
        try:
            # Decrypt the stored encoding
            encrypted_blob = row['face_encoding_blob']
            if is_encrypted(encrypted_blob):
                decrypted_bytes = decrypt_face_encoding(encrypted_blob)
            else:
                decrypted_bytes = encrypted_blob
            other_encoding = np.frombuffer(decrypted_bytes, dtype=np.float64)
        except Exception as e:
            print(f"Error decrypting face for employee {row['employee_id']}: {e}")
            continue
        
        if fr.compare_faces([other_encoding], live_encoding, tolerance=FACE_TOLERANCE)[0]:
            return {
                'matched': False,
                'confidence': confidence,
                'wrong_person': True,
                'wrong_person_id': row['employee_id'],
                'wrong_person_name': row['full_name'],
                'error': (
                    f'This face belongs to {row["full_name"]}. '
                    'You can only check in with your own registered face.'
                ),
            }

    return {
        'matched': False,
        'confidence': confidence,
        'error': (
            f'Face does not match your registered profile (confidence: {confidence}%). '
            'Only your own face can be used for attendance.'
        ),
    }


def _face_already_registered_to_other(img_np, employee_id):
    """Block registering a face that belongs to another employee."""
    fr = _import_face_recognition()
    if not fr:
        return None

    encodings = fr.face_encodings(img_np)
    if not encodings:
        return None

    live_encoding = encodings[0]
    others = query("""
        SELECT f.employee_id, e.full_name, f.face_encoding_blob
        FROM Face_Encoding f
        JOIN Employee e ON f.employee_id = e.employee_id
        WHERE f.employee_id != ? AND e.is_active = 1
    """, (employee_id,))

    for row in others:
        try:
            # Decrypt the stored encoding
            encrypted_blob = row['face_encoding_blob']
            if is_encrypted(encrypted_blob):
                decrypted_bytes = decrypt_face_encoding(encrypted_blob)
            else:
                decrypted_bytes = encrypted_blob
            other_encoding = np.frombuffer(decrypted_bytes, dtype=np.float64)
        except Exception as e:
            print(f"Error decrypting face for employee {row['employee_id']}: {e}")
            continue
        
        if fr.compare_faces([other_encoding], live_encoding, tolerance=FACE_TOLERANCE)[0]:
            return row['full_name']
    return None


def _today_open_checkin(employee_id):
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    return query("""
        SELECT * FROM Attendance
        WHERE employee_id=? AND date(check_in)=? AND check_out IS NULL
        ORDER BY check_in DESC LIMIT 1
    """, (employee_id, today), one=True)


def _increment_checkin_failures():
    count = session.get('biometric_checkin_failures', 0) + 1
    session['biometric_checkin_failures'] = count
    return count


def _reset_checkin_failures():
    session['biometric_checkin_failures'] = 0
    return 0


def _failure_payload(action, count):
    """Extra JSON fields when biometric check-in fails."""
    if action != 'check_in':
        return {}
    return {
        'failed_attempts': count,
        'max_attempts': 3,
        'show_manual_fallback': count >= 3,
    }


def _has_checkin_today(employee_id):
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    return query("""
        SELECT attendance_id FROM Attendance
        WHERE employee_id=? AND date(check_in)=?
        ORDER BY check_in DESC LIMIT 1
    """, (employee_id, today), one=True)


@att_bp.route('/')
@login_required
def time_tracking():
    uid  = session['user_id']
    role = session['user_role']
    co   = session['company_id']

    # Personal records for the current week
    my_records = query("""
        SELECT a.*, b.name as branch_name FROM Attendance a
        JOIN Branch b ON a.branch_id=b.branch_id
        WHERE a.employee_id=?
        ORDER BY a.check_in DESC LIMIT 14
    """, (uid,))

    # Team overview (HR/Manager/Admin sees all, Manager restricted to branch)
    team = None
    if role in ('Admin', 'HR', 'Manager'):
        if role == 'Manager':
            team = query("""
                SELECT e.full_name, e.position, d.department_name,
                       SUM(CASE WHEN date(a.check_in)=date('now') THEN 1 ELSE 0 END) as present_today,
                       SUM(a.hours_worked) as total_hours,
                       SUM(a.overtime_hours) as total_ot,
                       MAX(a.status) as status
                FROM Employee e
                LEFT JOIN Attendance a ON e.employee_id=a.employee_id
                    AND date(a.check_in) >= date('now','-6 days')
                JOIN Department d ON e.department_id=d.department_id
                WHERE e.company_id=? AND e.branch_id=? AND e.is_active=1
                GROUP BY e.employee_id
                ORDER BY e.full_name
            """, (co, session['branch_id']))
        else:
            team = query("""
                SELECT e.full_name, e.position, d.department_name,
                       SUM(CASE WHEN date(a.check_in)=date('now') THEN 1 ELSE 0 END) as present_today,
                       SUM(a.hours_worked) as total_hours,
                       SUM(a.overtime_hours) as total_ot,
                       MAX(a.status) as status
                FROM Employee e
                LEFT JOIN Attendance a ON e.employee_id=a.employee_id
                    AND date(a.check_in) >= date('now','-6 days')
                JOIN Department d ON e.department_id=d.department_id
                WHERE e.company_id=? AND e.is_active=1
                GROUP BY e.employee_id
                ORDER BY e.full_name
            """, (co,))

    # Summary stats
    this_week = query("""
        SELECT SUM(hours_worked) as hrs, SUM(overtime_hours) as ot
        FROM Attendance
        WHERE employee_id=? AND date(check_in) >= date('now','-6 days')
    """, (uid,), one=True)

    return render_template('attendance/time_tracking.html',
                           my_records=my_records, team=team, this_week=this_week)


@att_bp.route('/manual', methods=['GET', 'POST'])
@role_required('Admin', 'HR')
def manual():
    co = session['company_id']
    uid = session['user_id']
    employees = query("SELECT employee_id, full_name, position FROM Employee WHERE company_id=? AND is_active=1 ORDER BY full_name", (co,))
    branches  = query("SELECT * FROM Branch WHERE company_id=?", (co,))

    if request.method == 'POST':
        f         = request.form
        emp_id    = int(f['employee_id'])
        att_date  = f['att_date']
        att_time  = f['att_time']
        att_type  = f['att_type']   # 'Check In' or 'Check Out'
        reason    = f.get('reason', '').strip()
        branch_id = int(f.get('branch_id', session['branch_id']))

        # Server-side validation: reason is mandatory
        if not reason:
            flash('Override reason is mandatory. Please select a reason.', 'danger')
            return redirect(url_for('attendance.manual'))

        dt_str = f"{att_date} {att_time}:00"

        if att_type == 'Check In':
            aid = execute("""
                INSERT INTO Attendance
                (employee_id, branch_id, check_in, is_manual_entry, manual_reason,
                 corrected_by, corrected_at, status)
                VALUES(?,?,?,1,?,?,datetime('now'),'Approved')
            """, (emp_id, branch_id, dt_str, reason, uid))
            log_audit('MANUAL_CHECKIN', 'Attendance',
                      f'Manual check-in for employee_id={emp_id}',
                      'Attendance', aid, 'Success', {'datetime': dt_str, 'reason': reason})
            flash('Manual check-in recorded.', 'success')

        elif att_type == 'Check Out':
            # Find latest open check-in
            open_att = query("""
                SELECT * FROM Attendance
                WHERE employee_id=? AND date(check_in)=? AND check_out IS NULL
                ORDER BY check_in DESC LIMIT 1
            """, (emp_id, att_date), one=True)

            if not open_att:
                flash('No open check-in found for this employee on that date.', 'danger')
                return redirect(url_for('attendance.manual'))

            ci = datetime.datetime.fromisoformat(open_att['check_in'])
            co_dt = datetime.datetime.fromisoformat(dt_str)
            diff_h = round((co_dt - ci).total_seconds() / 3600, 2)
            ot = round(max(0, diff_h - 8), 2)

            execute("""
                UPDATE Attendance SET check_out=?, hours_worked=?, overtime_hours=?,
                       corrected_by=?, corrected_at=datetime('now'), is_manual_entry=1,
                       manual_reason=?, status='Approved'
                WHERE attendance_id=?
            """, (dt_str, diff_h, ot, uid, reason, open_att['attendance_id']))
            log_audit('MANUAL_CHECKOUT', 'Attendance',
                      f'Manual check-out for employee_id={emp_id}',
                      'Attendance', open_att['attendance_id'], 'Success',
                      {'datetime': dt_str, 'hours': diff_h})
            flash(f'Manual check-out recorded. Hours: {diff_h}h.', 'success')

        return redirect(url_for('attendance.manual'))

    recent = query("""
        SELECT a.*, e.full_name, b.name as branch_name
        FROM Attendance a
        JOIN Employee e ON a.employee_id=e.employee_id
        JOIN Branch b ON a.branch_id=b.branch_id
        WHERE e.company_id=? AND a.is_manual_entry=1
        ORDER BY a.created_at DESC LIMIT 20
    """, (co,))

    return render_template('attendance/manual.html',
                           employees=employees, branches=branches, recent=recent)


@att_bp.route('/biometric')
@login_required
def biometric():
    """Page for face recognition."""
    uid = session['user_id']
    open_att = _today_open_checkin(uid)
    return render_template('attendance/biometric.html',
                           can_check_in=open_att is None,
                           can_check_out=open_att is not None,
                           face_registered=_get_stored_encoding(uid) is not None,
                           failed_attempts=session.get('biometric_checkin_failures', 0),
                           can_manual_override=session.get('user_role') in ('Admin', 'HR'))


@att_bp.route('/status')
@login_required
def attendance_status():
    """Return current check-in/out eligibility without face verification."""
    uid = session['user_id']
    open_att = _today_open_checkin(uid)
    return jsonify({
        'can_check_in': open_att is None,
        'can_check_out': open_att is not None,
        'face_registered': _get_stored_encoding(uid) is not None,
        'open_check_in': open_att['check_in'] if open_att else None,
    })


@att_bp.route('/register_face', methods=['POST'])
@login_required
def register_face():
    if not _import_face_recognition():
        return jsonify({'error': 'Face recognition module is not properly installed on the server.'}), 503
    uid = session['user_id']
    data = request.json
    if not data or 'image' not in data:
        return jsonify({'error': 'No image data'}), 400

    try:
        img_np = _decode_image(data['image'])
        fr = _import_face_recognition()
        encodings = fr.face_encodings(img_np)
        if not encodings:
            return jsonify({'error': 'No face detected. Please try again.'}), 400

        other_name = _face_already_registered_to_other(img_np, uid)
        if other_name:
            log_audit('REGISTER_FACE', 'Attendance',
                      f'Blocked: face already registered to {other_name}',
                      'Employee', uid, 'Failed', {'other_employee': other_name})
            return jsonify({
                'error': f'This face is already registered to {other_name}. Each employee must use their own face.'
            }), 403

        encoding_blob = encodings[0].tobytes()
        existing = query("SELECT encoding_id FROM Face_Encoding WHERE employee_id=?", (uid,), one=True)
        if existing:
            execute("UPDATE Face_Encoding SET face_encoding_blob=?, updated_at=datetime('now') WHERE employee_id=?",
                    (encoding_blob, uid))
        else:
            execute("INSERT INTO Face_Encoding (employee_id, face_encoding_blob, registered_by) VALUES (?,?,?)",
                    (uid, encoding_blob, uid))

        log_audit('REGISTER_FACE', 'Attendance', 'Registered face biometric', 'Employee', uid)
        return jsonify({'success': True, 'message': 'Face registered successfully!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@att_bp.route('/preview_verify', methods=['POST'])
@login_required
def preview_verify():
    """Real-time face verification preview — no attendance recorded."""
    uid = session['user_id']
    data = request.json
    if not data or 'image' not in data:
        return jsonify({'error': 'No image data'}), 400

    stored_encoding = _get_stored_encoding(uid)
    if stored_encoding is None:
        return jsonify({
            'registered': False,
            'face_detected': False,
            'matched': False,
            'confidence': 0,
            'message': 'Face not registered. Please register your face first.'
        })

    try:
        img_np = _decode_image(data['image'])
        result = _verify_face_for_user(img_np, uid)
        open_att = _today_open_checkin(uid)

        face_detected = result.get('error') != 'No face detected. Please position your face in the frame.'

        if result.get('error') and not result.get('matched'):
            payload = {
                'registered': True,
                'face_detected': face_detected,
                'matched': False,
                'confidence': result.get('confidence', 0),
                'can_check_in': open_att is None,
                'can_check_out': open_att is not None,
                'wrong_person': result.get('wrong_person', False),
                'message': result['error'],
            }
            return jsonify(payload)

        return jsonify({
            'registered': True,
            'face_detected': True,
            'matched': result['matched'],
            'confidence': result['confidence'],
            'threshold': VERIFY_THRESHOLD,
            'can_check_in': open_att is None,
            'can_check_out': open_att is not None,
            'message': f'Verified ({result["confidence"]}%)' if result['matched'] else result.get('error', 'Face mismatch'),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@att_bp.route('/verify_face', methods=['POST'])
@login_required
def verify_face():
    if not _import_face_recognition():
        return jsonify({'error': 'Face recognition module is not properly installed on the server.'}), 503
    uid = session['user_id']
    data = request.json
    action = data.get('action')

    if not data or 'image' not in data or not action:
        return jsonify({'error': 'Invalid request'}), 400

    stored_encoding = _get_stored_encoding(uid)
    if stored_encoding is None:
        return jsonify({'error': 'Face not registered. Please register your face first.'}), 400

    try:
        img_np = _decode_image(data['image'])
        result = _verify_face_for_user(img_np, uid)

        if result.get('error') and not result.get('matched'):
            details = {'action': action, 'confidence': result.get('confidence', 0)}
            if result.get('wrong_person'):
                details['wrong_person_id'] = result.get('wrong_person_id')
                details['wrong_person_name'] = result.get('wrong_person_name')
                log_audit('BIOMETRIC_WRONG_PERSON', 'Attendance', result['error'],
                          'Employee', uid, 'Failed', details)
                return jsonify({'error': result['error'], 'wrong_person': True}), 403

            if action == 'check_in':
                count = _increment_checkin_failures()
                details['attempt'] = count
                details['reason'] = 'no_face' if not result.get('confidence') else 'mismatch'
            log_audit('BIOMETRIC_VERIFY_FAILED', 'Attendance', result['error'],
                      'Employee', uid, 'Failed', details)
            return jsonify({
                'error': result['error'],
                **_failure_payload(action, session.get('biometric_checkin_failures', 0)),
            }), 400 if 'No face detected' in result['error'] else 401

        confidence = result['confidence']
        bid = session['branch_id']
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        if action == 'check_in':
            if _today_open_checkin(uid):
                return jsonify({'error': 'You are already checked in. Use Check Out instead.'}), 400

            aid = execute("""
                INSERT INTO Attendance (employee_id, branch_id, check_in, confidence_score, status)
                VALUES (?,?,?,?,'Approved')
            """, (uid, bid, now, confidence))
            _reset_checkin_failures()
            msg = f"Check-in successful! Confidence: {confidence}%"
            log_audit('BIOMETRIC_CHECKIN', 'Attendance', 'Face verified check-in',
                      'Attendance', aid, 'Success', {'confidence': confidence})
        else:
            open_att = _today_open_checkin(uid)
            if not open_att:
                return jsonify({'error': 'No open check-in found for today.'}), 400

            ci = datetime.datetime.fromisoformat(open_att['check_in'])
            co_dt = datetime.datetime.now()
            diff_h = round((co_dt - ci).total_seconds() / 3600, 2)
            ot = round(max(0, diff_h - 8), 2)

            execute("""
                UPDATE Attendance SET check_out=?, hours_worked=?, overtime_hours=?,
                       confidence_score=?, status='Approved'
                WHERE attendance_id=?
            """, (now, diff_h, ot, confidence, open_att['attendance_id']))
            msg = f"Check-out successful! Hours: {diff_h}h. Confidence: {confidence}%"
            log_audit('BIOMETRIC_CHECKOUT', 'Attendance', 'Face verified check-out',
                      'Attendance', open_att['attendance_id'], 'Success', {'confidence': confidence})

        return jsonify({'success': True, 'message': msg, 'confidence': confidence})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@att_bp.route('/manual_self', methods=['POST'])
@login_required
def manual_self():
    """Employee self-service manual check-in after biometric failures."""
    uid = session['user_id']
    bid = session['branch_id']
    data = request.json or {}
    reason = data.get('reason', 'Biometric failed (3 attempts)').strip()
    att_time = data.get('time')  # optional HH:MM

    # Validate reason is provided and not empty
    if not reason:
        return jsonify({'error': 'Manual entry reason is required.'}), 400

    if session.get('biometric_checkin_failures', 0) < 3:
        return jsonify({'error': 'Manual entry is available after 3 failed biometric attempts.'}), 403

    if _today_open_checkin(uid):
        return jsonify({'error': 'You are already checked in today.'}), 400

    now = datetime.datetime.now()
    if att_time:
        try:
            parts = att_time.split(':')
            now = now.replace(hour=int(parts[0]), minute=int(parts[1]), second=0, microsecond=0)
        except (ValueError, IndexError):
            return jsonify({'error': 'Invalid time format. Use HH:MM'}), 400

    dt_str = now.strftime('%Y-%m-%d %H:%M:%S')
    aid = execute("""
        INSERT INTO Attendance
        (employee_id, branch_id, check_in, is_manual_entry, manual_reason, status)
        VALUES (?,?,?,1,?,'Pending')
    """, (uid, bid, dt_str, reason))

    _reset_checkin_failures()
    log_audit('MANUAL_CHECKIN', 'Attendance',
              'Self-service manual check-in after biometric failure',
              'Attendance', aid, 'Success',
              {'datetime': dt_str, 'reason': reason, 'self_service': True})

    return jsonify({
        'success': True,
        'message': f'Manual check-in recorded at {dt_str[11:16]} (pending approval).',
    })


@att_bp.route('/logs')
@login_required
def attendance_logs():
    """View filterable attendance logs."""
    co = session['company_id']
    uid = session['user_id']
    role = session['user_role']

    date_from = request.args.get('from', datetime.date.today().replace(day=1).isoformat())
    date_to = request.args.get('to', datetime.date.today().isoformat())
    emp_filter = request.args.get('employee', '')
    method = request.args.get('method', '')
    branch = request.args.get('branch', '')
    export = request.args.get('export')

    employees = []
    branches = []
    if role in ('Admin', 'HR', 'Manager'):
        if role == 'Manager':
            employees = query(
                "SELECT employee_id, full_name FROM Employee WHERE company_id=? AND branch_id=? AND is_active=1 ORDER BY full_name",
                (co, session['branch_id']))
            branches = query("SELECT branch_id, name FROM Branch WHERE company_id=? AND branch_id=? ORDER BY name", (co, session['branch_id']))
        else:
            employees = query(
                "SELECT employee_id, full_name FROM Employee WHERE company_id=? AND is_active=1 ORDER BY full_name",
                (co,))
            branches = query("SELECT branch_id, name FROM Branch WHERE company_id=? ORDER BY name", (co,))

    sql = """
        SELECT a.*, e.full_name, d.department_name, b.name as branch_name,
               CASE WHEN a.is_manual_entry=1 THEN 'Manual' ELSE 'Biometric' END as entry_method
        FROM Attendance a
        JOIN Employee e ON a.employee_id=e.employee_id
        JOIN Department d ON e.department_id=d.department_id
        JOIN Branch b ON a.branch_id=b.branch_id
        WHERE e.company_id=?
          AND date(a.check_in) >= ? AND date(a.check_in) <= ?
    """
    args = [co, date_from, date_to]

    if role == 'Manager':
        sql += " AND e.branch_id=?"
        args.append(session['branch_id'])
    elif role not in ('Admin', 'HR'):
        sql += " AND a.employee_id=?"
        args.append(uid)

    if emp_filter:
        sql += " AND a.employee_id=?"
        args.append(int(emp_filter))

    if method == 'manual':
        sql += " AND a.is_manual_entry=1"
    elif method == 'biometric':
        sql += " AND a.is_manual_entry=0"

    if branch:
        sql += " AND a.branch_id=?"
        args.append(int(branch))

    sql += " ORDER BY a.check_in DESC LIMIT 500"
    logs = query(sql, args)

    if export == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Employee', 'Department', 'Branch', 'Check In', 'Check Out',
                         'Hours', 'OT Hours', 'Method', 'Confidence', 'Status'])
        for row in logs:
            writer.writerow([
                row['full_name'], row['department_name'], row['branch_name'],
                row['check_in'], row['check_out'] or '',
                row['hours_worked'] or '', row['overtime_hours'] or '',
                row['entry_method'],
                f"{row['confidence_score']:.1f}%" if row['confidence_score'] else '',
                row['status']
            ])
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=attendance_logs_{date_from}_{date_to}.csv'
        response.headers['Content-type'] = 'text/csv'
        return response

    if role == 'Manager':
        summary = query("""
            SELECT COUNT(*) as total_records,
                   SUM(CASE WHEN a.is_manual_entry=0 THEN 1 ELSE 0 END) as biometric_count,
                   SUM(CASE WHEN a.is_manual_entry=1 THEN 1 ELSE 0 END) as manual_count,
                   ROUND(AVG(a.confidence_score), 1) as avg_confidence,
                   ROUND(SUM(a.hours_worked), 1) as total_hours
            FROM Attendance a
            JOIN Employee e ON a.employee_id=e.employee_id
            WHERE e.company_id=? AND e.branch_id=?
              AND date(a.check_in) >= ? AND date(a.check_in) <= ?
        """, (co, session['branch_id'], date_from, date_to), one=True)
    elif role in ('Admin', 'HR'):
        summary = query("""
            SELECT COUNT(*) as total_records,
                   SUM(CASE WHEN a.is_manual_entry=0 THEN 1 ELSE 0 END) as biometric_count,
                   SUM(CASE WHEN a.is_manual_entry=1 THEN 1 ELSE 0 END) as manual_count,
                   ROUND(AVG(a.confidence_score), 1) as avg_confidence,
                   ROUND(SUM(a.hours_worked), 1) as total_hours
            FROM Attendance a
            JOIN Employee e ON a.employee_id=e.employee_id
            WHERE e.company_id=?
              AND date(a.check_in) >= ? AND date(a.check_in) <= ?
        """, (co, date_from, date_to), one=True)
    else:
        summary = query("""
            SELECT COUNT(*) as total_records,
                   SUM(CASE WHEN a.is_manual_entry=0 THEN 1 ELSE 0 END) as biometric_count,
                   SUM(CASE WHEN a.is_manual_entry=1 THEN 1 ELSE 0 END) as manual_count,
                   ROUND(AVG(a.confidence_score), 1) as avg_confidence,
                   ROUND(SUM(a.hours_worked), 1) as total_hours
            FROM Attendance a
            JOIN Employee e ON a.employee_id=e.employee_id
            WHERE e.company_id=? AND a.employee_id=?
              AND date(a.check_in) >= ? AND date(a.check_in) <= ?
        """, (co, uid, date_from, date_to), one=True)

    return render_template('attendance/logs.html',
                           logs=logs, summary=summary,
                           employees=employees, branches=branches,
                           date_from=date_from, date_to=date_to,
                           emp_filter=emp_filter, method=method, branch=branch)
