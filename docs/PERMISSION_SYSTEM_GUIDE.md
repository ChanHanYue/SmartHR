# SmartHR - Automatic Permission System Guide

## Overview
This document explains the automatic permission assignment system that grants or revokes permissions when employees are promoted or demoted.

---

## Architecture

### Database Tables

#### 1. **Permission** Table
Stores all available permissions in the system.

```sql
CREATE TABLE Permission (
    permission_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    permission_name TEXT NOT NULL UNIQUE,  -- e.g., 'view_employees', 'approve_leave'
    description     TEXT,
    module_name     TEXT,                  -- e.g., 'employees', 'leave', 'payroll'
    created_at      TEXT DEFAULT (datetime('now'))
);
```

#### 2. **Role_Permission** Table
Maps roles to permissions (many-to-many relationship).

```sql
CREATE TABLE Role_Permission (
    role_id         INTEGER NOT NULL,
    permission_id   INTEGER NOT NULL,
    granted_at      TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id)       REFERENCES Role(role_id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES Permission(permission_id) ON DELETE CASCADE
);
```

#### 3. **Employee_Permission** Table
Tracks individual employee permissions and their assignment history.

```sql
CREATE TABLE Employee_Permission (
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
```

---

## Available Permissions by Role

### 1. **Admin** - Full System Access
```
✅ view_employees          - View employee list and details
✅ add_employee            - Create new employees
✅ edit_employee           - Edit employee information
✅ delete_employee         - Delete/deactivate employees
✅ view_payroll            - View payroll information
✅ generate_payroll        - Generate payroll records
✅ apply_leave             - Apply for leave
✅ view_leave              - View own leave balance
✅ approve_leave           - Approve leave requests
✅ view_all_leave          - View all employee leave records
✅ view_attendance         - View own attendance
✅ view_all_attendance     - View all attendance records
✅ manual_attendance       - Create manual attendance records
✅ submit_invoice          - Submit expense invoices
✅ view_invoice            - View own invoices
✅ approve_invoice         - Approve invoices
✅ view_all_invoice        - View all invoices
✅ manage_organization     - Manage org structure (branches, departments)
✅ manage_roles            - Manage roles and permissions
✅ view_reports            - View reports
✅ generate_reports        - Generate custom reports
✅ view_audit_log          - View audit logs
✅ manage_audit_log        - Archive audit logs
✅ access_dashboard        - Access main dashboard
✅ view_analytics          - View analytics and statistics
```

### 2. **HR** - Personnel & Payroll Management
```
✅ view_employees
✅ edit_employee
✅ view_payroll
✅ generate_payroll
✅ approve_leave
✅ view_all_leave
✅ view_all_attendance
✅ manual_attendance
✅ approve_invoice
✅ view_all_invoice
✅ manage_organization
✅ view_reports
✅ generate_reports
✅ view_audit_log
✅ access_dashboard
```

### 3. **Manager** - Team Oversight
```
✅ view_employees
✅ apply_leave
✅ view_leave
✅ approve_leave
✅ view_attendance
✅ view_all_attendance
✅ submit_invoice
✅ view_invoice
✅ approve_invoice
✅ view_reports
✅ access_dashboard
✅ view_analytics
```

### 4. **Employee** - Standard Access
```
✅ apply_leave
✅ view_leave
✅ view_attendance
✅ submit_invoice
✅ view_invoice
✅ access_dashboard
```

---

## Automatic Permission Assignment

### When Does Permission Assignment Occur?

#### 1. **New Employee Creation**
When an admin/HR creates a new employee:
- All permissions for the selected role are automatically granted
- Entry is added to `Employee_Permission` with `reason='initial_role_assignment'`
- Audit log entry records the creation with the assigned role

#### 2. **Employee Promotion/Demotion**
When an admin/HR edits an employee and changes their role:
- The system detects the role change
- All old permissions are revoked (marked as `is_active=0`)
- All new permissions are granted based on the new role
- Audit log records `PROMOTE_DEMOTE` action with old and new role names
- User receives a success message confirming the permission change

#### 3. **Database Initialization**
When `init_db.py` is run:
- All permissions and role-permission mappings are seeded
- Existing seed employees are assigned permissions based on their roles

---

## Implementation Details

### Helper Functions in `app/database.py`

#### `assign_role_permissions(employee_id, role_id, current_user_id=None)`
```python
def assign_role_permissions(employee_id, role_id, current_user_id=None):
    """
    Assign all permissions for a role to an employee.
    Revokes old permissions and grants new ones based on the role.
    """
    # 1. Gets all permissions for the role from Role_Permission
    # 2. Revokes all currently active permissions for the employee
    # 3. Grants all permissions for the new role
    # 4. Records who granted the permissions (current_user_id)
```

#### `get_role_permissions(role_id)`
```python
def get_role_permissions(role_id):
    """Get all permissions for a given role."""
    # Returns list of permissions with names, descriptions, and module
```

#### `has_permission(employee_id, permission_name)`
```python
def has_permission(employee_id, permission_name):
    """Check if an employee has a specific permission."""
    # Returns True/False
```

#### `get_employee_permissions(employee_id)`
```python
def get_employee_permissions(employee_id):
    """Get all active permissions for an employee."""
    # Returns list of all active employee permissions
```

### Modified Routes

#### `add_employee()` in `app/employees/routes.py`
```python
# After creating the employee:
assign_role_permissions(emp_id, int(f['role_id']), session.get('user_id'))
```

#### `edit_employee()` in `app/employees/routes.py`
```python
# Detects role changes:
if old_role_id != new_role_id:
    assign_role_permissions(emp_id, new_role_id, session.get('user_id'))
    # Logs PROMOTE_DEMOTE action with role details
```

---

## Audit Trail

All permission changes are logged in the `AuditLog` table:

### Creation Example
```
action: CREATE
module_name: Employee
description: Created employee Jane Smith with role HR
target_table: Employee
target_record_id: 15
action_details: {"email": "jane@smarthr.my", "role": "HR"}
```

### Promotion Example
```
action: PROMOTE_DEMOTE
module_name: Employee
description: Employee role changed from Employee to Manager; permissions auto-updated
target_table: Employee
target_record_id: 8
action_details: {"old_role": "Employee", "new_role": "Manager"}
```

---

## Usage Examples

### Scenario 1: Creating a New Employee
```
1. Admin goes to: /employees/add
2. Fills form and selects "HR" role
3. Submits the form
4. System creates employee with all HR permissions
5. Success message: "Employee 'John Doe' added successfully with HR permissions!"
6. Audit log records the creation with role
```

### Scenario 2: Promoting an Employee
```
1. Admin goes to: /employees/5/view
2. Clicks "Edit" button
3. Changes role from "Employee" to "Manager"
4. Submits the form
5. System:
   - Revokes all Employee permissions
   - Grants all Manager permissions
   - Records promotion in audit log
6. Success message: "Employee updated successfully. Role changed to Manager; permissions granted automatically."
```

### Scenario 3: Demoting an Employee
```
1. Admin edits employee and changes role from "Manager" to "Employee"
2. System:
   - Revokes all Manager permissions
   - Grants all Employee permissions
   - Logs the change
3. Employee loses approval rights, report access, etc. immediately
```

---

## Permission Checking (Future Implementation)

To enforce permissions in routes:

```python
from app.database import has_permission

@some_bp.route('/protected')
@login_required
def protected_route():
    if not has_permission(session['user_id'], 'approve_leave'):
        abort(403)  # Forbidden
    
    # Route logic here
```

---

## Database Migration

If adding this system to an existing database:

```bash
# The schema.sql will automatically create the new tables
# Run migration script to seed permissions for existing employees

python migrate_permissions.py
```

---

## FAQ

**Q: Can an employee have permissions outside their role?**
A: Currently no, but the `Employee_Permission` table allows for future manual overrides with the `reason` field.

**Q: What happens to permission history when an employee is promoted?**
A: All changes are tracked in `Employee_Permission` with `granted_at`, `revoked_at`, and `is_active` fields. Audit logs record all changes.

**Q: Can permissions be customized per role?**
A: Yes, by modifying the `Role_Permission` mappings in the database directly or via a future admin interface.

**Q: What if Role_Permission data is missing?**
A: A role with no permissions will grant the employee no permissions (least privilege principle).

---

## Testing Permission System

To test if permissions are working:

```sql
-- Check permissions for an employee
SELECT p.permission_name, p.description 
FROM Employee_Permission ep
JOIN Permission p ON ep.permission_id = p.permission_id
WHERE ep.employee_id = 1 AND ep.is_active = 1
ORDER BY p.module_name, p.permission_name;

-- Check role permissions
SELECT p.permission_name 
FROM Role_Permission rp
JOIN Permission p ON rp.permission_id = p.permission_id
WHERE rp.role_id = 2  -- HR role
ORDER BY p.permission_name;
```

---

## Summary

✅ **Automatic Permission Assignment**: Done
✅ **Role-Based Permissions**: Defined for all 4 roles
✅ **Audit Trail**: Logged in AuditLog table
✅ **Permission Revocation**: Old permissions revoked on role change
✅ **Future Extensibility**: Tables support custom permissions and overrides
