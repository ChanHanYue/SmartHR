"""app/organization/routes.py – Company / Branch / Department / Role management"""
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash
)
from app.database import query, execute, log_audit
from app.auth.routes import login_required, role_required

org_bp = Blueprint('organization', __name__, url_prefix='/organization')

# ----------------------------------------------------------------------
# Helper to get company_id from session (used for HR views)
# ----------------------------------------------------------------------
def _get_company_id():
    return session.get('company_id')

# ----------------------------------------------------------------------
# Redirect old index to company list
# ----------------------------------------------------------------------
@org_bp.route('/')
@login_required
def index():
    return redirect(url_for('organization.companies'))

# ======================================================================
# COMPANIES
# ======================================================================
@org_bp.route('/companies')
@login_required
@role_required('Admin', 'HR')
def companies():
    """List companies with branch and employee counts."""
    # For Admin: show all companies; for HR: show only their own company
    if session.get('user_role') == 'Admin':
        rows = query("""
            SELECT
                c.*,
                COUNT(DISTINCT b.branch_id) AS branch_count,
                COUNT(DISTINCT e.employee_id) AS employee_count
            FROM Company c
            LEFT JOIN Branch b ON b.company_id = c.company_id
            LEFT JOIN Employee e ON e.company_id = c.company_id
                AND e.employment_status != 'Terminated'
            GROUP BY c.company_id
            ORDER BY c.name
        """)
    else:
        co = _get_company_id()
        rows = query("""
            SELECT
                c.*,
                COUNT(DISTINCT b.branch_id) AS branch_count,
                COUNT(DISTINCT e.employee_id) AS employee_count
            FROM Company c
            LEFT JOIN Branch b ON b.company_id = c.company_id
            LEFT JOIN Employee e ON e.company_id = c.company_id
                AND e.employment_status != 'Terminated'
            WHERE c.company_id = ?
            GROUP BY c.company_id
        """, (co,))
    companies = [dict(row) for row in rows]
    return render_template('organization/company_list.html', companies=companies)


@org_bp.route('/company/add', methods=['GET', 'POST'])
@login_required
@role_required('Admin')   # Only Admin can create new companies
def add_company():
    if request.method == 'POST':
        f = request.form
        name = f.get('name', '').strip()
        if not name:
            flash('Company name is required.', 'danger')
            return redirect(url_for('organization.add_company'))
        if len(name) < 2 or len(name) > 150:
            flash('Company name must be 2-150 characters.', 'danger')
            return redirect(url_for('organization.add_company'))
            
        address = f.get('address', '').strip()
        contact = f.get('contact_no', '').strip()
        email = f.get('email', '').strip()
        
        # Validate email format if provided
        if email and '@' not in email:
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('organization.add_company'))
            
        cid = execute(
            "INSERT INTO Company (name, address, contact_no, email) VALUES (?,?,?,?)",
            (name, address, contact, email)
        )
        log_audit('CREATE', 'Organization', f'Added company "{name}"', 'Company', cid)
        flash(f'Company "{name}" created.', 'success')
        return redirect(url_for('organization.companies'))
    return render_template('organization/company_form.html', company=None)


@org_bp.route('/company/<int:cid>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def edit_company(cid):
    # HR can only edit their own company; Admin can edit any
    if session.get('user_role') == 'HR' and cid != _get_company_id():
        flash('You are not authorised to edit this company.', 'danger')
        return redirect(url_for('organization.companies'))

    company = query("SELECT * FROM Company WHERE company_id=?", (cid,), one=True)
    if not company:
        flash('Company not found.', 'danger')
        return redirect(url_for('organization.companies'))

    if request.method == 'POST':
        f = request.form
        name = f.get('name', '').strip()
        if not name:
            flash('Company name is required.', 'danger')
            return render_template('organization/company_form.html', company=company)
        if len(name) < 2 or len(name) > 150:
            flash('Company name must be 2-150 characters.', 'danger')
            return render_template('organization/company_form.html', company=company)
            
        address = f.get('address', '').strip()
        contact = f.get('contact_no', '').strip()
        email = f.get('email', '').strip()
        
        # Validate email format if provided
        if email and '@' not in email:
            flash('Please enter a valid email address.', 'danger')
            return render_template('organization/company_form.html', company=company)
            
        execute(
            "UPDATE Company SET name=?, address=?, contact_no=?, email=? WHERE company_id=?",
            (name, address, contact, email, cid)
        )
        log_audit('UPDATE', 'Organization', f'Updated company id={cid}', 'Company', cid)
        flash('Company updated.', 'success')
        return redirect(url_for('organization.companies'))

    return render_template('organization/company_form.html', company=company)


@org_bp.route('/company/<int:cid>/delete', methods=['POST'])
@login_required
@role_required('Admin')   # Only Admin can delete companies
def delete_company(cid):
    # Check for dependent branches
    branches = query("SELECT COUNT(*) as count FROM Branch WHERE company_id=?", (cid,), one=True)
    if branches['count'] > 0:
        flash('Cannot delete company: it has branches. Delete branches first.', 'danger')
        return redirect(url_for('organization.companies'))
    # Check for employees (even if no branches, but employees are linked to branches)
    employees = query("SELECT COUNT(*) as count FROM Employee WHERE company_id=?", (cid,), one=True)
    if employees['count'] > 0:
        flash('Cannot delete company: it has employees. Move them first.', 'danger')
        return redirect(url_for('organization.companies'))

    execute("DELETE FROM Company WHERE company_id=?", (cid,))
    log_audit('DELETE', 'Organization', f'Deleted company id={cid}', 'Company', cid)
    flash('Company deleted.', 'warning')
    return redirect(url_for('organization.companies'))


# ======================================================================
# BRANCHES
# ======================================================================
@org_bp.route('/branches')
@login_required
@role_required('Admin', 'HR')
def branches():
    """List branches, optionally filtered by company (Admin only)."""
    company_id = request.args.get('company_id', type=int)

    # If not Admin, force to own company
    if session.get('user_role') != 'Admin':
        company_id = _get_company_id()

    if company_id:
        rows = query("""
            SELECT
                b.*,
                c.name AS company_name,
                e.full_name AS manager_name
            FROM Branch b
            JOIN Company c ON c.company_id = b.company_id
            LEFT JOIN Employee e ON e.employee_id = b.hr_manager_id
            WHERE b.company_id = ?
            ORDER BY b.name
        """, (company_id,))
    else:
        rows = query("""
            SELECT
                b.*,
                c.name AS company_name,
                e.full_name AS manager_name
            FROM Branch b
            JOIN Company c ON c.company_id = b.company_id
            LEFT JOIN Employee e ON e.employee_id = b.hr_manager_id
            ORDER BY c.name, b.name
        """)

    branches = [dict(row) for row in rows]

    # For Admin filter dropdown: all companies
    companies = []
    if session.get('user_role') == 'Admin':
        companies = query("SELECT company_id, name FROM Company ORDER BY name")

    return render_template('organization/branch_list.html',
                           branches=branches,
                           companies=companies,
                           current_company=company_id)


@org_bp.route('/branch/add', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def add_branch():
    if request.method == 'POST':
        f = request.form
        name = f.get('name', '').strip()
        address_line1 = f.get('address_line1', '').strip()
        address_line2 = f.get('address_line2', '').strip()
        city = f.get('city', '').strip()
        state = f.get('state', '').strip()
        postal_code = f.get('postal_code', '').strip()
        
        # Validate required fields
        if not name:
            flash('Branch Name is required.', 'danger')
            return redirect(url_for('organization.add_branch'))
        if not address_line1:
            flash('Address Line 1 is required.', 'danger')
            return redirect(url_for('organization.add_branch'))
        if not city:
            flash('City/Region is required.', 'danger')
            return redirect(url_for('organization.add_branch'))
        if not state:
            flash('State is required.', 'danger')
            return redirect(url_for('organization.add_branch'))
        if not postal_code:
            flash('Postal Code is required.', 'danger')
            return redirect(url_for('organization.add_branch'))
        
        # Validate postal code format (5 digits)
        if not postal_code.isdigit() or len(postal_code) != 5:
            flash('Postal Code must be 5 digits.', 'danger')
            return redirect(url_for('organization.add_branch'))
        
        # Generate combined address for backward compatibility
        address_parts = [address_line1]
        if address_line2:
            address_parts.append(address_line2)
        address_parts.extend([postal_code, city, state])
        combined_address = ', '.join(address_parts)
        
        company_id = f.get('company_id')
        # HR can only add to their own company
        if session.get('user_role') == 'HR':
            company_id = _get_company_id()
        else:
            if not company_id:
                flash('Company selection is required.', 'danger')
                return redirect(url_for('organization.add_branch'))
        
        contact = f.get('contact_no', '').strip()
        hr_manager = f.get('hr_manager_id') or None
        parent = f.get('parent_branch_id') or None
        
        bid = execute(
            "INSERT INTO Branch (company_id, name, address, address_line1, address_line2, city, state, postal_code, contact_no, hr_manager_id, parent_branch_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (company_id, name, combined_address, address_line1, address_line2, city, state, postal_code, contact, hr_manager, parent)
        )
        log_audit('CREATE', 'Organization', f'Added branch "{name}"', 'Branch', bid)
        flash(f'Branch "{name}" added successfully.', 'success')
        return redirect(url_for('organization.branches'))

    # GET: populate dropdowns
    if session.get('user_role') == 'Admin':
        companies = query("SELECT company_id, name FROM Company ORDER BY name")
    else:
        co = _get_company_id()
        companies = query("SELECT company_id, name FROM Company WHERE company_id=?", (co,))

    employees = query("SELECT employee_id, full_name FROM Employee WHERE is_active=1 ORDER BY full_name")
    parent_branches = query("SELECT branch_id, name FROM Branch WHERE company_id=? ORDER BY name", (_get_company_id(),))
    return render_template('organization/branch_form.html',
                           branch=None,
                           companies=companies,
                           employees=employees,
                           parent_branches=parent_branches)


@org_bp.route('/branch/<int:bid>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def edit_branch(bid):
    branch = query("SELECT * FROM Branch WHERE branch_id=?", (bid,), one=True)
    if not branch:
        flash('Branch not found.', 'danger')
        return redirect(url_for('organization.branches'))
    # HR can only edit branches in their own company
    if session.get('user_role') == 'HR' and branch['company_id'] != _get_company_id():
        flash('You are not authorised to edit this branch.', 'danger')
        return redirect(url_for('organization.branches'))

    if request.method == 'POST':
        f = request.form
        name = f.get('name', '').strip()
        address_line1 = f.get('address_line1', '').strip()
        address_line2 = f.get('address_line2', '').strip()
        city = f.get('city', '').strip()
        state = f.get('state', '').strip()
        postal_code = f.get('postal_code', '').strip()
        
        # Validate required fields
        if not name or not address_line1 or not city or not state or not postal_code:
            flash('Branch Name, Address Line 1, City, State and Postal Code are required.', 'danger')
            companies = query("SELECT company_id, name FROM Company WHERE company_id=?", (branch['company_id'],))
            employees = query("SELECT employee_id, full_name FROM Employee WHERE is_active=1 ORDER BY full_name")
            parent_branches = query("SELECT branch_id, name FROM Branch WHERE company_id=? AND branch_id!=? ORDER BY name",
                                    (branch['company_id'], bid))
            return render_template('organization/branch_form.html',
                                   branch=branch,
                                   companies=companies,
                                   employees=employees,
                                   parent_branches=parent_branches)
        
        # Validate postal code format (5 digits)
        if not postal_code.isdigit() or len(postal_code) != 5:
            flash('Postal Code must be 5 digits.', 'danger')
            companies = query("SELECT company_id, name FROM Company WHERE company_id=?", (branch['company_id'],))
            employees = query("SELECT employee_id, full_name FROM Employee WHERE is_active=1 ORDER BY full_name")
            parent_branches = query("SELECT branch_id, name FROM Branch WHERE company_id=? AND branch_id!=? ORDER BY name",
                                    (branch['company_id'], bid))
            return render_template('organization/branch_form.html',
                                   branch=branch,
                                   companies=companies,
                                   employees=employees,
                                   parent_branches=parent_branches)
        
        # Generate combined address for backward compatibility
        address_parts = [address_line1]
        if address_line2:
            address_parts.append(address_line2)
        address_parts.extend([postal_code, city, state])
        combined_address = ', '.join(address_parts)
        
        contact = f.get('contact_no', '').strip()
        hr_manager = f.get('hr_manager_id') or None
        parent = f.get('parent_branch_id') or None
        execute(
            "UPDATE Branch SET name=?, address=?, address_line1=?, address_line2=?, city=?, state=?, postal_code=?, contact_no=?, hr_manager_id=?, parent_branch_id=? WHERE branch_id=?",
            (name, combined_address, address_line1, address_line2, city, state, postal_code, contact, hr_manager, parent, bid)
        )
        log_audit('UPDATE', 'Organization', f'Updated branch id={bid}', 'Branch', bid)
        flash('Branch updated successfully.', 'success')
        return redirect(url_for('organization.branches'))

    # GET: populate dropdowns
    companies = query("SELECT company_id, name FROM Company WHERE company_id=?", (branch['company_id'],))
    employees = query("SELECT employee_id, full_name FROM Employee WHERE is_active=1 ORDER BY full_name")
    parent_branches = query("SELECT branch_id, name FROM Branch WHERE company_id=? AND branch_id!=? ORDER BY name",
                            (branch['company_id'], bid))
    return render_template('organization/branch_form.html',
                           branch=branch,
                           companies=companies,
                           employees=employees,
                           parent_branches=parent_branches)


@org_bp.route('/branch/<int:bid>/delete', methods=['POST'])
@login_required
@role_required('Admin', 'HR')
def delete_branch(bid):
    # Get branch info
    branch = query("SELECT * FROM Branch WHERE branch_id=?", (bid,), one=True)
    if not branch:
        flash('Branch not found.', 'danger')
        return redirect(url_for('organization.branches'))
    
    # HR can only delete branches in their own company
    if session.get('user_role') == 'HR' and branch['company_id'] != _get_company_id():
        flash('You are not authorised to delete this branch.', 'danger')
        return redirect(url_for('organization.branches'))
    
    # Check for sub-branches
    sub = query("SELECT COUNT(*) as count FROM Branch WHERE parent_branch_id=?", (bid,), one=True)
    if sub['count'] > 0:
        flash("Cannot delete branch: It has sub-branches.", "danger")
        return redirect(url_for('organization.branches'))
    # Check for departments
    depts = query("SELECT COUNT(*) as count FROM Department WHERE branch_id=?", (bid,), one=True)
    if depts['count'] > 0:
        flash("Cannot delete branch: It has associated departments.", "danger")
        return redirect(url_for('organization.branches'))
    # Check for active employees
    emps = query("SELECT COUNT(*) as count FROM Employee WHERE branch_id=? AND is_active=1", (bid,), one=True)
    if emps['count'] > 0:
        flash("Cannot delete branch: It has active employees.", "danger")
        return redirect(url_for('organization.branches'))
    execute("DELETE FROM Branch WHERE branch_id=?", (bid,))
    log_audit('DELETE', 'Organization', f'Deleted branch id={bid}', 'Branch', bid)
    flash("Branch deleted.", "warning")
    return redirect(url_for('organization.branches'))


# ======================================================================
# DEPARTMENTS
# ======================================================================
@org_bp.route('/departments')
@login_required
@role_required('Admin', 'HR')
def departments():
    """List departments, optionally filtered by branch."""
    branch_id = request.args.get('branch_id', type=int)

    # If no filter, show all departments under the user's company (for HR)
    if session.get('user_role') == 'HR' and not branch_id:
        # Get all branches for the HR's company
        co = _get_company_id()
        rows = query("""
            SELECT
                d.*,
                b.name AS branch_name,
                COUNT(e.employee_id) AS emp_count
            FROM Department d
            JOIN Branch b ON b.branch_id = d.branch_id
            LEFT JOIN Employee e ON e.department_id = d.department_id
                AND e.employment_status != 'Terminated'
            WHERE b.company_id = ?
            GROUP BY d.department_id
            ORDER BY b.name, d.department_name
        """, (co,))
    else:
        if branch_id:
            rows = query("""
                SELECT
                    d.*,
                    b.name AS branch_name,
                    COUNT(e.employee_id) AS emp_count
                FROM Department d
                JOIN Branch b ON b.branch_id = d.branch_id
                LEFT JOIN Employee e ON e.department_id = d.department_id
                    AND e.employment_status != 'Terminated'
                WHERE d.branch_id = ?
                GROUP BY d.department_id
                ORDER BY d.department_name
            """, (branch_id,))
        else:
            # Admin viewing all departments without filter
            rows = query("""
                SELECT
                    d.*,
                    b.name AS branch_name,
                    COUNT(e.employee_id) AS emp_count
                FROM Department d
                JOIN Branch b ON b.branch_id = d.branch_id
                LEFT JOIN Employee e ON e.department_id = d.department_id
                    AND e.employment_status != 'Terminated'
                GROUP BY d.department_id
                ORDER BY b.name, d.department_name
            """)

    departments = [dict(row) for row in rows]

    # For filter dropdown: show branches (Admin sees all, HR sees only own company's branches)
    if session.get('user_role') == 'Admin':
        branches = query("SELECT branch_id, name FROM Branch ORDER BY name")
    else:
        co = _get_company_id()
        branches = query("SELECT branch_id, name FROM Branch WHERE company_id=? ORDER BY name", (co,))

    return render_template('organization/department_list.html',
                           departments=departments,
                           branches=branches,
                           current_branch=branch_id)


@org_bp.route('/department/add', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def add_department():
    if request.method == 'POST':
        f = request.form
        branch_id = f.get('branch_id')
        dept_name = f.get('department_name', '').strip()
        if not branch_id or not dept_name:
            flash('Branch and Department Name are required.', 'danger')
            return redirect(url_for('organization.add_department'))
        if len(dept_name) < 2 or len(dept_name) > 100:
            flash('Department name must be 2-100 characters.', 'danger')
            return redirect(url_for('organization.add_department'))
            
        # Check that the branch belongs to the HR's company (or admin)
        branch = query("SELECT company_id FROM Branch WHERE branch_id=?", (branch_id,), one=True)
        if not branch:
            flash('Invalid branch.', 'danger')
            return redirect(url_for('organization.add_department'))
        if session.get('user_role') == 'HR' and branch['company_id'] != _get_company_id():
            flash('You cannot add a department to a branch outside your company.', 'danger')
            return redirect(url_for('organization.add_department'))

        did = execute("INSERT INTO Department (branch_id, department_name) VALUES (?,?)",
                      (branch_id, dept_name))
        log_audit('CREATE', 'Organization', f'Added department "{dept_name}"', 'Department', did)
        flash(f'Department "{dept_name}" added.', 'success')
        return redirect(url_for('organization.departments'))

    # GET: list branches for the company
    co = _get_company_id()
    branches = query("SELECT branch_id, name FROM Branch WHERE company_id=? ORDER BY name", (co,))
    return render_template('organization/department_form.html', department=None, branches=branches)


@org_bp.route('/department/<int:did>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin', 'HR')
def edit_department(did):
    dept = query("""
        SELECT d.*, b.company_id
        FROM Department d
        JOIN Branch b ON d.branch_id = b.branch_id
        WHERE d.department_id = ?
    """, (did,), one=True)
    if not dept:
        flash('Department not found.', 'danger')
        return redirect(url_for('organization.departments'))
    # HR can only edit departments in their company
    if session.get('user_role') == 'HR' and dept['company_id'] != _get_company_id():
        flash('You are not authorised to edit this department.', 'danger')
        return redirect(url_for('organization.departments'))

    if request.method == 'POST':
        f = request.form
        new_name = f.get('department_name', '').strip()
        if not new_name:
            flash('Department name is required.', 'danger')
            branches = query("SELECT branch_id, name FROM Branch WHERE company_id=? ORDER BY name", (dept['company_id'],))
            return render_template('organization/department_form.html', department=dept, branches=branches)
        if len(new_name) < 2 or len(new_name) > 100:
            flash('Department name must be 2-100 characters.', 'danger')
            branches = query("SELECT branch_id, name FROM Branch WHERE company_id=? ORDER BY name", (dept['company_id'],))
            return render_template('organization/department_form.html', department=dept, branches=branches)
        execute("UPDATE Department SET department_name=? WHERE department_id=?", (new_name, did))
        log_audit('UPDATE', 'Organization', f'Updated department id={did}', 'Department', did)
        flash('Department updated.', 'success')
        return redirect(url_for('organization.departments'))

    # GET: branches for the same company
    branches = query("SELECT branch_id, name FROM Branch WHERE company_id=? ORDER BY name", (dept['company_id'],))
    return render_template('organization/department_form.html', department=dept, branches=branches)


@org_bp.route('/department/<int:did>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_department(did):
    # Check for active employees
    emps = query("SELECT COUNT(*) as count FROM Employee WHERE department_id=? AND is_active=1", (did,), one=True)
    if emps['count'] > 0:
        flash("Cannot delete department: It has active employees.", "danger")
        return redirect(url_for('organization.departments'))
    execute("DELETE FROM Department WHERE department_id=?", (did,))
    log_audit('DELETE', 'Organization', f'Deleted department id={did}', 'Department', did)
    flash("Department deleted.", "warning")
    return redirect(url_for('organization.departments'))


# ======================================================================
# ROLES (view only)
# ======================================================================
@org_bp.route('/roles')
@login_required
@role_required('Admin', 'HR')
def roles():
    """List roles with employee counts."""
    rows = query("""
        SELECT r.role_id, r.role_name,
               COUNT(e.employee_id) as employee_count
        FROM Role r
        LEFT JOIN Employee e ON r.role_id = e.role_id AND e.is_active=1
        GROUP BY r.role_id
        ORDER BY r.role_id
    """)
    roles = [dict(row) for row in rows]
    return render_template('organization/role_list.html', roles=roles)