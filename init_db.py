"""
init_db.py  –  Run ONCE to create the SQLite database and seed demo data.
Usage: python init_db.py
WARNING: Running this again will DROP all existing data!
"""
import sqlite3
import os
from werkzeug.security import generate_password_hash
from datetime import datetime, date

DB_PATH = os.path.join('instance', 'smarthr.db')
SCHEMA_PATH = 'schema.sql'

def get_connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def migrate_add_branch_address_fields():
    """Add new address fields to existing Branch table if they don't exist."""
    con = get_connection()
    cur = con.cursor()
    
    # Check if columns exist
    cur.execute("PRAGMA table_info(Branch)")
    columns = [row[1] for row in cur.fetchall()]
    
    # Add missing columns
    if 'address_line1' not in columns:
        print("[MIGRATION] Adding address_line1 column to Branch...")
        cur.execute("ALTER TABLE Branch ADD COLUMN address_line1 TEXT")
    if 'address_line2' not in columns:
        print("[MIGRATION] Adding address_line2 column to Branch...")
        cur.execute("ALTER TABLE Branch ADD COLUMN address_line2 TEXT")
    if 'city' not in columns:
        print("[MIGRATION] Adding city column to Branch...")
        cur.execute("ALTER TABLE Branch ADD COLUMN city TEXT")
    if 'state' not in columns:
        print("[MIGRATION] Adding state column to Branch...")
        cur.execute("ALTER TABLE Branch ADD COLUMN state TEXT")
    if 'postal_code' not in columns:
        print("[MIGRATION] Adding postal_code column to Branch...")
        cur.execute("ALTER TABLE Branch ADD COLUMN postal_code TEXT")
    
    con.commit()
    con.close()
    print("[OK] Branch table migration completed.")

def init_db():
    os.makedirs('instance', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)

    con = get_connection()
    with open(SCHEMA_PATH, 'r') as f:
        con.executescript(f.read())
    con.commit()
    print("[OK] Schema applied.")
    con.close()
    
    # Run migration to add new fields to existing tables
    migrate_add_branch_address_fields()
    
    con = get_connection()
    cur = con.cursor()

    # ── Roles ──────────────────────────────────────────────────────────────
    roles = [('Admin',), ('HR',), ('Manager',), ('Employee',)]
    cur.executemany("INSERT OR IGNORE INTO Role(role_name) VALUES(?)", roles)

    # ── Permissions ────────────────────────────────────────────────────────
    # Define all available permissions
    permissions = [
        # Employee Management
        ('view_employees', 'View employee list and details', 'employees'),
        ('add_employee', 'Create new employees', 'employees'),
        ('edit_employee', 'Edit employee information', 'employees'),
        ('delete_employee', 'Delete/deactivate employees', 'employees'),
        ('view_payroll', 'View payroll information', 'payroll'),
        ('generate_payroll', 'Generate payroll records', 'payroll'),
        
        # Leave Management
        ('apply_leave', 'Apply for leave', 'leave'),
        ('view_leave', 'View own leave balance', 'leave'),
        ('approve_leave', 'Approve leave requests', 'leave'),
        ('view_all_leave', 'View all employee leave records', 'leave'),
        
        # Attendance
        ('view_attendance', 'View own attendance', 'attendance'),
        ('view_all_attendance', 'View all attendance records', 'attendance'),
        ('manual_attendance', 'Create manual attendance records', 'attendance'),
        
        # Invoices
        ('submit_invoice', 'Submit expense invoices', 'invoice'),
        ('view_invoice', 'View own invoices', 'invoice'),
        ('approve_invoice', 'Approve invoices', 'invoice'),
        ('view_all_invoice', 'View all invoices', 'invoice'),
        
        # Organization
        ('manage_organization', 'Manage org structure (branches, departments)', 'organization'),
        ('manage_roles', 'Manage roles and permissions', 'organization'),
        
        # Reports
        ('view_reports', 'View reports', 'reports'),
        ('generate_reports', 'Generate custom reports', 'reports'),
        
        # Audit
        ('view_audit_log', 'View audit logs', 'audit'),
        ('manage_audit_log', 'Archive audit logs', 'audit'),
        
        # Dashboard
        ('access_dashboard', 'Access main dashboard', 'main'),
        ('view_analytics', 'View analytics and statistics', 'main'),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO Permission(permission_name, description, module_name) VALUES(?,?,?)",
        permissions
    )
    
    # Map permissions to roles
    # Admin has all permissions
    cur.execute("SELECT role_id FROM Role WHERE role_name='Admin'")
    admin_role = cur.fetchone()[0]
    cur.execute("SELECT permission_id FROM Permission")
    all_perms = cur.fetchall()
    for perm in all_perms:
        cur.execute("INSERT OR IGNORE INTO Role_Permission(role_id, permission_id) VALUES(?,?)",
                   (admin_role, perm[0]))
    
    # HR role permissions
    cur.execute("SELECT role_id FROM Role WHERE role_name='HR'")
    hr_role = cur.fetchone()[0]
    hr_perms = [
        'view_employees', 'edit_employee', 'view_payroll', 'generate_payroll',
        'approve_leave', 'view_all_leave', 'view_all_attendance', 'manual_attendance',
        'approve_invoice', 'view_all_invoice', 'manage_organization',
        'view_reports', 'generate_reports', 'view_audit_log', 'access_dashboard'
    ]
    for perm_name in hr_perms:
        cur.execute("SELECT permission_id FROM Permission WHERE permission_name=?", (perm_name,))
        perm = cur.fetchone()
        if perm:
            cur.execute("INSERT OR IGNORE INTO Role_Permission(role_id, permission_id) VALUES(?,?)",
                       (hr_role, perm[0]))
    
    # Manager role permissions
    cur.execute("SELECT role_id FROM Role WHERE role_name='Manager'")
    manager_role = cur.fetchone()[0]
    manager_perms = [
        'view_employees', 'apply_leave', 'view_leave', 'approve_leave',
        'view_attendance', 'view_all_attendance', 'submit_invoice', 'view_invoice',
        'approve_invoice', 'view_reports', 'access_dashboard', 'view_analytics'
    ]
    for perm_name in manager_perms:
        cur.execute("SELECT permission_id FROM Permission WHERE permission_name=?", (perm_name,))
        perm = cur.fetchone()
        if perm:
            cur.execute("INSERT OR IGNORE INTO Role_Permission(role_id, permission_id) VALUES(?,?)",
                       (manager_role, perm[0]))
    
    # Employee role permissions
    cur.execute("SELECT role_id FROM Role WHERE role_name='Employee'")
    emp_role = cur.fetchone()[0]
    emp_perms = [
        'apply_leave', 'view_leave', 'view_attendance', 'submit_invoice',
        'view_invoice', 'access_dashboard'
    ]
    for perm_name in emp_perms:
        cur.execute("SELECT permission_id FROM Permission WHERE permission_name=?", (perm_name,))
        perm = cur.fetchone()
        if perm:
            cur.execute("INSERT OR IGNORE INTO Role_Permission(role_id, permission_id) VALUES(?,?)",
                       (emp_role, perm[0]))

    # ── Company ────────────────────────────────────────────────────────────
    cur.execute("""INSERT OR IGNORE INTO Company(company_id,name,address,contact_no,email)
                   VALUES(1,'Maju Teknologi Sdn Bhd',
                   'No. 12, Jalan Semarak, 50450 Kuala Lumpur, Malaysia',
                   '+603-2110 8888','info@majutek.com.my')""")

    # ── Branches ───────────────────────────────────────────────────────────
    cur.execute("""INSERT OR IGNORE INTO Branch(branch_id,company_id,name,address,contact_no)
                   VALUES(1,1,'KL Headquarters',
                   'No. 12, Jalan Semarak, 50450 Kuala Lumpur, Malaysia','+603-2110 8888')""")
    cur.execute("""INSERT OR IGNORE INTO Branch(branch_id,company_id,name,address,contact_no)
                   VALUES(2,1,'Penang Office',
                   'Unit 5-3, Krystal Point, 11700 Gelugor, Pulau Pinang, Malaysia','+604-658 9000')""")

    # ── Departments ────────────────────────────────────────────────────────
    depts = [
        (1, 1, 'Engineering'),
        (2, 1, 'Human Resources'),
        (3, 1, 'Operations'),
        (4, 1, 'Finance'),
        (5, 1, 'Administration'),
        (6, 2, 'Engineering'),
        (7, 2, 'Operations'),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO Department(department_id,branch_id,department_name) VALUES(?,?,?)",
        depts
    )

    # ── Employees ──────────────────────────────────────────────────────────
    employees = [
        # (id, co, br, dept, name, ic, contact, address, dob, gender, ec_name, ec_no,
        #  position, emp_type, emp_status, hire_date, salary, role_id, email, password)
        (1, 1, 1, 5, 'Ahmad Zainal bin Abdullah',  '800101145001', '+601128889001',
         'No 5, Jalan Bukit Bintang, 55100 KL', '1980-01-14', 'Male',
         'Siti Zainal', '+601128889002', 'System Administrator',
         'Full-Time', 'Active', '2020-01-15', 0.00, 1,
         'admin@smarthr.my', generate_password_hash('Admin@123')),

        (2, 1, 1, 2, 'Amantha Lee Mei Ling', '850603085002', '+601123456001',
         'No 22, Jalan Ampang Hilir, 55000 KL', '1985-06-03', 'Female',
         'Lee Ah Kow', '+601123456002', 'HR Director',
         'Full-Time', 'Active', '2019-03-10', 9500.00, 2,
         'hr@smarthr.my', generate_password_hash('Hr@123')),

        (3, 1, 1, 3, 'Brian Harris', '780215085003', '+601187654321',
         'No 8, Jalan Utama, 50480 KL', '1978-02-15', 'Male',
         'Janet Harris', '+601187654322', 'Chief Executive Officer',
         'Full-Time', 'Active', '2018-06-01', 18000.00, 3,
         'brian@smarthr.my', generate_password_hash('Manager@123')),

        (4, 1, 1, 3, 'Elizabeth Lopez', '930211086004', '+601134567890',
         'No 14, Jalan Damansara, 50490 KL', '1993-02-11', 'Female',
         'Jose Lopez', '+601134567891', 'Operations Executive',
         'Full-Time', 'Active', '2023-02-11', 4800.00, 4,
         'elizabeth@smarthr.my', generate_password_hash('Employee@123')),

        (5, 1, 1, 1, 'Ryan Tan Chee Keong', '920819015005', '+601145678901',
         'No 33, Jalan Kepong, 52100 KL', '1992-08-19', 'Male',
         'Tan Ah Seng', '+601145678902', 'Senior Software Engineer',
         'Full-Time', 'Active', '2022-08-19', 7200.00, 4,
         'ryan@smarthr.my', generate_password_hash('Employee@123')),

        (6, 1, 1, 2, 'Sarah Lim Hui Shan', '950303086006', '+601156789012',
         'No 7, Jalan Cheras, 56100 KL', '1995-03-03', 'Female',
         'Lim Ah Moi', '+601156789013', 'HR Executive',
         'Full-Time', 'On Leave', '2024-01-03', 4500.00, 2,
         'sarah@smarthr.my', generate_password_hash('Employee@123')),

        (7, 1, 1, 4, 'Nurul Hana binti Mohd Yusof', '011115086007', '+601167890123',
         'No 19, Jalan Duta, 50480 KL', '2001-11-15', 'Female',
         'Mohd Yusof', '+601167890124', 'Finance Executive',
         'Contract', 'Active', '2025-11-15', 3800.00, 4,
         'nurul@smarthr.my', generate_password_hash('Employee@123')),

        (8, 1, 1, 1, 'Kevin Lim Boon Kiat', '900627015008', '+601178901234',
         'No 45, Jalan PJ, 47810 Petaling Jaya', '1990-06-27', 'Male',
         'Lim Boon Hock', '+601178901235', 'Junior Developer',
         'Part-Time', 'Inactive', '2021-06-27', 2800.00, 4,
         'kevin@smarthr.my', generate_password_hash('Employee@123')),

        (9, 1, 2, 6, 'Muhammad Hafiz bin Razali', '880512095009', '+601189012345',
         'No 3, Jalan Macalister, 10400 Penang', '1988-05-12', 'Male',
         'Razali bin Hamid', '+601189012346', 'Engineering Manager',
         'Full-Time', 'Active', '2021-03-01', 8500.00, 3,
         'hafiz@smarthr.my', generate_password_hash('Manager@123')),

        (10, 1, 2, 7, 'Priya Krishnamurthy', '910730086010', '+601190123456',
         'No 11, Jalan Penang, 10000 Penang', '1991-07-30', 'Female',
         'Krishnamurthy V', '+601190123457', 'Operations Coordinator',
         'Full-Time', 'Active', '2022-07-15', 5200.00, 4,
         'priya@smarthr.my', generate_password_hash('Employee@123')),
    ]
    cur.executemany("""
        INSERT OR IGNORE INTO Employee
        (employee_id,company_id,branch_id,department_id,full_name,ic_number,contact_no,
         address,date_of_birth,gender,emergency_contact_name,emergency_contact_no,
         position,employment_type,employment_status,hire_date,base_salary,
         role_id,email,password_hash)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, employees)

    # ── Assign Permissions to Employees ────────────────────────────────────
    # For each employee, grant all permissions associated with their role
    for emp_id, company_id, branch_id, dept_id, full_name, ic, contact, address, dob, gender, ec_name, ec_no, position, emp_type, emp_status, hire_date, salary, role_id, email, pw in employees:
        cur.execute("SELECT permission_id FROM Role_Permission WHERE role_id=?", (role_id,))
        role_perms = cur.fetchall()
        for perm in role_perms:
            cur.execute("INSERT OR IGNORE INTO Employee_Permission(employee_id, permission_id, is_active, reason) VALUES(?,?,1,'initial_role_assignment')",
                       (emp_id, perm[0]))

    # ── Leave Types ────────────────────────────────────────────────────────
    leave_types = [
        (1, 'Annual Leave',    14, 1, 0, 'Paid annual leave entitlement'),
        (2, 'Sick Leave',      14, 1, 1, 'Medical leave with MC required'),
        (3, 'Emergency Leave',  3, 1, 0, 'For family emergencies'),
        (4, 'Unpaid Leave',    30, 0, 0, 'No-pay leave upon approval'),
        (5, 'Maternity Leave', 90, 1, 1, 'Maternity leave (female)'),
        (6, 'Paternity Leave',  3, 1, 0, 'Paternity leave (male)'),
        (7, 'Examination Leave',5, 1, 1, 'For official examinations'),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO Leave_Type(leave_type_id,type_name,default_days,is_paid,requires_document,description) VALUES(?,?,?,?,?,?)",
        leave_types
    )

    # ── Leave Entitlements ─────────────────────────────────────────────────
    entitlements = [
        (1, 'Full-Time', 0, 14, 2026),
        (1, 'Full-Time', 2, 16, 2026),
        (1, 'Full-Time', 5, 18, 2026),
        (1, 'Part-Time', 0,  7, 2026),
        (1, 'Contract',  0, 10, 2026),
        (2, 'Full-Time', 0, 14, 2026),
        (2, 'Part-Time', 0,  7, 2026),
        (2, 'Contract',  0, 10, 2026),
        (3, 'Full-Time', 0,  3, 2026),
        (4, 'Full-Time', 0, 30, 2026),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO Leave_Entitlement(leave_type_id,employment_type,min_service_years,entitled_days,effective_year) VALUES(?,?,?,?,?)",
        entitlements
    )

    # ── Leave Balances (2026) ──────────────────────────────────────────────
    # (employee_id, leave_type_id, year, entitled, used, pending)
    balances = [
        (4, 1, 2026, 14, 4.0, 0.0),  (4, 2, 2026, 14, 2.0, 0.0), (4, 3, 2026, 3, 0, 0),
        (5, 1, 2026, 14, 6.0, 0.0),  (5, 2, 2026, 14, 0.0, 0.0), (5, 3, 2026, 3, 0, 0),
        (6, 1, 2026, 14, 6.0, 3.0),  (6, 2, 2026, 14, 1.0, 0.0), (6, 3, 2026, 3, 0, 0),
        (7, 1, 2026, 10, 0.0, 0.0),  (7, 2, 2026, 10, 0.0, 0.0), (7, 3, 2026, 3, 0, 0),
        (8, 1, 2026,  7, 2.0, 0.0),  (8, 2, 2026,  7, 0.0, 0.0),
        (9, 1, 2026, 16, 2.0, 0.0),  (9, 2, 2026, 14, 0.0, 0.0), (9, 3, 2026, 3, 0, 0),
        (10,1, 2026, 14, 0.0, 0.0),  (10,2, 2026, 14, 0.0, 0.0), (10,3, 2026, 3, 0, 0),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO Leave_Balance(employee_id,leave_type_id,year,entitled_days,used_days,pending_days) VALUES(?,?,?,?,?,?)",
        balances
    )

    # ── Leave Applications ─────────────────────────────────────────────────
    apps = [
        (1,6,1,'2026-04-07','2026-04-09',3,'Family vacation',None,'Pending',   None,None,None),
        (2,6,2,'2026-04-05','2026-04-05',1,'Medical checkup','mc_nurul.pdf','Approved',2,'2026-04-04','Approved. Rest well.'),
        (3,5,1,'2026-03-20','2026-03-25',4,'Annual break',  None,'Approved',  2,'2026-03-19','Enjoy your leave.'),
        (4,5,1,'2026-04-10','2026-04-10',1,'Fever',         None,'Pending',   None,None,None),
    ]
    cur.executemany("""
        INSERT OR IGNORE INTO Leave_Application
        (leave_id,employee_id,leave_type_id,start_date,end_date,total_days,reason,supporting_doc,
         status,reviewed_by,reviewed_at,review_comment)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, apps)

    # ── Attendance Records ─────────────────────────────────────────────────
    att = [
        (4, 1, '2026-04-21 09:00:00', '2026-04-21 18:00:00', 8.0, 0.0, None, 'Approved', 0),
        (4, 1, '2026-04-22 08:55:00', '2026-04-22 18:05:00', 8.17, 0.0, None, 'Approved', 0),
        (5, 1, '2026-04-21 09:10:00', '2026-04-21 19:30:00', 9.33, 1.33, None, 'Approved', 0),
        (5, 1, '2026-04-22 09:00:00', '2026-04-22 20:00:00', 9.0, 1.0, None, 'Flagged', 0),
        (7, 1, '2026-04-21 09:00:00', '2026-04-21 18:00:00', 8.0, 0.0, None, 'Approved', 0),
        (9, 2, '2026-04-21 08:30:00', '2026-04-21 17:30:00', 8.0, 0.0, None, 'Approved', 0),
        (10,2, '2026-04-21 09:05:00', '2026-04-21 18:00:00', 7.92, 0.0, None, 'Approved', 0),
    ]
    cur.executemany("""
        INSERT OR IGNORE INTO Attendance
        (employee_id,branch_id,check_in,check_out,hours_worked,overtime_hours,
         confidence_score,status,is_manual_entry)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, att)

    # ── Invoices ───────────────────────────────────────────────────────────
    inv = [
        (1, 4, 'inv_0842.jpg', 'receipt_techcorp.jpg',   'image', 'TechCorp Sdn Bhd',
         'INV-0842', '2026-04-02', '2026-04-16', 'MYR', 1.0, 3018.87, 181.13, 3200.00, 3200.00,
         'IT Equipment', 'Laptop maintenance service package', 'Approved', 2, '2026-04-03', None),

        (2, 5, 'inv_0841.jpg', 'receipt_officepro.jpg',  'image', 'OfficePro Supplies',
         'INV-0841', '2026-04-01', '2026-04-15', 'MYR', 1.0, 735.85,  44.15,  780.00, 780.00,
         'Office Supplies', 'Stationery and printing supplies', 'Approved', 2, '2026-04-02', None),

        (3, 4, 'inv_0843.jpg', 'receipt_petrol.jpg',     'image', 'Petronas',
         'INV-0843', '2026-04-08', '2026-04-22', 'MYR', 1.0, 120.00,  0.00,   120.00, 120.00,
         'Transport', 'Petrol claim for client visit', 'Pending', None, None, None),

        (4, 7, 'inv_0840.jpg', 'receipt_training.jpg',   'image', 'HR Academy Malaysia',
         'INV-0840', '2026-03-28', '2026-04-11', 'MYR', 1.0, 1500.00, 90.00,  1590.00, 1590.00,
         'Training', 'HR skills workshop registration', 'Rejected', 2, '2026-04-01',
         'Out of approved training budget for Q1.'),
    ]
    cur.executemany("""
        INSERT OR IGNORE INTO Invoice
        (invoice_id,employee_id,filename,original_name,file_type,vendor_name,
         invoice_number,invoice_date,due_date,currency,exchange_rate,subtotal,
         tax_amount,total_amount,total_amount_myr,category,description,status,
         approved_by,approved_at,rejection_reason)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, inv)

    # ── Payroll (April 2026) ───────────────────────────────────────────────
    def calc_payroll(emp_id, base, ot_pay=0, claims=0, bonus=0):
        gross = base + ot_pay + claims + bonus
        epf_e   = round(gross * 0.11, 2)
        epf_er  = round(gross * 0.13, 2)
        socso_e = round(min(gross, 5000) * 0.005, 2)
        socso_er= round(min(gross, 5000) * 0.0175, 2)
        eis_e   = round(min(gross, 5000) * 0.002, 2)
        eis_er  = round(min(gross, 5000) * 0.002, 2)
        pcb = round(max(0, (gross - 3000) * 0.01), 2) if gross > 3000 else 0
        total_ded = epf_e + socso_e + eis_e + pcb
        net = round(gross - total_ded, 2)
        return (emp_id, 4, 2026, base, ot_pay, 0, bonus, claims, 0, gross,
                epf_e, epf_er, socso_e, socso_er, eis_e, eis_er, pcb,
                total_ded, net, 'Finalised', 2)

    payrolls = [
        calc_payroll(4, 4800.00, ot_pay=0,    claims=3200.00),
        calc_payroll(5, 7200.00, ot_pay=360.00,claims=780.00),
        calc_payroll(6, 4500.00, ot_pay=0,    claims=0),
        calc_payroll(7, 3800.00, ot_pay=0,    claims=0),
        calc_payroll(8, 2800.00, ot_pay=0,    claims=0),
        calc_payroll(9, 8500.00, ot_pay=0,    claims=0),
        calc_payroll(10,5200.00, ot_pay=0,    claims=0),
    ]
    cur.executemany("""
        INSERT OR IGNORE INTO Payroll
        (employee_id,pay_period_month,pay_period_year,base_salary,overtime_pay,commission,bonus,
         invoice_claims,leave_adjustment,gross_pay,epf_employee,epf_employer,socso_employee,
         socso_employer,eis_employee,eis_employer,pcb_tax,total_deductions,net_pay,status,generated_by)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, payrolls)

    # ── Audit Log seed ─────────────────────────────────────────────────────
    logs = [
        (1,'LOGIN','Auth','Admin logged in','Employee',1,'Success',None,'127.0.0.1'),
        (2,'LOGIN','Auth','HR Director logged in','Employee',2,'Success',None,'192.168.1.23'),
        (2,'APPROVE','Leave','Approved leave application LV-002','Leave_Application',2,'Success','{"leave_id":2}','192.168.1.23'),
        (4,'APPLY_LEAVE','Leave','Elizabeth applied for Annual Leave','Leave_Application',1,'Success','{"days":3}','192.168.1.34'),
        (5,'LOGIN','Auth','Failed login attempt','Employee',5,'Failed',None,'192.168.1.57'),
    ]
    cur.executemany("""
        INSERT INTO AuditLog
        (employee_id,action,module_name,description,target_table,target_record_id,
         action_status,action_details,ip_address)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, logs)

    con.commit()
    con.close()
    print("[OK] Database seeded with Malaysian demo data.")
    print()
    print("=== DEFAULT LOGIN CREDENTIALS ===")
    print("System Admin : admin@smarthr.my   / Admin@123")
    print("HR Director  : hr@smarthr.my      / Hr@123")
    print("Manager      : brian@smarthr.my   / Manager@123  (Hafiz: hafiz@smarthr.my)")
    print("Employee     : elizabeth@smarthr.my / Employee@123  (others same password)")
    print("=================================")

if __name__ == '__main__':
    init_db()
