# SmartHR – AI-Powered HR Management System
## READ ME — Developer Reference

---

## 🚀 Quick Start (Automated)

1.  **Run Setup**: Double-click `Setup_SmartHR.bat`. (Installs libraries + initializes DB)
2.  **Launch Server**: Double-click `Start_SmartHR.bat`.
3.  **Access**: Visit the URL shown in the console (e.g., `http://192.168.x.x:5000`).

---

## 🔑 Default Login Credentials

| Role | Email | Password |
|------|-------|----------|
| System Admin | admin@smarthr.my | Admin@123 |
| HR Director | hr@smarthr.my | Hr@123 |
| Manager (KL) | brian@smarthr.my | Manager@123 |
| Manager (PG) | hafiz@smarthr.my | Manager@123 |
| Employee | elizabeth@smarthr.my | Employee@123 |
| Employee | ryan@smarthr.my | Employee@123 |
| Employee | nurul@smarthr.my | Employee@123 |
| Employee | priya@smarthr.my | Employee@123 |

> ⚠️ **Change all passwords before any production use!**

---

## 📁 Project Structure

```
smarthr_app/
├── app/
│   ├── __init__.py          # Flask app factory – registers all blueprints
│   ├── database.py          # SQLite helpers (get_db, query, execute, log_audit)
│   ├── auth/routes.py       # Login, logout, login_required, role_required + password reset
│   ├── main/routes.py       # Dashboard
│   ├── employees/routes.py  # Employee CRUD
│   ├── organization/routes.py  # Company/Branch/Department
│   ├── leave/routes.py      # Apply + approve/reject leave
│   ├── attendance/routes.py # Manual entry + time tracking + biometric face recog
│   ├── invoice/routes.py    # Upload, list, approve/reject
│   ├── payroll/routes.py    # List payroll + payslip view
│   ├── reports/routes.py    # Analytics and reports
│   ├── audit/routes.py      # Audit log viewer
│   ├── settings/routes.py   # Profile + password change
│   ├── notifications/
│   │   ├── routes.py        # In-app notification CRUD + send_notification helper
│   │   └── email_service.py # Email sending via Flask-Mail (multipart templates)
│   └── face/routes.py       # Face recognition attendance
├── docs/                    # Development guides and setup instructions
├── templates/
│   ├── *.html               # All Jinja2 page templates
│   └── emails/              # Email notification HTML templates (9 templates)
├── static/css/style.css     # Main stylesheet (green + dark SmartHR design)
├── uploads/                 # Invoice file uploads (gitignored)
├── instance/smarthr.db      # SQLite database (auto-created by init_db.py)
├── schema.sql               # SQLite schema (converted from MySQL hr_system_erd_v3.sql)
├── init_db.py               # DB init + Malaysian demo data seeder
├── run.py                   # Entry point (loads .env via python-dotenv)
├── requirements.txt         # Python dependencies
├── .env                     # Mail config (gitignored) — MAIL_USERNAME, MAIL_PASSWORD, etc.
├── .gitignore               # Excludes .env, __pycache__, instance/, uploads/
├── Setup_SmartHR.bat        # One-click setup script
└── Start_SmartHR.bat        # One-click launch script
```

---

## 🛠 Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.x |
| Framework | Flask | 3.x |
| Auth | Werkzeug | (included with Flask) |
| Database | SQLite | (stdlib) |
| Frontend | Jinja2 + Vanilla CSS/JS | — |
| OCR *(Sprint 2)* | Tesseract + pytesseract + PyPDF2 | — |
| Face Recog *(Sprint 2)* | OpenCV + face_recognition | — |

---

## 🗄 Database

- **Location:** `smarthr_app/instance/smarthr.db`
- **Backup:** Simply copy the `.db` file
- **Reset:** Delete `smarthr.db` and re-run `python init_db.py`
- **Schema file:** `schema.sql` (SQLite-compatible, 17 tables)

### Key Tables

| Table | Purpose |
|-------|---------|
| Employee | Users + auth credentials + employment info |
| Role | Admin / HR / Manager / Employee |
| Company / Branch / Department | Org structure |
| Attendance | Check-in/out records + manual overrides |
| Leave_Application | Leave requests |
| Leave_Balance | Remaining days per employee per year |
| Invoice | Expense invoice submissions |
| OCR_Result | Tesseract OCR output *(Sprint 2)* |
| Payroll | Monthly payroll records with EPF/SOCSO/EIS |
| AuditLog | All system actions logged here |

---

## 🔐 Role-Based Access

| Feature | Admin | HR | Manager | Employee |
|---------|-------|----|---------|---------|
| Dashboard | ✅ | ✅ | ✅ | ✅ |
| Employee CRUD | ✅ | ✅ | ❌ | ❌ |
| View own profile | ✅ | ✅ | ✅ | ✅ |
| Leave apply | ✅ | ✅ | ✅ | ✅ |
| Leave approve | ✅ | ✅ | ✅ | ❌ |
| Manual attendance | ✅ | ✅ | ❌ | ❌ |
| Invoice upload | ✅ | ✅ | ✅ | ✅ |
| Invoice approve | ✅ | ✅ | ✅ | ❌ |
| Payroll view | ✅ | ✅ | ❌ | Own only |
| Reports | ✅ | ✅ | ✅ | ❌ |
| Audit log | ✅ | ✅ | ❌ | ❌ |
| Org management | ✅ | ✅ | ❌ | ❌ |
| User deactivate | ✅ | ✅ | ❌ | ❌ |

---

## ✅ Sprint 1 Status (Completed)

| Module | Status | Notes |
|--------|--------|-------|
| Project Structure | ✅ Done | Flask app factory, blueprints |
| SQLite Schema | ✅ Done | Converted from hr_system_erd_v3.sql |
| Demo Data | ✅ Done | 10 Malaysian employees, leave, payroll, invoices |
| Login / Logout | ✅ Done | Session-based, account lock after 5 attempts |
| Dashboard | ✅ Done | Live metrics from DB |
| Employee CRUD | ✅ Done | List, add, view, edit, deactivate |
| Organization Mgmt | ✅ Done | Company, Branch, Department |
| Leave Apply | ✅ Done | Working-day calc, balance check |
| Leave Approve/Reject | ✅ Done | Balance auto-update |
| Manual Attendance | ✅ Done | Audit logged |
| Time Tracking | ✅ Done | Weekly summary, team overview |
| Invoice Upload | ✅ Done | File upload + metadata form |
| Invoice Approve/Reject | ✅ Done | With reason |
| Invoice OCR (Sprint 2) | ✅ Done | AI extraction for Images & PDFs |

### Advanced OCR Features:
- **Scoring Engine**: Multi-stage ranking system that prioritizes Invoice/Receipt IDs over Order numbers.
- **Vendor Learning**: Automatically learns preferred categories based on user corrections.
- **Malaysian Anchors**: High-priority detection for SDN BHD, SSM, and SST registration numbers.

| Payroll View | ✅ Done | Payslip with EPF/SOCSO/EIS breakdown |
| Reports | ✅ Done | Headcount, Attendance, Leave, Invoice, Payroll |
| Audit Log | ✅ Done | Paginated, filterable, modal details |
| Settings / Profile | ✅ Done | Edit profile + change password |
| READ_ME.md | ✅ Done | This file |

---

## ✅ Sprint 2 Status (Completed)

| Module | Status | Notes |
|--------|--------|-------|
| Automated Deployment | ✅ Done | One-click `.bat` scripts for Setup & Launch |
| Invoice OCR | ✅ Done | Supports PDF & Images with Scoring Engine |
| Malaysian Specifics | ✅ Done | SDN BHD detection + SSM/SST handling |
| Payroll Management | ✅ Done | Dynamic Engine (EPF/SOCSO/EIS + Proration + OT/Leave rules) |
| Bulk Payslips | ✅ Done | ZIP download of all monthly payslips |
| Payroll Claims | ✅ Done | Integrated approved invoices into payslips |
| Identity Scanner | ✅ Done | Malaysian IC/Passport OCR + Hardcoded Watermarking |
| Face Recognition | ✅ Done | Biometric face matching integration (resolved package resources dependencies) |
| Email Notifications | ✅ Done | Flask-Mail + Gmail SMTP + password reset + multipart (HTML+text) |
| Leave Duplicate Prevention | ✅ Done | Overlapping date check on leave application |
| Payroll Commission/Bonus Calc | ✅ Done | Commission (5% for >2yr), bonus (0-10% based on OT), leave adjustment |


### Sprint 2 Installation (when ready)
```bash
# OCR
pip install pytesseract
# Download Tesseract from: https://github.com/UB-Mannheim/tesseract/wiki
# Set path in app: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Face Recognition (Windows - use conda or WSL for easier install)
conda install -c conda-forge dlib
pip install face-recognition opencv-python
```

---

## 🗝 Session Variables

| Key | Value |
|-----|-------|
| `session['user_id']` | employee_id |
| `session['user_name']` | Full name |
| `session['user_role']` | Admin / HR / Manager / Employee |
| `session['user_initials']` | e.g. "AZ" |
| `session['user_email']` | Email address |
| `session['company_id']` | company_id |
| `session['branch_id']` | branch_id |
| `session['dept_name']` | Department name |

---

## 🔧 Configuration

- **Secret Key:** `app.secret_key` in `app/__init__.py` — **change before production**
- **Max Upload Size:** 10 MB (configurable in `__init__.py`)
- **Upload Folder:** `smarthr_app/uploads/`
- **DB Path:** `smarthr_app/instance/smarthr.db`

## 📧 Mail Configuration

SmartHR uses **Gmail SMTP** for email notifications (leave approve/reject, invoice approve/reject, IC access, payslip ready, password reset).

1. Enable 2FA on your Google account
2. Generate an App Password at https://myaccount.google.com/apppasswords
3. Create a `.env` file in the project root:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-16-char-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```
4. Emails are sent as **multipart/alternative** (HTML + plain text) for better deliverability
5. All email sends are logged in `AuditLog` (action: `SEND_EMAIL`)

> For development testing, use [Mailtrap](https://mailtrap.io) (port 2525, no real delivery).

---

## 👥 Team

| Member | Role |
|--------|------|
| Chan Han Yue | Full Stack Development, Database Design, AI Integration |
| Yap Kar Sheng | Co-developer — assign modules as needed |

**Supervisor:** TARUC Faculty of Computing & Information Technology

**Modules available for parallel development:**
- Sprint 2: OCR pipeline (`app/invoice/routes.py` → add OCR_Result logic)
- Sprint 2: Face recognition (`app/attendance/biometric.html` → wire to OpenCV)
- Sprint 2: Payroll calculation engine (`app/payroll/` → add calculation route)

---

## 📋 Pending / Next Features

| Feature | Status | Notes |
|---------|--------|-------|
| Leave Attachment Upload | ⏳ Planned | Allow employees to upload picture/PDF (e.g., medical cert for sick leave) when applying leave. Store in `uploads/leave/`, add `supporting_doc` column in Leave_Application (already exists in schema), update form + route. |

---

## ⚠️ Security Notes

1. Change `SECRET_KEY` in `app/__init__.py` before any real deployment
2. The `uploads/` folder should **not** be publicly accessible — serve through Flask with auth check
3. `instance/smarthr.db` should be backed up regularly
4. PDPA compliance: all data stays on local server, no cloud calls are made
