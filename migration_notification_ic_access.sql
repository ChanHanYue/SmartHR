-- SmartHR Migration: Add Notification and IC Access Request System
-- Apply this to existing database

PRAGMA foreign_keys = ON;

-- 1. Notifications Table
CREATE TABLE IF NOT EXISTS Notification (
    notification_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id      INTEGER NOT NULL,
    title            TEXT NOT NULL,
    message          TEXT NOT NULL,
    is_read          INTEGER DEFAULT 0,
    created_at       TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (employee_id) REFERENCES Employee(employee_id) ON DELETE CASCADE
);

-- 2. IC Access Request Table
CREATE TABLE IF NOT EXISTS IC_Access_Request (
    request_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id    INTEGER NOT NULL,
    target_employee_id INTEGER NOT NULL,
    reason          TEXT,
    status          TEXT DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected','Expired')),
    requested_at    TEXT DEFAULT (datetime('now')),
    reviewed_by     INTEGER,
    reviewed_at     TEXT,
    expires_at      TEXT, -- Access expires after some time if approved
    FOREIGN KEY (requester_id)   REFERENCES Employee(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (target_employee_id) REFERENCES Employee(employee_id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by)    REFERENCES Employee(employee_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_notification_employee ON Notification(employee_id);
CREATE INDEX IF NOT EXISTS idx_notification_read ON Notification(employee_id, is_read);
CREATE INDEX IF NOT EXISTS idx_ic_access_request_requester ON IC_Access_Request(requester_id);
CREATE INDEX IF NOT EXISTS idx_ic_access_request_target ON IC_Access_Request(target_employee_id);
CREATE INDEX IF NOT EXISTS idx_ic_access_request_status ON IC_Access_Request(status);
