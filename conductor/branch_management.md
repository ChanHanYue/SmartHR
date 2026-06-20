# Plan - Branch Management Module Implementation
    2
    3 ## Objective
    4 Implement full lifecycle management for Branches (Add, Edit, Delete) in the SmartHR system, as per the functional
      requirements in section 1.4.2 of the project documentation. Ensure the module is robust, safe, and extensible for
      future expansion (hierarchies).
    5
    6 ## Key Files & Context
    7 - `app/organization/routes.py`: Logic for company, branch, and department management.
    8 - `templates/organization/index.html`: Main UI for organization management.
    9 - `schema.sql`: Defines the `Branch` table structure.
   10 - `instance/smarthr.db`: The live SQLite database.
   11
   12 ## Implementation Steps
   13
   14 ### 1. Database Schema Update
   15 - Modify `schema.sql` to include `parent_branch_id` in the `Branch` table.
   16 - Update the live database: `ALTER TABLE Branch ADD COLUMN parent_branch_id INTEGER REFERENCES Branch(branch_id);`
   17
   18 ### 2. Backend Logic (`app/organization/routes.py`)
   19 - **Add Branch**: Update `add_branch` to optionally accept `parent_branch_id`.
   20 - **Edit Branch**: Update `edit_branch` to handle `parent_branch_id` and other metadata.
   21 - **Delete Branch**: Implement a new `delete_branch` route:
   22     - Block deletion if the branch has sub-branches, departments, or active employees.
   23     - Log the audit event upon success.
   24 - **Audit Logging**: Use `log_audit` for all operations.
   25
   26 ### 3. Frontend UI (`templates/organization/index.html`)
   27 - **Branches Table**: Add "Action" column with Edit/Delete buttons.
   28 - **Modals**:
   29     - Add Parent Branch selection to "Add Branch" modal.
   30     - Implement "Edit Branch" modal with pre-filled values.
   31 - **JavaScript**: Add helper functions to handle modal data population.
   32
   33 ## Verification & Testing
   34 1. **Hierarchical Setup**: Create a Main Office and a Sub-branch, then verify the link in the DB.
   35 2. **Safety Check**: Attempt to delete a branch with a department and verify it fails with a warning.
   36 3. **Audit Verification**: Ensure all actions appear in the system audit log.