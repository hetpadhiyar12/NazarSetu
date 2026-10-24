-- NazarSetu SQLite Schema DDL
-- Enable foreign key constraints and WAL mode in SQLite
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ============================================================================
-- 1. COMPLAINTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS complaints (
    id TEXT PRIMARY KEY,                        -- Format: NS-DEMO-XXXXXXXX
    idempotency_key TEXT UNIQUE,                -- Prevents duplicate browser re-submissions
    issue_type TEXT NOT NULL,                   -- Potholes and damaged roads | Overflowing garbage | Broken streetlights | Waterlogging and drainage issues
    description TEXT NOT NULL,                  -- Citizen-approved description
    visual_evidence TEXT,                       -- Issue DNA visible evidence summary
    uncertainty_notes TEXT,                     -- Transparent AI uncertainty disclosure
    city TEXT NOT NULL,                         -- Selected city
    locality TEXT NOT NULL,                     -- Selected locality
    landmark TEXT DEFAULT '',                   -- Optional street/landmark description
    ward TEXT NOT NULL,                         -- Mapped fictional demo ward
    department TEXT NOT NULL,                   -- Routed municipal department
    image_hash TEXT NOT NULL,                   -- SHA-256 hex digest of uploaded photo
    priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High')),
    status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'In Progress', 'Resolved')),
    ai_mode TEXT NOT NULL DEFAULT 'AI_VERIFIED' CHECK (ai_mode IN ('AI_VERIFIED', 'FALLBACK_MANUAL')),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- ============================================================================
-- 2. COMPLAINT EVENTS TABLE (Immutable Audit & Timeline Log)
-- ============================================================================
CREATE TABLE IF NOT EXISTS complaint_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id TEXT NOT NULL,
    event_type TEXT NOT NULL,                   -- CREATED | DUPLICATE_CHECKED | WARD_ROUTED | STATUS_UPDATED | ADMIN_NOTE
    details TEXT NOT NULL,                      -- Human-readable audit trail payload
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
);

-- ============================================================================
-- 3. INDEXES FOR FAST AGENT TOOL EXECUTION & DUPLICATE DETECTION
-- ============================================================================
-- Composite index for Smart Duplicate Guard (check_duplicate tool)
CREATE INDEX IF NOT EXISTS idx_complaints_duplicate_guard
ON complaints (issue_type, locality, image_hash, status);

-- Index for Admin Command Center filtering
CREATE INDEX IF NOT EXISTS idx_complaints_status_dept
ON complaints (status, department, issue_type, created_at DESC);

-- Index for chronological timeline lookup (get_complaint_timeline tool)
CREATE INDEX IF NOT EXISTS idx_events_complaint_chronological
ON complaint_events (complaint_id, created_at ASC, id ASC);
