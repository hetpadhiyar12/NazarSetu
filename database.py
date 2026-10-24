"""
NazarSetu Database Layer.

Provides SQLite persistence for civic complaints and audit event timelines.
All database access uses parameterized SQL to guarantee integrity and security.
"""

import sqlite3
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from config import DB_PATH, COMPLAINT_ID_PREFIX, STATUS_PENDING, STATUS_RESOLVED, VALID_STATUSES


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create and return a configured SQLite connection."""
    conn = sqlite3.connect(str(db_path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for smooth concurrency in Streamlit
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """Initialize database tables and indexes."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Complaints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id TEXT PRIMARY KEY,
                issue_type TEXT NOT NULL,
                description TEXT NOT NULL,
                city TEXT NOT NULL,
                locality TEXT NOT NULL,
                ward TEXT NOT NULL,
                department TEXT NOT NULL,
                image_hash TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                landmark TEXT,
                visual_evidence TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Complaint events audit timeline table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaint_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE
            )
        """)

        # Indexes for fast querying and duplicate checks
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_complaints_lookup ON complaints (issue_type, locality, image_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_complaint_events ON complaint_events (complaint_id, created_at)")
        
        conn.commit()


def generate_complaint_id() -> str:
    """Generate a unique tracking ID format: NS-DEMO-XXXXXXXX."""
    random_part = secrets.token_hex(4).upper()
    return f"{COMPLAINT_ID_PREFIX}{random_part}"


def insert_complaint(
    complaint_data: Dict[str, Any],
    db_path: Path = DB_PATH
) -> str:
    """
    Insert a confirmed complaint and record its initial registration event.
    Returns the assigned complaint_id.
    """
    complaint_id = complaint_data.get("id") or generate_complaint_id()
    now_iso = datetime.now().isoformat(timespec="seconds")

    issue_type = str(complaint_data.get("issue_type", "")).strip()
    description = str(complaint_data.get("description", "")).strip()
    city = str(complaint_data.get("city", "")).strip()
    locality = str(complaint_data.get("locality", "")).strip()
    ward = str(complaint_data.get("ward", "Demo Ward")).strip()
    department = str(complaint_data.get("department", "Unassigned")).strip()
    image_hash = str(complaint_data.get("image_hash", "")).strip()
    priority = str(complaint_data.get("priority", "Medium")).strip()
    status = str(complaint_data.get("status", STATUS_PENDING)).strip()
    landmark = str(complaint_data.get("landmark", "")).strip() if complaint_data.get("landmark") else None
    visual_evidence = str(complaint_data.get("visual_evidence", "")).strip() if complaint_data.get("visual_evidence") else None

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Ensure unique ID collision avoidance
        cursor.execute("SELECT id FROM complaints WHERE id = ?", (complaint_id,))
        if cursor.fetchone():
            complaint_id = generate_complaint_id()

        cursor.execute("""
            INSERT INTO complaints (
                id, issue_type, description, city, locality, ward, department,
                image_hash, priority, status, landmark, visual_evidence, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            complaint_id, issue_type, description, city, locality, ward, department,
            image_hash, priority, status, landmark, visual_evidence, now_iso, now_iso
        ))

        # Initial audit event
        event_details = f"Complaint officially registered by citizen for '{issue_type}' in {locality}, {city}. Assigned to {department} ({ward})."
        cursor.execute("""
            INSERT INTO complaint_events (complaint_id, event_type, details, created_at)
            VALUES (?, 'REGISTERED', ?, ?)
        """, (complaint_id, event_details, now_iso))

        conn.commit()

    return complaint_id


def get_complaint(complaint_id: str, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve complaint details by ID, or None if not found."""
    cid = complaint_id.strip()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE id = ? COLLATE NOCASE", (cid,))
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
    """Retrieve chronological audit events for a complaint."""
    cid = complaint_id.strip()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, complaint_id, event_type, details, created_at
            FROM complaint_events
            WHERE complaint_id = ? COLLATE NOCASE
            ORDER BY datetime(created_at) ASC, id ASC
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
    Update complaint status and record a timestamped event.
    Returns True if updated, False if complaint ID was not found or status invalid.
    """
    new_status = new_status.strip()
    if new_status not in VALID_STATUSES:
        return False

    now_iso = datetime.now().isoformat(timespec="seconds")
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM complaints WHERE id = ? COLLATE NOCASE", (complaint_id.strip(),))
        current = cursor.fetchone()
        if not current:
            return False
        
        old_status = current["status"]
        cursor.execute("""
            UPDATE complaints
            SET status = ?, updated_at = ?
            WHERE id = ? COLLATE NOCASE
        """, (new_status, now_iso, complaint_id.strip()))

        detail_text = f"Status updated from '{old_status}' to '{new_status}'."
        if note:
            detail_text += f" Notes: {note}"

        cursor.execute("""
            INSERT INTO complaint_events (complaint_id, event_type, details, created_at)
            VALUES (?, 'STATUS_CHANGE', ?, ?)
        """, (complaint_id.strip(), detail_text, now_iso))

        conn.commit()
        return True


def find_duplicate(
    issue_type: str,
    locality: str,
    image_hash: str,
    db_path: Path = DB_PATH
) -> Optional[Dict[str, Any]]:
    """
    Smart duplicate guard check:
    Compares issue_type, locality, and SHA-256 image_hash.
    Filters out already 'Resolved' complaints.
    Returns the existing complaint record if a matching unresolved record exists.
    """
    if not image_hash or not locality or not issue_type:
        return None

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM complaints
            WHERE issue_type = ? COLLATE NOCASE
              AND locality = ? COLLATE NOCASE
              AND image_hash = ?
              AND status != ?
            ORDER BY datetime(created_at) DESC
            LIMIT 1
        """, (issue_type.strip(), locality.strip(), image_hash.strip(), STATUS_RESOLVED))
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
    """Query complaints with optional filters for Admin Command Center."""
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

    query += " ORDER BY datetime(created_at) DESC LIMIT ?"
    params.append(limit)

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_complaint_stats(db_path: Path = DB_PATH) -> Dict[str, int]:
    """Retrieve high-level counters for Admin Dashboard."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM complaints")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Pending'")
        pending = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'In Progress'")
        in_progress = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM complaints WHERE status = 'Resolved'")
        resolved = cursor.fetchone()[0]

        return {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "resolved": resolved,
        }


def seed_demo_complaints(db_path: Path = DB_PATH) -> None:
    """Pre-seed sample demo complaints if database is completely empty."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM complaints")
        if cursor.fetchone()[0] > 0:
            return  # Already has data

    sample_complaints = [
        {
            "id": "NS-DEMO-A101B202",
            "issue_type": "Potholes and damaged roads",
            "description": "Deep 12cm crater pothole on 100ft road near 12th Main junction causing traffic bottleneck.",
            "city": "Bengaluru",
            "locality": "Indiranagar",
            "ward": "Ward 74 - Indiranagar East (Demo)",
            "department": "Roads & Infrastructure Department",
            "image_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "priority": "High",
            "status": "In Progress",
            "landmark": "Near Metro Pillar 84",
            "visual_evidence": "Visible asphalt disintegration with sharp rim edges and exposed base aggregates.",
            "created_at": "2026-10-23T10:15:00",
            "updated_at": "2026-10-24T09:30:00",
        },
        {
            "id": "NS-DEMO-C303D404",
            "issue_type": "Overflowing garbage",
            "description": "Municipal waste collection bin overflowing onto pedestrian footpath for 3 consecutive days.",
            "city": "Mumbai",
            "locality": "Bandra West",
            "ward": "Ward H/West - Bandra Hill Road (Demo)",
            "department": "Solid Waste Management Department",
            "image_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
            "priority": "Medium",
            "status": "Pending",
            "landmark": "Opposite St. Peter's Church",
            "visual_evidence": "Overflowing green dumper container with organic food waste and plastic debris spilling on pavement.",
            "created_at": "2026-10-24T08:00:00",
            "updated_at": "2026-10-24T08:00:00",
        },
        {
            "id": "NS-DEMO-E505F606",
            "issue_type": "Broken streetlights",
            "description": "Pole lighting extinguished, entire pedestrian walkway in complete darkness at night.",
            "city": "Delhi",
            "locality": "Connaught Place",
            "ward": "Ward 01 - Connaught Inner Circle (Demo)",
            "department": "Electrical & Public Lighting Department",
            "image_hash": "f6e5d4c3b2a10987654321fedcba0987654321abcdef0123456789abcdef0123",
            "priority": "Low",
            "status": "Resolved",
            "landmark": "Block B Lane 4",
            "visual_evidence": "Dark sodium fixture on pole arm with broken lamp diffuser glass.",
            "created_at": "2026-10-22T14:20:00",
            "updated_at": "2026-10-23T16:45:00",
        },
    ]

    for c in sample_complaints:
        with get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO complaints (
                    id, issue_type, description, city, locality, ward, department,
                    image_hash, priority, status, landmark, visual_evidence, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c["id"], c["issue_type"], c["description"], c["city"], c["locality"],
                c["ward"], c["department"], c["image_hash"], c["priority"], c["status"],
                c["landmark"], c["visual_evidence"], c["created_at"], c["updated_at"]
            ))

            cursor.execute("""
                INSERT INTO complaint_events (complaint_id, event_type, details, created_at)
                VALUES (?, 'REGISTERED', ?, ?)
            """, (c["id"], f"Initial demo complaint registered for {c['issue_type']}.", c["created_at"]))

            if c["status"] == "In Progress":
                cursor.execute("""
                    INSERT INTO complaint_events (complaint_id, event_type, details, created_at)
                    VALUES (?, 'STATUS_CHANGE', ?, ?)
                """, (c["id"], "Status updated from 'Pending' to 'In Progress'. Crew dispatched for road inspection.", c["updated_at"]))
            elif c["status"] == "Resolved":
                cursor.execute("""
                    INSERT INTO complaint_events (complaint_id, event_type, details, created_at)
                    VALUES (?, 'STATUS_CHANGE', ?, ?)
                """, (c["id"], "Status updated from 'Pending' to 'Resolved'. Luminaire replaced and operational verification logged.", c["updated_at"]))

            conn.commit()
