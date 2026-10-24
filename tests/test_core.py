"""
Automated Test Suite for NazarSetu Core Functions.

Covers:
1. Correct department mapping.
2. Correct demo locality lookup.
3. Unsupported locality handling.
4. Database complaint registration.
5. Unique tracking IDs.
6. Duplicate submission prevention.
7. Correct status retrieval.
8. Status-update persistence.
9. Complaint event timeline.
10. Duplicate matching when enabled.
11. Invalid tracking IDs.
12. Safe handling of invalid tool arguments.
"""

import os
import sys
import tempfile
from pathlib import Path
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import (
    SUPPORTED_CATEGORIES,
    DEPARTMENT_MAPPING,
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_RESOLVED,
)
import database
import tools
import agent


@pytest.fixture
def temp_db():
    """Create an isolated temporary SQLite database for tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = Path(f.name)
    database.init_db(temp_path)
    yield temp_path
    if temp_path.exists():
        temp_path.unlink()


# 1. Correct department mapping
def test_department_mapping():
    for category, expected_dept in DEPARTMENT_MAPPING.items():
        res = tools.select_department(category)
        assert res["status"] == "success"
        assert res["department"] == expected_dept
        assert res["is_supported"] is True


# 2. Correct demo locality lookup
def test_correct_demo_locality_lookup():
    res = tools.find_responsible_ward(city="Bengaluru", locality="Indiranagar")
    assert res["status"] == "success"
    assert res["is_supported"] is True
    assert "Ward 74" in res["ward"]
    assert res["ward_id"] == "DEMO-WARD-BLR-074"

    res_mumbai = tools.find_responsible_ward(city="Mumbai", locality="Bandra West")
    assert res_mumbai["status"] == "success"
    assert "Ward H/West" in res_mumbai["ward"]


# 3. Unsupported locality handling
def test_unsupported_locality_handling():
    res = tools.find_responsible_ward(city="Atlantis", locality="DeepSea")
    assert res["status"] == "unsupported_location"
    assert res["is_supported"] is False
    assert "not in the approved demo ward dataset" in res["message"]


# 4. Database complaint registration
def test_database_complaint_registration(temp_db):
    complaint_data = {
        "confirmed": True,
        "issue_type": "Potholes and damaged roads",
        "description": "Hazardous crater near hospital gate.",
        "city": "Bengaluru",
        "locality": "Indiranagar",
        "ward": "Ward 74 (Demo)",
        "department": "Roads & Infrastructure Department",
        "image_hash": "testhash12345",
        "priority": "High",
        "status": STATUS_PENDING,
    }
    reg_res = tools.register_complaint(complaint_data, db_path=temp_db)
    assert reg_res["status"] == "registered"
    assert reg_res["complaint_id"].startswith("NS-DEMO-")

    # Verify retrieval
    stored = database.get_complaint(reg_res["complaint_id"], db_path=temp_db)
    assert stored is not None
    assert stored["description"] == "Hazardous crater near hospital gate."
    assert stored["status"] == STATUS_PENDING


# 5. Unique tracking IDs
def test_unique_tracking_ids():
    ids = {database.generate_complaint_id() for _ in range(100)}
    assert len(ids) == 100
    for cid in ids:
        assert cid.startswith("NS-DEMO-")
        assert len(cid) == 16  # NS-DEMO- (8 chars) + 8 hex chars


# 6. Duplicate submission prevention (confirmation requirement)
def test_unconfirmed_submission_prevention(temp_db):
    unconfirmed_data = {
        "confirmed": False,
        "issue_type": "Potholes and damaged roads",
        "city": "Bengaluru",
        "locality": "Indiranagar",
    }
    res = tools.register_complaint(unconfirmed_data, db_path=temp_db)
    assert res["status"] == "confirmation_required"


# 7. Correct status retrieval
def test_correct_status_retrieval(temp_db):
    complaint_data = {
        "confirmed": True,
        "issue_type": "Overflowing garbage",
        "description": "Bin overflowing on pavement.",
        "city": "Mumbai",
        "locality": "Bandra West",
        "ward": "Ward H/West",
        "department": "Solid Waste Management Department",
        "image_hash": "hashgarbage99",
        "priority": "Medium",
        "status": STATUS_PENDING,
    }
    reg_res = tools.register_complaint(complaint_data, db_path=temp_db)
    cid = reg_res["complaint_id"]

    status_res = tools.get_complaint_status(cid, db_path=temp_db)
    assert status_res["status"] == "found"
    assert status_res["current_status"] == STATUS_PENDING
    assert status_res["department"] == "Solid Waste Management Department"


# 8. Status-update persistence
def test_status_update_persistence(temp_db):
    complaint_data = {
        "confirmed": True,
        "issue_type": "Broken streetlights",
        "description": "Fallen lamp post.",
        "city": "Delhi",
        "locality": "Connaught Place",
        "ward": "Ward 01",
        "department": "Electrical & Public Lighting Department",
        "image_hash": "hashlamp44",
        "priority": "High",
        "status": STATUS_PENDING,
    }
    cid = tools.register_complaint(complaint_data, db_path=temp_db)["complaint_id"]

    # Update to In Progress
    updated = database.update_complaint_status(
        complaint_id=cid,
        new_status=STATUS_IN_PROGRESS,
        note="Crew dispatched with crane.",
        db_path=temp_db
    )
    assert updated is True

    # Retrieve and verify
    assert database.get_complaint_status(cid, db_path=temp_db) == STATUS_IN_PROGRESS

    # Update to Resolved
    database.update_complaint_status(
        complaint_id=cid,
        new_status=STATUS_RESOLVED,
        note="Repaired and operational.",
        db_path=temp_db
    )
    assert database.get_complaint_status(cid, db_path=temp_db) == STATUS_RESOLVED


# 9. Complaint event timeline
def test_complaint_event_timeline(temp_db):
    complaint_data = {
        "confirmed": True,
        "issue_type": "Waterlogging and drainage issues",
        "description": "Road flooded with rainwater.",
        "city": "Ahmedabad",
        "locality": "Satellite",
        "ward": "Ward 02",
        "department": "Stormwater & Drainage Department",
        "image_hash": "waterhash88",
        "priority": "High",
        "status": STATUS_PENDING,
    }
    cid = tools.register_complaint(complaint_data, db_path=temp_db)["complaint_id"]
    database.update_complaint_status(cid, STATUS_IN_PROGRESS, note="Dewatering pump on site", db_path=temp_db)

    timeline_res = tools.get_complaint_timeline(cid, db_path=temp_db)
    assert timeline_res["status"] == "success"
    assert timeline_res["event_count"] >= 2
    
    events = timeline_res["events"]
    assert events[0]["event_type"] in ["CREATED", "REGISTERED"]
    assert events[1]["event_type"] in ["STATUS_UPDATED", "STATUS_CHANGE"]
    assert "Dewatering pump" in events[1]["details"]


# 10. Duplicate matching when enabled
def test_duplicate_matching(temp_db):
    img_hash = "identical_sha256_hash_12345"
    complaint_data = {
        "confirmed": True,
        "issue_type": "Potholes and damaged roads",
        "description": "First report of severe pothole.",
        "city": "Bengaluru",
        "locality": "Indiranagar",
        "ward": "Ward 74",
        "department": "Roads & Infrastructure Department",
        "image_hash": img_hash,
        "priority": "High",
        "status": STATUS_PENDING,
    }
    first_cid = tools.register_complaint(complaint_data, db_path=temp_db)["complaint_id"]

    # Check duplicate
    dup_res = tools.check_duplicate(
        issue_type="Potholes and damaged roads",
        locality="Indiranagar",
        image_hash=img_hash,
        db_path=temp_db
    )
    assert dup_res["status"] == "duplicate_found"
    assert dup_res["is_duplicate"] is True
    assert dup_res["existing_complaint_id"] == first_cid

    # If the first complaint is marked Resolved, duplicate check should not flag it as an unresolved duplicate
    database.update_complaint_status(first_cid, STATUS_RESOLVED, db_path=temp_db)
    dup_resolved = tools.check_duplicate(
        issue_type="Potholes and damaged roads",
        locality="Indiranagar",
        image_hash=img_hash,
        db_path=temp_db
    )
    assert dup_resolved["status"] == "no_duplicate"
    assert dup_resolved["is_duplicate"] is False


# 11. Invalid tracking IDs
def test_invalid_tracking_ids(temp_db):
    res = tools.get_complaint_status("NON_EXISTENT_ID_9999", db_path=temp_db)
    assert res["status"] == "not_found"
    assert "No complaint found" in res["message"]

    res_empty = tools.get_complaint_status("", db_path=temp_db)
    assert res_empty["status"] == "error"

    timeline_empty = tools.get_complaint_timeline("UNKNOWN-99", db_path=temp_db)
    assert timeline_empty["status"] == "not_found"


# 12. Safe handling of invalid tool arguments
def test_safe_handling_of_invalid_tool_arguments():
    # find_responsible_ward with None/wrong types
    res_ward = tools.find_responsible_ward(None, 123)  # type: ignore
    assert res_ward["status"] == "error"
    assert res_ward["is_supported"] is False

    # select_department with None/empty
    res_dept = tools.select_department(None)  # type: ignore
    assert res_dept["status"] == "error"

    # check_duplicate with None
    res_dup = tools.check_duplicate(None, None, None)  # type: ignore
    assert res_dup["status"] == "error"

    # register_complaint with invalid type
    res_reg = tools.register_complaint("not a dict")  # type: ignore
    assert res_reg["status"] == "error"

    # execute_tool_call with unknown tool name
    unknown_res = tools.execute_tool_call("non_existent_tool", {})
    assert unknown_res["status"] == "error"
    assert "Unknown tool" in unknown_res["message"]


# 13. Idempotency Key duplicate browser submission prevention
def test_idempotency_key_duplicate_prevention(temp_db):
    idem_key = "unique_client_token_abc_123"
    complaint_data = {
        "confirmed": True,
        "idempotency_key": idem_key,
        "issue_type": "Potholes and damaged roads",
        "description": "Double submission test.",
        "city": "Bengaluru",
        "locality": "Indiranagar",
        "ward": "Ward 74",
        "department": "Roads & Infrastructure Department",
        "image_hash": "hash_idem_test",
        "priority": "High",
        "status": STATUS_PENDING,
        "ai_mode": "AI_VERIFIED",
    }
    # First submission
    res1 = tools.register_complaint(complaint_data, db_path=temp_db)
    assert res1["status"] == "registered"
    first_id = res1["complaint_id"]

    # Second immediate submission with identical idempotency key
    res2 = tools.register_complaint(complaint_data, db_path=temp_db)
    assert res2["status"] == "registered"
    assert res2["complaint_id"] == first_id

    # Verify only 1 complaint exists in database
    with database.get_connection(temp_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM complaints WHERE idempotency_key = ?", (idem_key,))
        count = cursor.fetchone()[0]
        assert count == 1


# 14. Schema CHECK constraints and metadata preservation
def test_schema_constraints_and_metadata(temp_db):
    complaint_data = {
        "confirmed": True,
        "issue_type": "Waterlogging and drainage issues",
        "description": "Flooded road near metro station.",
        "visual_evidence": "Murky water pooling across 2 lanes.",
        "uncertainty_notes": "Nighttime shadows near curb.",
        "city": "Ahmedabad",
        "locality": "Satellite",
        "landmark": "Near Shivranjani Cross Roads",
        "ward": "Ward 02",
        "department": "Stormwater & Drainage Department",
        "image_hash": "meta_hash_xyz",
        "priority": "High",
        "status": STATUS_PENDING,
        "ai_mode": "AI_VERIFIED",
    }
    cid = tools.register_complaint(complaint_data, db_path=temp_db)["complaint_id"]
    status_info = tools.get_complaint_status(cid, db_path=temp_db)

    assert status_info["status"] == "found"
    assert status_info["visual_evidence"] == "Murky water pooling across 2 lanes."
    assert status_info["uncertainty_notes"] == "Nighttime shadows near curb."
    assert status_info["landmark"] == "Near Shivranjani Cross Roads"
    assert status_info["ai_mode"] == "AI_VERIFIED"
    assert status_info["priority"] == "High"

