
import sqlite3
import os

db_path = os.path.join('instance', 'smarthr.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("Employees:")
cursor.execute("SELECT employee_id, full_name, gender FROM Employee")
for emp in cursor.fetchall():
    print(dict(emp))

conn.close()
