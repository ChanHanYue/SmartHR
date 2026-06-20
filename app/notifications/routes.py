from flask import Blueprint, jsonify, session, request
from app.database import query, execute, log_audit
from app.auth.routes import login_required

notif_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notif_bp.route('/')
@login_required
def index():
    uid = session['user_id']
    notifs = query("""
        SELECT * FROM Notification
        WHERE employee_id = ?
        ORDER BY created_at DESC
        LIMIT 20
    """, (uid,))
    return jsonify(notifs)

@notif_bp.route('/unread-count')
@login_required
def unread_count():
    uid = session['user_id']
    count = query("""
        SELECT COUNT(*) as cnt FROM Notification
        WHERE employee_id = ? AND is_read = 0
    """, (uid,), one=True)
    return jsonify({"count": count['cnt']})

@notif_bp.route('/mark-read/<int:notif_id>', methods=['POST'])
@login_required
def mark_read(notif_id):
    uid = session['user_id']
    execute("""
        UPDATE Notification
        SET is_read = 1
        WHERE notification_id = ? AND employee_id = ?
    """, (notif_id, uid))
    log_audit('MARK_NOTIF_READ', 'Notifications', f"Marked notification {notif_id} as read")
    return jsonify({"success": True})

@notif_bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    uid = session['user_id']
    execute("""
        UPDATE Notification
        SET is_read = 1
        WHERE employee_id = ? AND is_read = 0
    """, (uid,))
    log_audit('MARK_ALL_NOTIFS_READ', 'Notifications', "Marked all notifications as read")
    return jsonify({"success": True})

def send_notification(employee_id, title, message, type='Info', related_url=None, extra_context=None):
    """Helper function to send a notification to an employee (in-app + email)"""
    execute("""
        INSERT INTO Notification (employee_id, title, message, type, related_url)
        VALUES (?, ?, ?, ?, ?)
    """, (employee_id, title, message, type, related_url))
    try:
        from app.notifications.email_service import send_email_notification
        send_email_notification(employee_id, title, message, extra_context)
    except Exception as e:
        print(f"[EMAIL] Failed to send email notification: {e}")
