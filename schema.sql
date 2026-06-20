-- =============================================================================
-- SmartHR – SQLite Schema (converted from hr_system_erd_v3.sql)
-- SQLite differences: no ENUM, no AUTO_INCREMENT, no JSON type, no ON UPDATE
-- =============================================================================
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Role (
    role_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name TEXT NOT NULL UNIQUE  -- 'Admin', 'HR', 'Manager', 'Employee'
);

CREATE TABLE IF NOT EXISTS Company (
    company_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    address     TEXT,
    contact_no  TEXT,
    email       TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Branch (
    branch_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id    INTEGER NOT NULL,
    name          TEXT NOT NULL,
    address       TEXT,
    address_line1 TEXT,
    address_line2 TEXT,
    city          TEXT,
    state         TEXT,
    postal_code   TEXT,
    contact_no    TEXT,
    hr_manager_id INTEGER,
    parent_branch_id INTEGER,
    FOREIGN KEY (company_id) REFERENCES Company(company_id),
    FOREIGN KEY (parent_branch_id) REFERENCES Branch(branch_id)
);

CREATE TABLE IF NOT EXISTS Department (
    department_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id       INTEGER NOT NULL,
    department_name TEXT NOT NULL,
    FOREIGN KEY (branch_id) REFERENCES Branch(branch_id)
);

CREATE TABLE IF NOT EXISTS Employee (
    employee_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id             INTEGER NOT NULL,
    branch_id              INTEGER NOT NULL,
    department_id          INTEGER NOT NULL,
    full_name              TEXT NOT NULL,
    ic_number              TEXT UNIQUE,
    passport_number        TEXT,
    contact_no             TEXT,
    address                TEXT,
    date_of_birth          TEXT,
    gender                 TEXT CHECK(gender IN ('Male','Female','Other')),
    marital_status         TEXT, -- 'Single', 'Married', 'Divorced', 'Widowed'
    emergency_contact_name TEXT,
    emergency_contact_no   TEXT,
    position               TEXT,
    employment_type        TEXT NOT NULL DEFAULT 'Full-Time'
                               CHECK(employment_type IN ('Full-Time','Part-Time','Contract')),
    employment_status      TEXT DEFAULT 'Active'
                               CHECK(employment_status IN ('Active','On Leave','Inactive','Terminated')),
    hire_date              TEXT NOT NULL,
    base_salary            REAL NOT NULL DEFAULT 0.00,
    role_id                INTEGER NOT NULL,
    email                  TEXT NOT NULL UNIQUE,
    password_hash          TEXT NOT NULL,
    is_active              INTEGER DEFAULT 1,
    failed_attempts        INTEGER DEFAULT 0,
    locked_until           TEXT,
    last_login             TEXT,
    id_document_path       TEXT, -- Path to watermarked IC/Passport
    created_at             TEXT DEFAULT (datetime('now')),
    updated_at             TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (company_id)    REFERENCES Company(company_id),
    FOREIGN KEY (branch_id)     REFERENCES Branch(branch_id),
    FOREIGN KEY (department_id) REFERENCES Department(department_id),
    FOREIGN KEY (role_id)       REFERENCES Role(role_id)
);

CREATE TABLE IF NOT EXISTS Face_Encoding (
    encoding_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id        INTEGER NOT NULL UNIQUE,
    face_encoding_blob BLOB NOT NULL,
    registered_at      TEXT DEFAULT (datetime('now')),
    updated_at         TEXT DEFAULT (datetime('now')),
    registered_by      INTEGER,
    FOREIGN KEY (employee_id)   REFERENCES Employee(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (registered_by) REFERENCES Employee(employee_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Attendance (
    attendance_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id      INTEGER NOT NULL,
    branch_id        INTEGER NOT NULL,
    check_in         TEXT NOT NULL,
    check_out        TEXT,
    hours_worked     REAL,
    overtime_hours   REAL DEFAULT 0.00,
    confidence_score REAL,
    status           TEXT DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Flagged')),
    is_manual_entry  INTEGER DEFAULT 0,
    manual_reason    TEXT,
    corrected_by     INTEGER,
    corrected_at     TEXT,
    created_at       TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id)  REFERENCES Employee(employee_id),
    FOREIGN KEY (branch_id)    REFERENCES Branch(branch_id),
    FOREIGN KEY (corrected_by) REFERENCES Employee(employee_id)
);

CREATE TABLE IF NOT EXISTS Invoice (
  invoice_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id    INTEGER NOT NULL,
  filename       TEXT NOT NULL,
  original_name  TEXT,
  file_type      TEXT NOT NULL CHECK(file_type IN ('image','pdf')),
  vendor_name    TEXT,
  invoice_number TEXT,
  invoice_date   TEXT,
  due_date       TEXT,
  currency       TEXT DEFAULT 'MYR',
  exchange_rate  REAL,
  subtotal       REAL,
  tax_amount     REAL DEFAULT 0.00,
  total_amount   REAL,
  total_amount_myr REAL,
  category       TEXT,
  description    TEXT,
  status         TEXT DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected','Paid')),
  submitted_at   TEXT DEFAULT (datetime('now')),
  approved_by    INTEGER,
  approved_at    TEXT,
  rejection_reason TEXT,
  FOREIGN KEY (employee_id) REFERENCES Employee(employee_id),
  FOREIGN KEY (approved_by) REFERENCES Employee(employee_id)
);

CREATE TABLE IF NOT EXISTS OCR_Result (
    result_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id       INTEGER NOT NULL UNIQUE,
    raw_text         TEXT,
    extracted_data   TEXT,   -- JSON stored as text
    confidence_score REAL,
    ocr_engine       TEXT DEFAULT 'Tesseract',
    is_manual_review INTEGER DEFAULT 0,
    reviewed_by      INTEGER,
    reviewed_at      TEXT,
    created_at       TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (invoice_id)  REFERENCES Invoice(invoice_id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES Employee(employee_id)
);

-- Learned patterns for specific vendors to improve OCR over time
CREATE TABLE IF NOT EXISTS Vendor_Pattern (
    pattern_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_name    TEXT NOT NULL UNIQUE,
    inv_num_anchor TEXT,   -- e.g., "Ref No"
    date_anchor    TEXT,   -- e.g., "Issue Date"
    total_anchor   TEXT,   -- e.g., "Amount Due"
    category_hint  TEXT,
    occurrence_count INTEGER DEFAULT 1,
    last_updated   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Leave_Type (
    leave_type_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name        TEXT NOT NULL UNIQUE,
    default_days     INTEGER NOT NULL DEFAULT 0,
    is_paid          INTEGER DEFAULT 1,
    requires_document INTEGER DEFAULT 0,
    description      TEXT,
    eligible_genders TEXT, -- Comma-separated list of eligible genders (e.g., 'Male,Female' or 'Female' for maternity),
    eligible_marital_status TEXT -- Comma-separated list of eligible marital statuses (e.g., 'Single,Married' or NULL for any)
);

CREATE TABLE IF NOT EXISTS Leave_Entitlement (
    entitlement_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    leave_type_id    INTEGER NOT NULL,
    employment_type  TEXT NOT NULL CHECK(employment_type IN ('Full-Time','Part-Time','Contract')),
    min_service_years INTEGER NOT NULL DEFAULT 0,
    entitled_days    INTEGER NOT NULL DEFAULT 0,
    effective_year   INTEGER NOT NULL,
    UNIQUE (leave_type_id, employment_type, min_service_years, effective_year),
    FOREIGN KEY (leave_type_id) REFERENCES Leave_Type(leave_type_id)
);

CREATE TABLE IF NOT EXISTS Leave_Balance (
    balance_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id   INTEGER NOT NULL,
    leave_type_id INTEGER NOT NULL,
    year          INTEGER NOT NULL,
    entitled_days REAL NOT NULL DEFAULT 0.0,
    used_days     REAL NOT NULL DEFAULT 0.0,
    pending_days  REAL NOT NULL DEFAULT 0.0,
    UNIQUE (employee_id, leave_type_id, year),
    FOREIGN KEY (employee_id)   REFERENCES Employee(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (leave_type_id) REFERENCES Leave_Type(leave_type_id)
);

CREATE TABLE IF NOT EXISTS Leave_Application (
    leave_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL,
    leave_type_id   INTEGER NOT NULL,
    start_date      TEXT NOT NULL,
    end_date        TEXT NOT NULL,
    total_days      REAL NOT NULL,
    reason          TEXT,
    supporting_doc  TEXT,
    status          TEXT DEFAULT 'Pending'
                        CHECK(status IN ('Pending','Approved','Rejected','Cancelled')),
    applied_at      TEXT DEFAULT (datetime('now')),
    reviewed_by     INTEGER,
    reviewed_at     TEXT,
    review_comment  TEXT,
    last_updated_by INTEGER,
    last_updated_at TEXT,
    FOREIGN KEY (employee_id)    REFERENCES Employee(employee_id),
    FOREIGN KEY (leave_type_id)  REFERENCES Leave_Type(leave_type_id),
    FOREIGN KEY (reviewed_by)    REFERENCES Employee(employee_id),
    FOREIGN KEY (last_updated_by) REFERENCES Employee(employee_id)
);

CREATE TABLE IF NOT EXISTS Payroll (
    payroll_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id      INTEGER NOT NULL,
    pay_period_month INTEGER NOT NULL,
    pay_period_year  INTEGER NOT NULL,
    base_salary      REAL NOT NULL DEFAULT 0.00,
    overtime_pay     REAL NOT NULL DEFAULT 0.00,
    commission       REAL NOT NULL DEFAULT 0.00,
    bonus            REAL NOT NULL DEFAULT 0.00,
    invoice_claims   REAL NOT NULL DEFAULT 0.00,
    leave_adjustment REAL NOT NULL DEFAULT 0.00,
    gross_pay        REAL NOT NULL DEFAULT 0.00,
    epf_employee     REAL NOT NULL DEFAULT 0.00,
    epf_employer     REAL NOT NULL DEFAULT 0.00,
    socso_employee   REAL NOT NULL DEFAULT 0.00,
    socso_employer   REAL NOT NULL DEFAULT 0.00,
    eis_employee     REAL NOT NULL DEFAULT 0.00,
    eis_employer     REAL NOT NULL DEFAULT 0.00,
    pcb_tax          REAL NOT NULL DEFAULT 0.00,
    total_deductions REAL NOT NULL DEFAULT 0.00,
    net_pay          REAL NOT NULL DEFAULT 0.00,
    status           TEXT DEFAULT 'Draft' CHECK(status IN ('Draft','Finalised','Paid')),
    generated_by     INTEGER,
    generated_at     TEXT DEFAULT (datetime('now')),
    UNIQUE (employee_id, pay_period_month, pay_period_year),
    FOREIGN KEY (employee_id)  REFERENCES Employee(employee_id),
    FOREIGN KEY (generated_by) REFERENCES Employee(employee_id)
);

CREATE TABLE IF NOT EXISTS Payslip (
    payslip_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    payroll_id   INTEGER NOT NULL UNIQUE,
    employee_id  INTEGER NOT NULL,
    filename     TEXT NOT NULL,
    generated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (payroll_id)  REFERENCES Payroll(payroll_id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id)
);

CREATE TABLE IF NOT EXISTS Report (
    report_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_by INTEGER NOT NULL,
    report_type  TEXT NOT NULL CHECK(report_type IN ('Attendance','Invoice','Payroll','Leave','Headcount')),
    parameters   TEXT,
    file_path    TEXT,
    generated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (generated_by) REFERENCES Employee(employee_id)
);

CREATE TABLE IF NOT EXISTS AuditLog (
    audit_log_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id      INTEGER,
    action           TEXT NOT NULL,
    module_name      TEXT NOT NULL,
    description      TEXT,
    target_table     TEXT,
    target_record_id TEXT,
    action_status    TEXT NOT NULL DEFAULT 'Success' CHECK(action_status IN ('Success','Failed')),
    action_details   TEXT,   -- JSON stored as text
    ip_address       TEXT,
    user_agent       TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    is_archived      INTEGER NOT NULL DEFAULT 0,
    archived_at      TEXT,
    retention_until  TEXT,
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Notification (
    notification_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id        INTEGER NOT NULL,
    title              TEXT NOT NULL,
    message            TEXT,
    type               TEXT NOT NULL CHECK(type IN ('Info','Success','Warning','Error')),
    is_read            INTEGER NOT NULL DEFAULT 0,
    related_url        TEXT,
    created_at         TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_attendance_employee   ON Attendance(employee_id);
CREATE INDEX IF NOT EXISTS idx_attendance_checkin    ON Attendance(check_in);
CREATE INDEX IF NOT EXISTS idx_invoice_employee      ON Invoice(employee_id);
CREATE INDEX IF NOT EXISTS idx_invoice_status        ON Invoice(status);
CREATE INDEX IF NOT EXISTS idx_leave_app_employee    ON Leave_Application(employee_id);
CREATE INDEX IF NOT EXISTS idx_leave_app_status      ON Leave_Application(status);
CREATE INDEX IF NOT EXISTS idx_leave_balance_emp_yr  ON Leave_Balance(employee_id, year);
CREATE INDEX IF NOT EXISTS idx_payroll_employee      ON Payroll(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_email        ON Employee(email);
CREATE INDEX IF NOT EXISTS idx_audit_log_employee    ON AuditLog(employee_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_module      ON AuditLog(module_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at  ON AuditLog(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_archive     ON AuditLog(is_archived, archived_at);
CREATE INDEX IF NOT EXISTS idx_notification_employee ON Notification(employee_id);
CREATE INDEX IF NOT EXISTS idx_notification_read     ON Notification(employee_id, is_read);

-- =============================================================================
-- Permission System – Role-Based Access Control (RBAC)
-- =============================================================================

-- Define all available permissions in the system
CREATE TABLE IF NOT EXISTS Permission (
    permission_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    permission_name TEXT NOT NULL UNIQUE,  -- e.g., 'view_employees', 'approve_leave'
    description     TEXT,
    module_name     TEXT,                  -- e.g., 'employees', 'leave', 'payroll'
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Map roles to permissions (many-to-many)
CREATE TABLE IF NOT EXISTS Role_Permission (
    role_id         INTEGER NOT NULL,
    permission_id   INTEGER NOT NULL,
    granted_at      TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id)       REFERENCES Role(role_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES Permission(permission_id) ON DELETE CASCADE
);

-- Track individual employee permissions (optional: for audit/override)
CREATE TABLE IF NOT EXISTS Employee_Permission (
    employee_permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id     INTEGER NOT NULL,
    permission_id   INTEGER NOT NULL,
    granted_at      TEXT DEFAULT (datetime('now')),
    revoked_at      TEXT,
    is_active       INTEGER DEFAULT 1,
    granted_by      INTEGER,
    reason          TEXT,  -- e.g., 'promotion', 'role_change', 'manual_override'
    UNIQUE (employee_id, permission_id),
    FOREIGN KEY (employee_id)  REFERENCES Employee(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES Permission(permission_id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by)    REFERENCES Employee(employee_id) ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_role_permission_role     ON Role_Permission(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permission_perm     ON Role_Permission(permission_id);
CREATE INDEX IF NOT EXISTS idx_employee_permission_emp  ON Employee_Permission(employee_id);
CREATE INDEX IF NOT EXISTS idx_employee_permission_perm ON Employee_Permission(permission_id);
CREATE INDEX IF NOT EXISTS idx_employee_permission_active ON Employee_Permission(employee_id, is_active);
