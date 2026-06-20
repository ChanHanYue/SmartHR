# Permission System - Quick Reference

## What Changed?

### New Database Tables
- `Permission` - Lists all available permissions
- `Role_Permission` - Maps roles to permissions
- `Employee_Permission` - Tracks employee permissions

### Modified Routes
1. **Employee Creation** (`/employees/add`)
   - Automatically grants permissions based on selected role

2. **Employee Edit** (`/employees/<id>/edit`)
   - Detects role changes
   - Automatically revokes old permissions
   - Grants new permissions
   - Logs the change with PROMOTE_DEMOTE action

### New Helper Functions in `app/database.py`
```python
assign_role_permissions(employee_id, role_id, current_user_id=None)
get_role_permissions(role_id)
has_permission(employee_id, permission_name)
get_employee_permissions(employee_id)
```

---

## How It Works

### Step 1: Employee Created
```
Admin creates employee "John Doe" with role "Employee"
↓
System automatically grants:
  ✅ apply_leave
  ✅ view_leave
  ✅ view_attendance
  ✅ submit_invoice
  ✅ view_invoice
  ✅ access_dashboard
```

### Step 2: Employee Promoted
```
Admin edits John and changes role from "Employee" to "Manager"
↓
System:
  ❌ Revokes all Employee permissions
  ✅ Grants all Manager permissions
     - view_employees
     - approve_leave
     - view_all_attendance
     - approve_invoice
     - etc.
↓
Audit log records: PROMOTE_DEMOTE action
↓
Admin sees message: "Role changed to Manager; permissions granted automatically."
```

### Step 3: Employee Demoted
```
Admin edits John and changes role from "Manager" back to "Employee"
↓
System revokes Manager permissions and grants Employee permissions
↓
John loses all Manager-specific access immediately
```

---

## Role Permissions Summary

| Permission | Admin | HR | Manager | Employee |
|---|:---:|:---:|:---:|:---:|
| view_employees | ✅ | ✅ | ✅ | ❌ |
| add_employee | ✅ | ❌ | ❌ | ❌ |
| edit_employee | ✅ | ✅ | ❌ | ❌ |
| delete_employee | ✅ | ❌ | ❌ | ❌ |
| view_payroll | ✅ | ✅ | ❌ | ❌ |
| generate_payroll | ✅ | ✅ | ❌ | ❌ |
| apply_leave | ✅ | ✅ | ✅ | ✅ |
| view_leave | ✅ | ✅ | ✅ | ✅ |
| approve_leave | ✅ | ✅ | ✅ | ❌ |
| view_all_leave | ✅ | ✅ | ❌ | ❌ |
| view_attendance | ✅ | ✅ | ✅ | ✅ |
| view_all_attendance | ✅ | ✅ | ✅ | ❌ |
| manual_attendance | ✅ | ✅ | ❌ | ❌ |
| submit_invoice | ✅ | ✅ | ✅ | ✅ |
| view_invoice | ✅ | ✅ | ✅ | ✅ |
| approve_invoice | ✅ | ✅ | ✅ | ❌ |
| view_all_invoice | ✅ | ✅ | ❌ | ❌ |
| manage_organization | ✅ | ✅ | ❌ | ❌ |
| manage_roles | ✅ | ❌ | ❌ | ❌ |
| view_reports | ✅ | ✅ | ✅ | ❌ |
| generate_reports | ✅ | ✅ | ❌ | ❌ |
| view_audit_log | ✅ | ✅ | ❌ | ❌ |
| manage_audit_log | ✅ | ❌ | ❌ | ❌ |
| access_dashboard | ✅ | ✅ | ✅ | ✅ |
| view_analytics | ✅ | ❌ | ✅ | ❌ |

---

## Testing the System

### Test 1: Create New Employee
1. Go to `/employees/add`
2. Fill in form with role "Employee"
3. Submit
4. Check database:
   ```sql
   SELECT COUNT(*) FROM Employee_Permission 
   WHERE employee_id = [NEW_ID] AND is_active = 1;
   -- Should return 6 (Employee role permissions)
   ```

### Test 2: Promote Employee
1. Go to `/employees/[ID]/view`
2. Edit and change role from "Employee" to "Manager"
3. Submit
4. Check database:
   ```sql
   SELECT COUNT(*) FROM Employee_Permission 
   WHERE employee_id = [ID] AND is_active = 1;
   -- Should return 12 (Manager role permissions)
   
   SELECT COUNT(*) FROM Employee_Permission 
   WHERE employee_id = [ID] AND is_active = 0;
   -- Should return 6 (old Employee permissions revoked)
   ```

### Test 3: Check Audit Log
```sql
SELECT * FROM AuditLog 
WHERE action = 'PROMOTE_DEMOTE' 
ORDER BY created_at DESC LIMIT 1;
-- Should show the promotion/demotion action with role details
```

---

## Future Enhancements

1. **Permission Enforcement**
   - Add `@require_permission('permission_name')` decorator
   - Enforce permissions in all routes

2. **Custom Permissions**
   - UI to customize role permissions
   - Manual permission overrides for exceptions

3. **Permission Groups**
   - Group related permissions
   - Easier role management

4. **Department-Based Permissions**
   - Restrict manager access to specific departments
   - Fine-grained access control

5. **Permission Audit Dashboard**
   - Visual showing who has what permissions
   - Permission change history
   - Compliance reports

---

## Troubleshooting

**Problem**: Employee not getting permissions after role assignment
- **Solution**: Check if Role_Permission mappings exist for the role
- **SQL**: `SELECT * FROM Role_Permission WHERE role_id = [ROLE_ID];`

**Problem**: Old permissions not being revoked
- **Solution**: Check if is_active flag is being set to 0
- **SQL**: `SELECT * FROM Employee_Permission WHERE employee_id = [ID] AND revoked_at IS NOT NULL;`

**Problem**: Permission system not initialized
- **Solution**: Run `python init_db.py` to seed permission data
- **Check**: `SELECT COUNT(*) FROM Permission;` (should be > 20)

---

## Key Files Modified

1. **schema.sql** - Added Permission, Role_Permission, Employee_Permission tables
2. **app/database.py** - Added permission helper functions
3. **app/employees/routes.py** - Updated add_employee() and edit_employee()
4. **init_db.py** - Added permission seeding and employee permission assignment

---

## Important Notes

- ✅ Permissions are **automatically managed** - no manual intervention needed
- ✅ All permission changes are **audited** in AuditLog
- ✅ Permission changes happen **immediately** upon role change
- ✅ System uses **role-based access control (RBAC)**
- ⚠️ Enforce permissions in routes using `has_permission()` function (future work)
