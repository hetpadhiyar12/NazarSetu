"""
NazarSetu Database Layer.

Provides SQLite persistence for civic complaints and audit event timelines.
All database access uses parameterized SQL to guarantee integrity and security.
Implements idempotency keys, CHECK constraints, and optimized composite indexes.
"""

import sqlite3
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from config import DB_PATH, COMPLAINT_ID_PREFIX, STATUS_PENDING, STATUS_RESOLVED, VALID_STATUSES


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create and return a configured SQLite connection with WAL and FK enabled."""
    conn = sqlite3.connect(str(db_path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """Initialize database tables, CHECK constraints, and performance indexes."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Check if legacy complaints table exists without idempotency_key
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='complaints'")
        table_exists = cursor.fetchone()
        if table_exists:
            cursor.execute("PRAGMA table_info(complaints)")
            columns = [row["name"] for row in cursor.fetchall()]
            if "idempotency_key" not in columns or "ai_mode" not in columns:
                # Recreate table with new constraints and fields
                cursor.execute("DROP TABLE IF EXISTS complaint_events")
                cursor.execute("DROP TABLE IF EXISTS complaints")

        # 1. Complaints Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE,
                issue_type TEXT NOT NULL,
                description TEXT NOT NULL,
                visual_evidence TEXT,
                uncertainty_notes TEXT,
                city TEXT NOT NULL,
                locality TEXT NOT NULL,
                landmark TEXT DEFAULT '',
                ward TEXT NOT NULL,
                department TEXT NOT NULL,
                image_hash TEXT NOT NULL,
                priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High')),
                status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'In Progress', 'Resolved')),
                ai_mode TEXT NOT NULL DEFAULT 'AI_VERIFIED' CHECK (ai_mode IN ('AI_VERIFIED', 'FALLBACK_MANUAL')),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            );
        """)

        # 2. Complaint Events Table (Immutable Audit & Timeline Log)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaint_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
            );
        """)

        # 3. Indexes for fast agent tool execution & duplicate detection
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_complaints_duplicate_guard
            ON complaints (issue_type, locality, image_hash, status);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_complaints_status_dept
            ON complaints (status, department, issue_type, created_at DESC);
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_complaint_chronological
            ON complaint_events (complaint_id, created_at ASC, id ASC);
        """)

        conn.commit()


def generate_complaint_id() -> str:
    """Generate a unique tracking ID format: NS-DEMO-XXXXXXXX."""
    random_part = secrets.token_hex(4).upper()
    return f"{COMPLAINT_ID_PREFIX}{random_part}"


def generate_idempotency_key(payload_seed: Optional[str] = None) -> str:
    """Generate a unique idempotency key to prevent double submissions."""
    token = secrets.token_hex(8)
    if payload_seed:
        return f"idem_{payload_seed[:16]}_{token}"
    return f"idem_{token}"


def insert_complaint(
    complaint_data: Dict[str, Any],
    db_path: Path = DB_PATH
) -> str:
    """
    Insert a confirmed complaint and record its initial registration event.
    Prevents duplicate submissions via idempotency_key UNIQUE constraint.
    Returns the assigned complaint_id.
    """
    init_db(db_path)
    complaint_id = complaint_data.get("id") or generate_complaint_id()
    idempotency_key = complaint_data.get("idempotency_key") or generate_idempotency_key(complaint_id)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    issue_type = str(complaint_data.get("issue_type", "")).strip()
    description = str(complaint_data.get("description", "")).strip()
    city = str(complaint_data.get("city", "")).strip()
    locality = str(complaint_data.get("locality", "")).strip()
    ward = str(complaint_data.get("ward", "Demo Ward")).strip()
    department = str(complaint_data.get("department", "Unassigned")).strip()
    image_hash = str(complaint_data.get("image_hash", "")).strip()
    
    # Validate priority against CHECK constraint
    raw_priority = str(complaint_data.get("priority", "Medium")).strip().capitalize()
    priority = raw_priority if raw_priority in ["Low", "Medium", "High"] else "Medium"
    
    # Validate status against CHECK constraint
    raw_status = str(complaint_data.get("status", STATUS_PENDING)).strip()
    status = raw_status if raw_status in VALID_STATUSES else STATUS_PENDING

    # Validate ai_mode against CHECK constraint
    raw_ai_mode = str(complaint_data.get("ai_mode", "AI_VERIFIED")).strip().upper()
    ai_mode = raw_ai_mode if raw_ai_mode in ["AI_VERIFIED", "FALLBACK_MANUAL"] else "AI_VERIFIED"

    landmark = str(complaint_data.get("landmark", "")).strip() if complaint_data.get("landmark") else ""
    visual_evidence = str(complaint_data.get("visual_evidence", "")).strip() if complaint_data.get("visual_evidence") else None
    uncertainty_notes = str(complaint_data.get("uncertainty_notes", "")).strip() if complaint_data.get("uncertainty_notes") else None

    with get_connection(db_path) as conn:
        cursor = conn.cursor()

        # Check for existing idempotency key to prevent double browser re-submissions
        cursor.execute("SELECT id FROM complaints WHERE idempotency_key = ?", (idempotency_key,))
        existing_row = cursor.fetchone()
        if existing_row:
            return existing_row["id"]

        # Ensure ID collision avoidance
        cursor.execute("SELECT id FROM complaints WHERE id = ?", (complaint_id,))
        if cursor.fetchone():
            complaint_id = generate_complaint_id()

        cursor.execute("""
            INSERT INTO complaints (
                id, idempotency_key, issue_type, description, visual_evidence, uncertainty_notes,
                city, locality, landmark, ward, department, image_hash, priority, status,
                ai_mode, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            complaint_id, idempotency_key, issue_type, description, visual_evidence, uncertainty_notes,
            city, locality, landmark, ward, department, image_hash, priority, status,
            ai_mode, now_iso, now_iso
        ))

        # Initial audit event in complaint_events
        event_details = f"Complaint officially registered by citizen for '{issue_type}' in {locality}, {city}. Assigned to {department} ({ward})."
        cursor.execute("""
            INSERT INTO complaint_events (complaint_id, event_type, details, created_at)
            VALUES (?, 'CREATED', ?, ?)
        """, (complaint_id, event_details, now_iso))

        conn.commit()

    return complaint_id


def get_complaint(complaint_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """
    Retrieve complaint details by ID using the parameterized query:
    WHERE UPPER(TRIM(id)) = UPPER(TRIM(:complaint_id))
    """
    init_db(db_path)
    cid = str(complaint_id).strip()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, idempotency_key, issue_type, description, visual_evidence, uncertainty_notes,
                   city, locality, landmark, ward, department, priority, status, ai_mode,
                   created_at, updated_at
            FROM complaints
            WHERE UPPER(TRIM(id)) = UPPER(TRIM(?));
        """, (cid,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)


def get_complaint_status(complaint_id: str, db_path: Path = DB_PATH) -> Optional[str]:
    """Retrieve only the latest status for a complaint ID."""
    complaint = get_complaint(complaint_id, db_path=db_path)
    if complaint:
        return complaint["status"]
    return None


def get_complaint_timeline(complaint_id: str, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """
    Retrieve chronological audit events for a complaint using:
    WHERE UPPER(TRIM(complaint_id)) = UPPER(TRIM(:complaint_id))
    ORDER BY created_at ASC, id ASC;
    """
    init_db(db_path)
    cid = str(complaint_id).strip()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, complaint_id, event_type, details, created_at
            FROM complaint_events
            WHERE UPPER(TRIM(complaint_id)) = UPPER(TRIM(?))
            ORDER BY created_at ASC, id ASC;
        """, (cid,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def update_complaint_status(
    complaint_id: str,
    new_status: str,
    note: Optional[str] = None,
    db_path: Path = DB_PATH
) -> bool:
    """
    Update complaint status and record a timestamped STATUS_UPDATED event.
    Returns True if updated, False if complaint ID was not found or status invalid.
    """
    init_db(db_path)
    new_status = new_status.strip()
    if new_status not in VALID_STATUSES:
        return False

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status FROM complaints
            WHERE UPPER(TRIM(id)) = UPPER(TRIM(?));
        """, (complaint_id.strip(),))
        current = cursor.fetchone()
        if not current:
            return False

        old_status = current["status"]
        cursor.execute("""
            UPDATE complaints
            SET status = ?, updated_at = ?
            WHERE UPPER(TRIM(id)) = UPPER(TRIM(?));
        """, (new_status, now_iso, complaint_id.strip()))

        detail_text = f"Status updated from '{old_status}' to '{new_status}'."
        if note:
            detail_text += f" Notes: {note}"

        event_type = "STATUS_UPDATED" if not note else "STATUS_UPDATED"
        cursor.execute("""
            INSERT INTO complaint_events (complaint_id, event_type, details, created_at)
            VALUES (?, ?, ?, ?)
        """, (complaint_id.strip(), event_type, detail_text, now_iso))

        conn.commit()
        return True


def find_duplicate(
    issue_type: str,
    locality: str,
    image_hash: str,
    db_path: Path = DB_PATH
) -> Optional[Dict[str, Any]]:
    """
    Smart duplicate guard parameterized query:
    SELECT id, issue_type, locality, ward, department, status, created_at
    FROM complaints
    WHERE LOWER(TRIM(issue_type)) = LOWER(TRIM(:issue_type))
      AND LOWER(TRIM(locality)) = LOWER(TRIM(:locality))
      AND image_hash = :image_hash
      AND status != 'Resolved'
    ORDER BY created_at DESC
    LIMIT 1;
    """
    init_db(db_path)
    if not image_hash or not locality or not issue_type:
        return None

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, issue_type, locality, ward, department, status, created_at
            FROM complaints
            WHERE LOWER(TRIM(issue_type)) = LOWER(TRIM(?))
              AND LOWER(TRIM(locality)) = LOWER(TRIM(?))
              AND image_hash = ?
              AND status != 'Resolved'
            ORDER BY created_at DESC
            LIMIT 1;
        """, (issue_type.strip(), locality.strip(), image_hash.strip()))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def list_complaints(
    issue_type: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db_path: Path = DB_PATH
) -> List[Dict[str, Any]]:
    """Query complaints with optional filters for Admin Command Center using indexed fields."""
    init_db(db_path)
    query = "SELECT * FROM complaints WHERE 1=1"
    params: List[Any] = []

    if issue_type and issue_type != "All":
        query += " AND issue_type = ?"
        params.append(issue_type.strip())

    if department and department != "All":
        query += " AND department = ?"
        params.append(department.strip())

    if status and status != "All":
        query += " AND status = ?"
        params.append(status.strip())

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_complaint_stats(db_path: Path = DB_PATH) -> Dict[str, int]:
    """Retrieve high-level counters for Admin Dashboard."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM complaints;")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Pending';")
        pending = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'In Progress';")
        in_progress = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved';")
        resolved = cursor.fetchone()[0]

        return {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "resolved": resolved,
        }


def seed_demo_complaints(db_path: Path = DB_PATH) -> None:
    """Pre-seed sample demo complaints with proper constraints and events."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM complaints;")
        if cursor.fetchone()[0] > 0:
            return  # Already seeded

    sample_complaints = [
        {
            "id": "NS-DEMO-A101B202",
            "idempotency_key": "seed_idem_001_pothole",
            "issue_type": "Potholes and damaged roads",
            "description": "Deep 12cm crater pothole on 100ft road near 12th Main junction causing traffic bottleneck.",
            "visual_evidence": "Visible asphalt disintegration with sharp rim edges and exposed base aggregates.",
            "uncertainty_notes": "Lighting conditions optimal, clear depth visible.",
            "city": "Bengaluru",
            "locality": "Indiranagar",
            "landmark": "Near Metro Pillar 84",
            "ward": "Ward 74 - Indiranagar East (Demo)",
            "department": "Roads & Infrastructure Department",
            "image_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "priority": "High",
            "status": "In Progress",
            "ai_mode": "AI_VERIFIED",
            "created_at": "2026-10-23T10:15:00Z",
            "updated_at": "2026-10-24T09:30:00Z",
        },
        {
            "id": "NS-DEMO-C303D404",
            "idempotency_key": "seed_idem_002_garbage",
            "issue_type": "Overflowing garbage",
            "description": "Municipal waste collection bin overflowing onto pedestrian footpath for 3 consecutive days.",
            "visual_evidence": "Overflowing green dumper container with organic food waste and plastic debris spilling on pavement.",
            "uncertainty_notes": "Minor peripheral blur on sidewalk edge.",
            "city": "Mumbai",
            "locality": "Bandra West",
            "landmark": "Opposite St. Peter's Church",
            "ward": "Ward H/West - Bandra Hill Road (Demo)",
            "department": "Solid Waste Management Department",
            "image_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
            "priority": "Medium",
            "status": "Pending",
            "ai_mode": "AI_VERIFIED",
            "created_at": "2026-10-24T08:00:00Z",
            "updated_at": "2026-10-24T08:00:00Z",
        },
        {
            "id": "NS-DEMO-E505F606",
            "idempotency_key": "seed_idem_003_streetlight",
            "issue_type": "Broken streetlights",
            "description": "Pole lighting extinguished, entire pedestrian walkway in complete darkness at night.",
            "visual_evidence": "Dark sodium fixture on pole arm with broken lamp diffuser glass.",
            "uncertainty_notes": "Low ambient nighttime illumination.",
            "city": "Delhi",
            "locality": "Connaught Place",
            "landmark": "Block B Lane 4",
            "ward": "Ward 01 - Connaught Inner Circle (Demo)",
            "department": "Electrical & Public Lighting Department",
            "image_hash": "f6e5d4c3b2a10987654321fedcba0987654321abcdef0123456789abcdef0123",
            "priority": "Low",
            "status": "Resolved",
            "ai_mode": "FALLBACK_MANUAL",
            "created_at": "2026-10-22T14:20:00Z",
            "updated_at": "2026-10-23T16:45:00Z",
        },
    ]

    for c in sample_complaints:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO complaints (
                    id, idempotency_key, issue_type, description, visual_evidence, uncertainty_notes,
                    city, locality, landmark, ward, department, image_hash, priority, status,
                    ai_mode, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c["id"], c["idempotency_key"], c["issue_type"], c["description"],
                c["visual_evidence"], c["uncertainty_notes"], c["city"], c["locality"],
                c["landmark"], c["ward"], c["department"], c["image_hash"], c["priority"],
                c["status"], c["ai_mode"], c["created_at"], c["updated_at"]
            ))

            cursor.execute("""
                INSERT INTO complaint_events (complaint_id, event_type, details, created_at)
                VALUES (?, 'CREATED', ?, ?)
            """, (c["id"], f"Initial demo complaint registered for {c['issue_type']}.", c["created_at"]))

            if c["status"] == "In Progress":
                cursor.execute("""
                    INSERT INTO complaint_events (complaint_id, event_type, details, created_at)
                    VALUES (?, 'STATUS_UPDATED', ?, ?)
                """, (c["id"], "Status updated from 'Pending' to 'In Progress'. Crew dispatched for road inspection.", c["updated_at"]))
            elif c["status"] == "Resolved":
                cursor.execute("""
                    INSERT INTO complaint_events (complaint_id, event_type, details, created_at)
                    VALUES (?, 'STATUS_UPDATED', ?, ?)
                """, (c["id"], "Status updated from 'Pending' to 'Resolved'. Luminaire replaced and operational verification logged.", c["updated_at"]))

            conn.commit()
