import pytest
from app.payroll.calculator import calculate_proration, calculate_ot_or_leave, calculate_epf, calculate_socso

def test_proration():
    # Hire date 15th of May (30 days month - 15 + 1 = 16 days worked)
    # base 3000 -> 3000 * (16/30) = 1600
    assert calculate_proration(3000, '2026-05-15', 5, 2026) == 1600.0
    # Hired previous month, should get full base
    assert calculate_proration(3000, '2026-04-15', 5, 2026) == 3000.0

def test_ot_threshold():
    # Salary < 4000 gets OT pay
    pay, type = calculate_ot_or_leave(3000, 10)
    assert type == "OT_PAY"
    assert pay > 0
    
    # Salary > 4000 gets Replacement Leave
    pay, type = calculate_ot_or_leave(5000, 10)
    assert type == "REPLACEMENT_LEAVE"
    assert pay == 0.0

def test_statutory_caps():
    # SOCSO/EIS capped at 6000
    emp, er = calculate_socso(10000)
    capped_emp = round(6000 * 0.005, 2)
    assert emp == capped_emp
