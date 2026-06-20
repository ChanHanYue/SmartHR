import sys
sys.stdout.reconfigure(encoding='utf-8')

from jinja2 import Environment, FileSystemLoader, DebugUndefined

env = Environment(
    loader=FileSystemLoader('templates'),
    undefined=DebugUndefined
)

# Stub url_for so Jinja doesn't error on it
def url_for(endpoint, **kwargs):
    return f'/stub/{endpoint}'

env.globals['url_for'] = url_for

test_cases = [
    {'user_role': 'Admin',    'user_name': 'Admin User',    'user_initials': 'AU', 'company_id': 1, 'user_id': 1, 'branch_id': 1},
    {'user_role': 'HR',       'user_name': 'HR User',       'user_initials': 'HU', 'company_id': 1, 'user_id': 2, 'branch_id': 1},
    {'user_role': 'Manager',  'user_name': 'Manager User',  'user_initials': 'MU', 'company_id': 1, 'user_id': 3, 'branch_id': 1},
    {'user_role': 'Employee', 'user_name': 'Emp User',      'user_initials': 'EU', 'company_id': 1, 'user_id': 4, 'branch_id': 1},
]

template = env.get_template('dashboard.html')

all_ok = True
for sess in test_cases:
    try:
        html = template.render(
            session=sess,
            request=type('R', (), {'endpoint': 'main.dashboard', 'blueprint': 'main'})(),
            total_emp=10, on_leave=2, pending_leaves=3, pending_invoices=1,
            activity=[], pending_q=[], dept_dist=[],
            has_unread_notifications=False, header_notifications=[],
            get_flashed_messages=lambda **kw: []
        )
        opens = html.count('<div')
        closes = html.count('</div')
        nav_open = html.count('<nav')
        nav_close = html.count('</nav')
        div_balanced = opens == closes
        nav_balanced = nav_open == nav_close
        status = 'OK' if div_balanced and nav_balanced else 'BROKEN'
        if not (div_balanced and nav_balanced):
            all_ok = False
        print(f"{sess['user_role']:10s} [{status}]: divs {opens}/{closes} balanced={div_balanced}, nav {nav_open}/{nav_close} balanced={nav_balanced}")
    except Exception as e:
        all_ok = False
        print(f"{sess['user_role']:10s} [ERROR]: {e}")

print()
print("Overall result:", "ALL ROLES PASS" if all_ok else "SOME ROLES HAVE ISSUES")
