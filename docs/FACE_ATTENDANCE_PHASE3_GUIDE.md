# Face Recognition - Phase 3: Attendance Reports & Analytics

## 🎯 Overview

Phase 3 implements **comprehensive attendance reporting and analytics** with interactive dashboards, charts, and export capabilities. This allows employees to view personal attendance history and HR/managers to analyze team performance.

✅ Filtered attendance reports  
✅ Interactive analytics dashboard  
✅ Real-time KPIs & statistics  
✅ CSV export  
✅ Multi-level filtering (date, branch, dept, employee)  
✅ Top performers analysis  
✅ Daily/departmental trends  

---

## 📋 Prerequisites

### Phase 1 & 2 Must Be Complete
- ✅ Face registration working
- ✅ Real-time face attendance work
- ✅ Attendance records being created

### Install Dependencies
```bash
pip install -r requirements.txt
```

No new Python packages needed! Phase 3 uses:
- Chart.js (loaded via CDN) - browser charts
- Built-in Flask CSV module
- SQLite queries (no external DB tools)

---

## 🚀 Quick Start

### 1. Verify Earlier Phases Working
```bash
# Start app
python run.py

# Test face registration (HR)
# Login: hr@smarthr.my / Hr@123
# Register faces for 2-3 employees

# Test face attendance (Employee)
# Login: elizabeth@smarthr.my / Employee@123
# Do some check-ins/outs
```

### 2. Access Reports

#### Employee Personal Report
```
URL: http://localhost:5000/face/reports
- Logged-in employee sees ONLY their records
- Can filter by date range
- Can export their CSV
```

#### HR/Manager Analytics Dashboard
```
URL: http://localhost:5000/face/analytics
- See all employees across org
- Filter by branch, department, date
- Real-time KPIs & charts
- Top performer rankings
```

#### Detailed Team Report
```
URL: http://localhost:5000/face/reports (as HR/Manager)
- All employees in organization
- Full filtering options
- CSV export with all details
```

---

## 📁 Files Created/Modified

### New Files (Phase 3)
```
app/face/
├── reports.py              ← Report generation logic
│   ├── get_attendance_records()    - Query with filters
│   ├── calculate_statistics()      - KPI calculations
│   ├── get_daily_stats()          - Daily breakdown
│   └── get_employee_stats()       - Employee performance

templates/face/
├── attendance_report.html   ← Detailed report viewer
│   ├── Filters panel
│   ├── Statistics cards
│   ├── Records table
│   └── CSV export
└── attendance_analytics.html ← Analytics dashboard
    ├── KPI cards
    ├── Daily trend chart
    ├── Hourly distribution
    ├── Department breakdown
    └── Top performers list
```

### Routes Added
```
GET /face/reports              → Attendance report page
GET /face/api/report_data      → Report data API
GET /face/export/csv           → CSV download
GET /face/analytics            → Analytics dashboard
GET /face/api/analytics_data   → Analytics API
```

---

## 🔌 API Endpoints (Phase 3)

### 1. Get Attendance Report Data
```
GET /face/api/report_data
```

**Query Parameters:**
```
from_date=2026-05-15       // Optional
to_date=2026-06-15         // Optional
employee_id=4              // Optional (HR only)
branch_id=1                // Optional
department_id=1            // Optional
status=Approved            // Optional: Approved/Pending/Flagged
manual_only=false          // Optional: true for manual entries only
```

**Response:**
```json
{
  "success": true,
  "records": [
    {
      "attendance_id": 1,
      "employee_id": 4,
      "full_name": "Elizabeth Lopez",
      "position": "Operations Executive",
      "branch_name": "KL Headquarters",
      "department_name": "Operations",
      "check_in": "2026-06-15 09:15:30",
      "check_out": "2026-06-15 18:00:00",
      "hours_worked": 8.75,
      "overtime_hours": 0.75,
      "status": "Approved",
      "manual": false
    }
  ],
  "statistics": {
    "total_records": 42,
    "total_hours": 340.5,
    "total_overtime": 8.5,
    "avg_hours_per_day": 8.14,
    "days_present": 42,
    "on_time_count": 38,
    "late_count": 4
  },
  "daily_breakdown": [
    {
      "date": "2026-06-15",
      "present": 10,
      "total_hours": 82.5,
      "employees": 10
    }
  ],
  "employee_breakdown": [
    {
      "employee_id": 4,
      "full_name": "Elizabeth Lopez",
      "position": "Operations Executive",
      "check_ins": 42,
      "total_hours": 340.5,
      "avg_hours": 8.1
    }
  ]
}
```

---

### 2. Get Analytics Data
```
GET /face/api/analytics_data
```

**Query Parameters:**
```
from_date=2026-05-15       // Optional
to_date=2026-06-15         // Optional
branch_id=1                // Optional
department_id=1            // Optional
```

**Response:**
```json
{
  "success": true,
  "statistics": {
    "total_records": 420,
    "total_hours": 3405,
    "avg_hours_per_day": 8.14,
    "days_present": 42,
    "on_time_count": 380,
    "late_count": 40
  },
  "daily_breakdown": [
    {
      "date": "2026-06-15",
      "present": 10,
      "total_hours": 82.5,
      "employees": 10
    }
  ],
  "employee_breakdown": [
    {
      "employee_id": 4,
      "full_name": "Elizabeth Lopez",
      "check_ins": 42,
      "total_hours": 340.5,
      "avg_hours": 8.1
    }
  ],
  "department_breakdown": [
    {
      "department": "Operations",
      "employee_count": 3,
      "records": 126,
      "total_hours": 1020.75
    }
  ]
}
```

---

### 3. Export as CSV
```
GET /face/export/csv
```

**Query Parameters:** Same as report_data

**Response:** CSV file download
```
Employee ID,Full Name,Position,Branch,Department,Date,Check In,Check Out,Hours Worked,Overtime,Status,Manual Entry
4,Elizabeth Lopez,Operations Executive,KL Headquarters,Operations,2026-06-15,09:15:30,18:00:00,8.75,0.75,Approved,No
```

---

## 📊 Features Breakdown

### Attendance Report Page (`/face/reports`)

#### For Employees
- View **personal attendance history**
- Filter by date range (from → to)
- Statistics: Total hours, avg/day, days present
- Manual entry detection (badge)
- Approval status display
- Export personal CSV

#### For HR/Managers
- View **all employees** in organization
- Filter by:
  - Date range (from/to)
  - Specific employee
  - Branch
  - Department
  - Status (Approved/Pending/Flagged)
  - Manual entries only
- Statistics panel with KPIs
- Detailed records table
- Bulk export as CSV

**UI Elements:**
```
┌───────────────────────────────────────────┐
│ 📊 Attendance Report                      │
├───────────────────────────────────────────┤
│ 🔍 Filters:                               │
│  [From] [To] [Employee▼] [Branch▼]       │
│  [Dept▼] [Status▼] [Manual?] [Reset]     │
├───────────────────────────────────────────┤
│ Statistics:                               │
│  Total: 42 | Hours: 340.5h | Days: 42    │
│  Avg: 8.1h/day | On-time: 38/42          │
├───────────────────────────────────────────┤
│ 📋 Records Table:                         │
│ Employee | Branch | Date | In | Out | Hrs│
│ ─────────────────────────────────────────│
│ Elizabeth| KL HQ  | 6/15 | 9:15| 18:00| 8.75│
└───────────────────────────────────────────┘
```

---

### Analytics Dashboard (`/face/analytics`)

#### Access
- HR/Admin/Manager only
- Employees redirected to report page

#### KPI Cards (6 metrics)
- **Total Check-Ins:** All recorded attendance
- **Total Hours Logged:** Sum of hours worked
- **Days Present:** Unique dates with attendance
- **Avg Hours/Day:** Total hours / days
- **On Time:** Records with >= 8 hours
- **Late:** Records with < 8 hours

#### Charts (3 interactive)

1. **Daily Attendance Trend** (Line chart, dual-axis)
   - X-axis: Date
   - Left Y: Check-ins per day
   - Right Y: Total hours per day
   - Shows patterns over time

2. **Top Employees by Hours** (Horizontal bar chart)
   - Top 10 employees
   - Average hours per check-in
   - Visual comparison

3. **Department Breakdown** (Doughnut chart)
   - Each department's proportion
   - Total hours per department
   - Color-coded

#### Employee Ranking
- Top 15 employees by total hours
- Shows: Name, check-ins, total hours, avg hours/day
- Badges for quick stat lookup

**UI Elements:**
```
┌──────────────────────────────────────────────┐
│ 📈 Analytics Dashboard                       │
├──────────────────────────────────────────────┤
│ 🔍 Filters: [From] [To] [Branch▼] [Dept▼]  │
├──────┬──────────┬────────┬────────┬──────────┤
│ 420  │ 3,405h   │ 42 days│ 8.14h  │ 380 OK  │
│ Total│ Hours    │ Present│ Avg/Day│ On-time │
├──────────────────────────────────────────────┤
│ Graph1: Daily Trend        │ Graph3: Depts   │
│ (Time-series line)        │ (Donut)         │
├──────────────────────────────────────────────┤
│ Graph2: Top Employees (horizontal bar)       │
├──────────────────────────────────────────────┤
│ Top Performers:                              │
│ Elizabeth Lopez    │ 42 check-ins │ 340.5h  │
│ Ryan Tan          │ 40 check-ins │ 325.0h  │
└──────────────────────────────────────────────┘
```

---

## 🧪 Testing Checklist

### Test Case 1: Employee Report
- [ ] Login as employee (elizabeth@smarthr.my)
- [ ] Navigate to `/face/reports`
- [ ] See only own attendance records
- [ ] Cannot filter by other employees
- [ ] Apply date range filter
- [ ] Export CSV with only own data
- [ ] Verify CSV has correct format

### Test Case 2: HR Report Complex Filters
- [ ] Login as HR (hr@smarthr.my)
- [ ] Go to `/face/reports`
- [ ] See all employees in dropdown
- [ ] Filter by: branch, department, date range
- [ ] Filter by status (Approved/Pending)
- [ ] Filter manual entries only (checkbox)
- [ ] Combine multiple filters
- [ ] Export filtered CSV
- [ ] Verify CSV includes all filtered records

### Test Case 3: Analytics Dashboard
- [ ] Login as manager/HR
- [ ] Navigate to `/face/analytics`
- [ ] See KPI cards populate
- [ ] Chart 1: Daily trend shows data
- [ ] Chart 2: Top employees bar chart
- [ ] Chart 3: Department doughnut chart
- [ ] Apply date range filter
- [ ] Charts update dynamically
- [ ] Employee ranking shows top 15

### Test Case 4: CSV Export Format
- [ ] Export from both report & analytics
- [ ] Open CSV in Excel/Sheets
- [ ] Headers correct: Employee ID, Name, Branch, etc.
- [ ] Date/time format readable
- [ ] No encoding issues
- [ ] Manual entry column shows Yes/No
- [ ] Status column shows Approved/Pending

### Test Case 5: Statistics Accuracy
- [ ] Create 5 test attendance records manually
- [ ] Go to report page
- [ ] Verify:
     - Total records = 5
     - Total hours = sum of hours_worked
     - Days present = unique dates
     - On-time/late count matches criteria (>=8 / <8)
- [ ] Analytics dashboard shows same stats

### Test Case 6: Responsive Design
- [ ] View reports on desktop (1920x1080)
- [ ] View reports on tablet (iPad)
- [ ] View reports on mobile (iPhone)
- [ ] All filters accessible on mobile
- [ ] Charts responsive and readable
- [ ] No horizontal overflow

---

## 📊 Data Queries

### SQL: Total Hours by Employee (Last 30 Days)
```sql
SELECT 
    e.full_name,
    COUNT(a.attendance_id) as check_ins,
    SUM(a.hours_worked) as total_hours,
    AVG(a.hours_worked) as avg_hours
FROM Attendance a
JOIN Employee e ON a.employee_id = e.employee_id
WHERE date(a.check_in) >= date('now', '-30 days')
GROUP BY e.employee_id
ORDER BY total_hours DESC;
```

### SQL: Daily Breakdown
```sql
SELECT 
    date(a.check_in) as date,
    COUNT(DISTINCT a.employee_id) as employees_present,
    COUNT(a.attendance_id) as check_ins,
    SUM(a.hours_worked) as total_hours
FROM Attendance a
WHERE date(a.check_in) >= date('now', '-30 days')
GROUP BY date(a.check_in)
ORDER BY date DESC;
```

### SQL: Manual vs Automatic Entries
```sql
SELECT 
    a.is_manual_entry,
    COUNT(*) as count,
    SUM(a.hours_worked) as total_hours
FROM Attendance a
WHERE date(a.check_in) >= date('now', '-30 days')
GROUP BY a.is_manual_entry;
```

---

## 🔒 Security & Access Control

### Role-Based Access
- **Employee:** View only own attendance (API enforced)
- **Manager:** View branch/department attendance
- **HR/Admin:** View all attendance across organization

### Data Privacy
- Employees can't access other employees' data
- Server-side filtering prevents SQL injection
- All dates/times sanitized
- CSV export respects permissions

### Audit Trail
All report access logged in AuditLog (if implemented):
```
Action: VIEW_REPORT
Module: Attendance
Description: Employee 4 viewed attendance report
Target: Attendance table
IP: 192.168.1.x
```

---

## 🐛 Common Issues & Fixes

| Issue | Cause | Solution |
|-------|-------|----------|
| "No records found" | Wrong date range | Adjust from/to dates to match data |
| Charts not rendering | JavaScript error | Check browser console (F12) |
| CSV empty | User has no attendance | Check attendance table populated |
| Slow report load | Too many records | Narrow date range or add index |
| Export button missing | JavaScript disabled | Enable JS or use direct URL |
| "Access denied" | Wrong role | Login as HR/Manager for analytics |

---

## 📈 Performance Optimization

### Indexes Recommended
```sql
CREATE INDEX idx_attendance_date ON Attendance(check_in);
CREATE INDEX idx_attendance_emp_date ON Attendance(employee_id, check_in);
CREATE INDEX idx_attendance_branch ON Attendance(branch_id);
```

### Query Optimization
- Date filters use indexed columns
- Aggregations done server-side (not browser)
- Chart data limited to last 90 days by default
- Employee list capped at top 15

### Caching Strategy (Optional)
- Cache daily stats for 1 hour
- Cache department breakdowns for 2 hours
- Clear cache on new attendance record
- Implement using Redis or SQL query caching

---

## 🚀 Advanced Features (Not Implemented)

Future enhancements:
- **Predictive Analytics:** Forecast attendance patterns
- **Anomaly Detection:** Flag unusual attendance
- **Email Reports:** Scheduled automatic emails
- **PDF Export:** Formatted reports with logos
- **Data Validation:** Check for impossible times
- **Shift Analysis:** Track by shift (morning/evening)
- **Approval Workflow:** HR approve pending records
- **Undo/Rollback:** Revert attendance changes

---

## 📗 Database Schema (Phase 3 Compatible)

No schema changes required! Phase 3 uses existing tables:

**Attendance Table (already has all needed columns):**
```sql
- attendance_id (PK)
- employee_id (FK)
- check_in (datetime)
- check_out (datetime, nullable)
- hours_worked (decimal)
- overtime_hours (decimal)
- status (text)
- is_manual_entry (boolean)
```

**Employee/Branch/Department:** Standard references

---

## 🎯 Testing with Python

```python
# Test query in Python
from app.database import get_db_connection

conn = get_db_connection()

# Get all attendance for report
records = conn.execute("""
    SELECT a.*, e.full_name, b.name as branch_name
    FROM Attendance a
    JOIN Employee e ON a.employee_id = e.employee_id
    JOIN Branch b ON a.branch_id = b.branch_id
    WHERE date(a.check_in) >= '2026-05-15'
    ORDER BY a.check_in DESC
""").fetchall()

print(f"Total records: {len(records)}")
for rec in records:
    print(f"{rec['full_name']} - {rec['hours_worked']}h on {rec['check_in']}")

conn.close()
```

---

## 📞 Support & Debugging

### Enable Debug Mode
In Flask app:
```python
app.config['DEBUG'] = True
```

### Check Browser Console
Press F12 → Console tab to see JavaScript errors

### Server Logs
```bash
# Run with verbose logging
python run.py 2>&1 | tee app.log
```

### Inspect Database
```bash
sqlite3 instance/smarthr.db
.mode column
SELECT COUNT(*) FROM Attendance;
SELECT * FROM Attendance LIMIT 5;
```

---

## ✅ Phase 3 Complete Checklist

- [ ] Phase 1 & 2 prerequisites met
- [ ] `app/face/reports.py` created with all functions
- [ ] `templates/face/attendance_report.html` created
- [ ] `templates/face/attendance_analytics.html` created
- [ ] CSV export working
- [ ] Charts rendering with data
- [ ] Filters working (date, employee, branch, dept, status)
- [ ] Statistics calculations accurate
- [ ] Employee report only shows own data
- [ ] HR/Manager dashboard working
- [ ] Responsive design tested on mobile
- [ ] CSV format correct and importable
- [ ] All edge cases tested

---

## 🎯 Next Steps

### Already Implemented
✅ Phase 1: Face Registration  
✅ Phase 2: Real-Time Attendance  
✅ Phase 3: Reports & Analytics  

### Future Best Practices
- Implement email notification system
- Add advanced security (2FA, device fingerprinting)
- Create mobile app for attendance
- Integrate with payroll system
- Implement leave auto-approval rules
- Add overtime tracking & approval
- Create supervisor dashboard

---

## 📚 Files Reference

| File | Purpose |
|------|---------|
| `app/face/reports.py` | Report generation logic |
| `templates/face/attendance_report.html` | Report viewer UI |
| `templates/face/attendance_analytics.html` | Analytics dashboard UI |
| `app/face/__init__.py` | Blueprint registration |
| `app/face/routes.py` | Phase 1/2 endpoints |
| `app/face/matcher.py` | Face matching logic |

---

**Version:** Phase 3.0  
**Date:** June 15, 2026  
**Status:** ✅ Ready for Testing
