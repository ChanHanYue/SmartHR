"""
migrate_db.py – Update existing SmartHR database with new features.
Usage: python migrate_db.py
This will preserve all existing data while adding new tables/columns.
"""
import sqlite3
import os

DB_PATH = os.path.join('instance', 'smarthr.db')

def get_connection():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def migrate_add_branch_address_fields():
    """Add new address fields to existing Branch table if they don't exist."""
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at {DB_PATH}")
        print("Please run init_db.py first to initialize the database.")
        return False
    
    con = get_connection()
    cur = con.cursor()
    
    try:
        # Check if columns exist
        cur.execute("PRAGMA table_info(Branch)")
        columns = [row[1] for row in cur.fetchall()]
        
        columns_added = []
        
        # Add missing columns
        if 'address_line1' not in columns:
            print("[MIGRATION] Adding address_line1 column to Branch...")
            cur.execute("ALTER TABLE Branch ADD COLUMN address_line1 TEXT")
            columns_added.append('address_line1')
        
        if 'address_line2' not in columns:
            print("[MIGRATION] Adding address_line2 column to Branch...")
            cur.execute("ALTER TABLE Branch ADD COLUMN address_line2 TEXT")
            columns_added.append('address_line2')
        
        if 'city' not in columns:
            print("[MIGRATION] Adding city column to Branch...")
            cur.execute("ALTER TABLE Branch ADD COLUMN city TEXT")
            columns_added.append('city')
        
        if 'state' not in columns:
            print("[MIGRATION] Adding state column to Branch...")
            cur.execute("ALTER TABLE Branch ADD COLUMN state TEXT")
            columns_added.append('state')
        
        if 'postal_code' not in columns:
            print("[MIGRATION] Adding postal_code column to Branch...")
            cur.execute("ALTER TABLE Branch ADD COLUMN postal_code TEXT")
            columns_added.append('postal_code')
        
        con.commit()
        
        if columns_added:
            print(f"\n[OK] Successfully added {len(columns_added)} column(s): {', '.join(columns_added)}")
        else:
            print("[INFO] All address columns already exist.")
        return True
            
    except sqlite3.Error as e:
        print(f"[ERROR] Migration failed: {e}")
        con.rollback()
        return False
    finally:
        con.close()

def migrate_add_invoice_currency_fields():
    """Add currency, exchange_rate, and total_amount_myr columns to Invoice table."""
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at {DB_PATH}")
        return False
    
    con = get_connection()
    cur = con.cursor()
    
    try:
        # Check if columns exist
        cur.execute("PRAGMA table_info(Invoice)")
        columns = [row[1] for row in cur.fetchall()]
        
        columns_added = []
        
        if 'currency' not in columns:
            print("[MIGRATION] Adding currency column to Invoice...")
            cur.execute("ALTER TABLE Invoice ADD COLUMN currency TEXT DEFAULT 'MYR'")
            columns_added.append('currency')
        
        if 'exchange_rate' not in columns:
            print("[MIGRATION] Adding exchange_rate column to Invoice...")
            cur.execute("ALTER TABLE Invoice ADD COLUMN exchange_rate REAL")
            columns_added.append('exchange_rate')
        
        if 'total_amount_myr' not in columns:
            print("[MIGRATION] Adding total_amount_myr column to Invoice...")
            cur.execute("ALTER TABLE Invoice ADD COLUMN total_amount_myr REAL")
            columns_added.append('total_amount_myr')
        
        con.commit()
        
        if columns_added:
            print(f"\n[OK] Successfully added {len(columns_added)} column(s): {', '.join(columns_added)}")
        else:
            print("[INFO] All currency-related columns already exist.")
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] Migration failed: {e}")
        con.rollback()
        return False
    finally:
        con.close()


def migrate_add_notification_and_ic_access():
    """Add Notification and IC Access Request tables, and ensure RBAC tables exist and are populated."""
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at {DB_PATH}")
        return False
    
    con = get_connection()
    cur = con.cursor()
    
    try:
        # Ensure all RBAC tables exist
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Role'")
        if not cur.fetchone():
            print("[MIGRATION] Creating Role table...")
            cur.execute("""
                CREATE TABLE Role (
                    role_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    role_name TEXT NOT NULL UNIQUE
                )
            """)
            print("[OK] Role table created")
        
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Permission'")
        if not cur.fetchone():
            print("[MIGRATION] Creating Permission table...")
            cur.execute("""
                CREATE TABLE Permission (
                    permission_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    permission_name TEXT NOT NULL UNIQUE,
                    description     TEXT,
                    module_name     TEXT,
                    created_at      TEXT DEFAULT (datetime('now'))
                )
            """)
            print("[OK] Permission table created")
        
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Role_Permission'")
        if not cur.fetchone():
            print("[MIGRATION] Creating Role_Permission table...")
            cur.execute("""
                CREATE TABLE Role_Permission (
                    role_id         INTEGER NOT NULL,
                    permission_id   INTEGER NOT NULL,
                    granted_at      TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (role_id, permission_id),
                    FOREIGN KEY (role_id)       REFERENCES Role(role_id) ON DELETE CASCADE,
                    FOREIGN KEY (permission_id) REFERENCES Permission(permission_id) ON DELETE CASCADE
                )
            """)
            print("[OK] Role_Permission table created")
        
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Employee_Permission'")
        if not cur.fetchone():
            print("[MIGRATION] Creating Employee_Permission table...")
            cur.execute("""
                CREATE TABLE Employee_Permission (
                    employee_permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id     INTEGER NOT NULL,
                    permission_id   INTEGER NOT NULL,
                    granted_at      TEXT DEFAULT (datetime('now')),
                    revoked_at      TEXT,
                    is_active       INTEGER DEFAULT 1,
                    granted_by      INTEGER,
                    reason          TEXT,
                    UNIQUE (employee_id, permission_id),
                    FOREIGN KEY (employee_id)  REFERENCES Employee(employee_id) ON DELETE CASCADE,
                    FOREIGN KEY (permission_id) REFERENCES Permission(permission_id) ON DELETE CASCADE,
                    FOREIGN KEY (granted_by)    REFERENCES Employee(employee_id) ON DELETE SET NULL
                )
            """)
            print("[OK] Employee_Permission table created")
        
        # Check if Role table has data, if not insert default roles
        cur.execute("SELECT COUNT(*) FROM Role")
        role_count = cur.fetchone()[0]
        if role_count == 0:
            print("[MIGRATION] Populating Role table with default roles...")
            cur.executemany("INSERT OR IGNORE INTO Role(role_name) VALUES(?)",
                          [('Admin',), ('HR',), ('Manager',), ('Employee',)])
            print("[OK] Default roles added")

        # Check if Permission table has data, if not insert default permissions
        cur.execute("SELECT COUNT(*) FROM Permission")
        perm_count = cur.fetchone()[0]
        if perm_count == 0:
            print("[MIGRATION] Populating Permission table with default permissions...")
            permissions = [
                ('view_employees', 'View employee list and details', 'employees'),
                ('add_employee', 'Create new employees', 'employees'),
                ('edit_employee', 'Edit employee information', 'employees'),
                ('delete_employee', 'Delete/deactivate employees', 'employees'),
                ('view_payroll', 'View payroll information', 'payroll'),
                ('generate_payroll', 'Generate payroll records', 'payroll'),
                ('apply_leave', 'Apply for leave', 'leave'),
                ('view_leave', 'View own leave balance', 'leave'),
                ('approve_leave', 'Approve leave requests', 'leave'),
                ('view_all_leave', 'View all employee leave records', 'leave'),
                ('view_attendance', 'View own attendance', 'attendance'),
                ('view_all_attendance', 'View all attendance records', 'attendance'),
                ('manual_attendance', 'Create manual attendance records', 'attendance'),
                ('submit_invoice', 'Submit expense invoices', 'invoice'),
                ('view_invoice', 'View own invoices', 'invoice'),
                ('approve_invoice', 'Approve invoices', 'invoice'),
                ('view_all_invoice', 'View all invoices', 'invoice'),
                ('manage_organization', 'Manage org structure (branches, departments)', 'organization'),
                ('manage_roles', 'Manage roles and permissions', 'organization'),
                ('view_reports', 'View reports', 'reports'),
                ('generate_reports', 'Generate custom reports', 'reports'),
                ('view_audit_log', 'View audit logs', 'audit'),
                ('manage_audit_log', 'Archive audit logs', 'audit'),
                ('access_dashboard', 'Access main dashboard', 'main'),
                ('view_analytics', 'View analytics and statistics', 'main'),
            ]
            cur.executemany(
                "INSERT OR IGNORE INTO Permission(permission_name, description, module_name) VALUES(?,?,?)",
                permissions
            )
            print("[OK] Default permissions added")

            # Now populate Role_Permission
            print("[MIGRATION] Setting up role permissions...")
            # Get role IDs
            cur.execute("SELECT role_id, role_name FROM Role")
            roles = {row['role_name']: row['role_id'] for row in cur.fetchall()}
            
            # Get permission IDs
            cur.execute("SELECT permission_id, permission_name FROM Permission")
            perms = {row['permission_name']: row['permission_id'] for row in cur.fetchall()}

            # Admin - all permissions
            for perm_id in perms.values():
                cur.execute("INSERT OR IGNORE INTO Role_Permission(role_id, permission_id) VALUES(?,?)",
                          (roles['Admin'], perm_id))
            
            # HR permissions
            hr_perms = ['view_employees', 'edit_employee', 'view_payroll', 'generate_payroll',
                       'approve_leave', 'view_all_leave', 'view_all_attendance', 'manual_attendance',
                       'approve_invoice', 'view_all_invoice', 'manage_organization',
                       'view_reports', 'generate_reports', 'view_audit_log', 'access_dashboard']
            for perm_name in hr_perms:
                if perm_name in perms:
                    cur.execute("INSERT OR IGNORE INTO Role_Permission(role_id, permission_id) VALUES(?,?)",
                              (roles['HR'], perms[perm_name]))
            
            # Manager permissions
            manager_perms = ['view_employees', 'apply_leave', 'view_leave', 'approve_leave',
                          'view_attendance', 'view_all_attendance', 'submit_invoice', 'view_invoice',
                          'approve_invoice', 'view_reports', 'access_dashboard', 'view_analytics']
            for perm_name in manager_perms:
                if perm_name in perms:
                    cur.execute("INSERT OR IGNORE INTO Role_Permission(role_id, permission_id) VALUES(?,?)",
                              (roles['Manager'], perms[perm_name]))
            
            # Employee permissions
            emp_perms = ['apply_leave', 'view_leave', 'view_attendance', 'submit_invoice',
                      'view_invoice', 'access_dashboard']
            for perm_name in emp_perms:
                if perm_name in perms:
                    cur.execute("INSERT OR IGNORE INTO Role_Permission(role_id, permission_id) VALUES(?,?)",
                              (roles['Employee'], perms[perm_name]))
            
            print("[OK] Role permissions set up")

        # Check if tables already exist
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Notification'")
        if not cur.fetchone():
            print("[MIGRATION] Creating Notification table...")
            cur.execute("""
                CREATE TABLE Notification (
                    notification_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id      INTEGER NOT NULL,
                    title            TEXT NOT NULL,
                    message          TEXT NOT NULL,
                    type             TEXT NOT NULL DEFAULT 'Info' CHECK(type IN ('Info','Success','Warning','Error')),
                    is_read          INTEGER DEFAULT 0,
                    related_url      TEXT,
                    created_at       TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id) ON DELETE CASCADE
                )
            """)
            # Create indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_notification_employee ON Notification(employee_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_notification_read ON Notification(employee_id, is_read)")
            print("[OK] Notification table created")
        else:
            # Check and add missing columns
            cur.execute("PRAGMA table_info(Notification)")
            columns = [row[1] for row in cur.fetchall()]
            if 'type' not in columns:
                print("[MIGRATION] Adding type column to Notification...")
                cur.execute("ALTER TABLE Notification ADD COLUMN type TEXT NOT NULL DEFAULT 'Info' CHECK(type IN ('Info','Success','Warning','Error'))")
            if 'related_url' not in columns:
                print("[MIGRATION] Adding related_url column to Notification...")
                cur.execute("ALTER TABLE Notification ADD COLUMN related_url TEXT")
        
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='IC_Access_Request'")
        if not cur.fetchone():
            print("[MIGRATION] Creating IC_Access_Request table...")
            cur.execute("""
                CREATE TABLE IC_Access_Request (
                    request_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    requester_id    INTEGER NOT NULL,
                    target_employee_id INTEGER NOT NULL,
                    reason          TEXT,
                    status          TEXT DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected','Expired')),
                    requested_at    TEXT DEFAULT (datetime('now')),
                    reviewed_by     INTEGER,
                    reviewed_at     TEXT,
                    expires_at      TEXT,
                    FOREIGN KEY (requester_id)   REFERENCES Employee(employee_id) ON DELETE CASCADE,
                    FOREIGN KEY (target_employee_id) REFERENCES Employee(employee_id) ON DELETE CASCADE,
                    FOREIGN KEY (reviewed_by)    REFERENCES Employee(employee_id)
                )
            """)
            # Create indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ic_access_request_requester ON IC_Access_Request(requester_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ic_access_request_target ON IC_Access_Request(target_employee_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ic_access_request_status ON IC_Access_Request(status)")
            print("[OK] IC_Access_Request table created")
        
        con.commit()
        print("[INFO] Notification & IC Access Request system added successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] Migration failed: {e}")
        con.rollback()
        return False
    finally:
        con.close()

def migrate_add_leave_type_eligibility():
    """Add eligibility columns to Leave_Type and set default values for existing leaves."""
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found at {DB_PATH}")
        return False
    
    con = get_connection()
    cur = con.cursor()
    
    try:
        # Check if columns exist in Leave_Type
        cur.execute("PRAGMA table_info(Leave_Type)")
        cols = [row[1] for row in cur.fetchall()]
        
        if 'eligible_genders' not in cols:
            print("[MIGRATION] Adding eligible_genders column to Leave_Type...")
            cur.execute("ALTER TABLE Leave_Type ADD COLUMN eligible_genders TEXT")
        
        if 'eligible_marital_status' not in cols:
            print("[MIGRATION] Adding eligible_marital_status column to Leave_Type...")
            cur.execute("ALTER TABLE Leave_Type ADD COLUMN eligible_marital_status TEXT")
        
        # Now check Employee table for marital_status
        cur.execute("PRAGMA table_info(Employee)")
        emp_cols = [row[1] for row in cur.fetchall()]
        
        if 'marital_status' not in emp_cols:
            print("[MIGRATION] Adding marital_status column to Employee...")
            cur.execute("ALTER TABLE Employee ADD COLUMN marital_status TEXT")
        
        # Now let's set default values for existing leave types based on their names
        cur.execute("SELECT leave_type_id, type_name FROM Leave_Type")
        leave_types = cur.fetchall()
        
        for lt in leave_types:
            lt_id, lt_name = lt
            eligible_genders = None
            eligible_marital = None
            
            lt_name_lower = lt_name.lower()
            
            if 'maternity' in lt_name_lower:
                eligible_genders = 'Female'
            elif 'paternity' in lt_name_lower:
                eligible_genders = 'Male'
            # Add other gender-specific leaves here if needed
            
            # Update the leave type
            cur.execute("""
                UPDATE Leave_Type 
                SET eligible_genders=?, eligible_marital_status=? 
                WHERE leave_type_id=?
            """, (eligible_genders, eligible_marital, lt_id))
        
        con.commit()
        print("[OK] Leave type eligibility migration completed!")
        return True
    except sqlite3.Error as e:
        print(f"[ERROR] Leave eligibility migration failed: {e}")
        con.rollback()
        return False
    finally:
        con.close()

if __name__ == '__main__':
    print("=" * 60)
    print("SmartHR Database Migration Tool")
    print("=" * 60)
    
    success = True
    
    # Run all migrations
    if not migrate_add_branch_address_fields():
        success = False
    
    if not migrate_add_notification_and_ic_access():
        success = False
    
    if not migrate_add_invoice_currency_fields():
        success = False
    
    if not migrate_add_leave_type_eligibility():
        success = False
    
    if success:
        print("\n[SUCCESS] All migrations completed successfully!")
        print("You can now run the application with new features.")
    else:
        print("\n[FAILED] Some migrations did not complete. Please check the errors above.")
    print("=" * 60)
