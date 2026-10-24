"""
NazarSetu Agent Tools.

Implements genuine Python tool functions callable by the autonomous agent,
with parameter validation, structured outputs, and fallback resilience.
"""

import csv
import hashlib
from typing import Dict, Any, List, Optional
from pathlib import Path

from config import (
    DEMO_WARDS_CSV,
    DEPARTMENT_MAPPING,
    SUPPORTED_CATEGORIES,
    DB_PATH,
    PRIORITY_RULES,
)
import database

# Cache for demo ward mapping
_WARDE_CACHE: Optional[List[Dict[str, str]]] = None


def load_ward_data(csv_path: Path = DEMO_WARDS_CSV) -> List[Dict[str, str]]:
    """Load and cache fictional demo ward mapping."""
    global _WARDE_CACHE
    if _WARDE_CACHE is not None:
        return _WARDE_CACHE
    
    wards = []
    if csv_path.exists():
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                wards.append({k.strip(): v.strip() for k, v in row.items()})
    _WARDE_CACHE = wards
    return _WARDE_CACHE


def compute_image_hash(image_bytes: bytes) -> str:
    """Compute deterministic SHA-256 hash of image bytes for duplicate detection."""
    return hashlib.sha256(image_bytes).hexdigest()


# Tool 1: find_responsible_ward
def find_responsible_ward(city: str, locality: str) -> Dict[str, Any]:
    """
    Look up the location in the approved local ward dataset.
    Returns the mapped ward or a clear unsupported-location response.
    """
    if not isinstance(city, str) or not isinstance(locality, str):
        return {
            "status": "error",
            "message": "Invalid input arguments. 'city' and 'locality' must be strings.",
            "is_supported": False,
        }

    city_clean = city.strip()
    locality_clean = locality.strip()

    if not city_clean or not locality_clean:
        return {
            "status": "error",
            "message": "Both 'city' and 'locality' must be non-empty.",
            "is_supported": False,
        }

    wards = load_ward_data()
    for row in wards:
        if (
            row.get("city", "").lower() == city_clean.lower()
            and row.get("locality", "").lower() == locality_clean.lower()
        ):
            return {
                "status": "success",
                "is_supported": True,
                "city": row.get("city"),
                "locality": row.get("locality"),
                "ward": row.get("ward_name"),
                "ward_id": row.get("ward_id"),
                "zone": row.get("zone"),
                "nodal_officer": row.get("nodal_officer"),
                "is_demo_data": True,
            }

    return {
        "status": "unsupported_location",
        "is_supported": False,
        "city": city_clean,
        "locality": locality_clean,
        "message": f"Locality '{locality_clean}' in '{city_clean}' is not in the approved demo ward dataset.",
        "supported_cities": ["Bengaluru", "Mumbai", "Delhi", "Ahmedabad", "Pune"],
    }


# Tool 2: select_department
def select_department(issue_type: str) -> Dict[str, Any]:
    """
    Route the civic issue to a matching municipal department.
    """
    if not isinstance(issue_type, str) or not issue_type.strip():
        return {
            "status": "error",
            "department": "Unassigned",
            "message": "Invalid issue type parameter.",
            "is_supported": False,
        }

    clean_issue = issue_type.strip()
    # Direct match or loose substring match
    for supported, dept in DEPARTMENT_MAPPING.items():
        if clean_issue.lower() == supported.lower() or supported.lower() in clean_issue.lower():
            return {
                "status": "success",
                "issue_type": supported,
                "department": dept,
                "is_supported": True,
            }

    return {
        "status": "unknown_issue",
        "department": "General Grievance Cell",
        "issue_type": clean_issue,
        "is_supported": False,
        "message": f"'{clean_issue}' does not map directly to standard civic categories.",
        "supported_categories": SUPPORTED_CATEGORIES,
    }


# Tool 3: check_duplicate
def check_duplicate(
    issue_type: str,
    locality: str,
    image_hash: str,
    db_path: Path = DB_PATH
) -> Dict[str, Any]:
    """
    Search local database for unresolved complaints matching issue category, locality, and image hash.
    Returns existing tracking ID if a likely duplicate is found.
    """
    if not isinstance(issue_type, str) or not isinstance(locality, str) or not isinstance(image_hash, str):
        return {
            "status": "error",
            "is_duplicate": False,
            "message": "Invalid argument types for duplicate check.",
        }

    try:
        dup = database.find_duplicate(
            issue_type=issue_type,
            locality=locality,
            image_hash=image_hash,
            db_path=db_path
        )
        if dup:
            return {
                "status": "duplicate_found",
                "is_duplicate": True,
                "existing_complaint_id": dup["id"],
                "existing_status": dup["status"],
                "existing_created_at": dup["created_at"],
                "message": (
                    f"A potentially matching unresolved complaint ({dup['id']}) "
                    f"already exists in {locality} with status '{dup['status']}'."
                ),
            }
        
        return {
            "status": "no_duplicate",
            "is_duplicate": False,
            "message": "No matching duplicate unresolved report found in this locality.",
        }
    except Exception as e:
        return {
            "status": "error",
            "is_duplicate": False,
            "message": f"Duplicate guard encounter non-fatal error: {str(e)}",
        }


# Tool 4: register_complaint
def register_complaint(
    confirmed_details: Dict[str, Any],
    db_path: Path = DB_PATH
) -> Dict[str, Any]:
    """
    Create a real SQLite record and return the generated unique ID.
    Safety constraint: Requires confirmed=True in confirmed_details.
    """
    if not isinstance(confirmed_details, dict):
        return {
            "status": "error",
            "message": "Invalid arguments. 'confirmed_details' must be a dictionary.",
        }

    if not confirmed_details.get("confirmed", False):
        return {
            "status": "confirmation_required",
            "message": "Complaint submission halted: Citizen confirmation has not been provided.",
        }

    required_fields = ["issue_type", "city", "locality"]
    for field in required_fields:
        if not confirmed_details.get(field):
            return {
                "status": "error",
                "message": f"Missing required registration field: '{field}'.",
            }

    try:
        complaint_id = database.insert_complaint(confirmed_details, db_path=db_path)
        return {
            "status": "registered",
            "complaint_id": complaint_id,
            "message": f"Complaint successfully registered with Tracking ID: {complaint_id}",
            "department": confirmed_details.get("department", "Roads & Infrastructure Department"),
            "ward": confirmed_details.get("ward", "Demo Ward"),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to register complaint in database: {str(e)}",
        }


# Tool 5: get_complaint_status
def get_complaint_status(complaint_id: str, db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Retrieve an actual complaint from SQLite and return its latest stored status.
    """
    if not isinstance(complaint_id, str) or not complaint_id.strip():
        return {
            "status": "error",
            "message": "Invalid or missing tracking ID.",
        }

    cid = complaint_id.strip()
    record = database.get_complaint(cid, db_path=db_path)
    if not record:
        return {
            "status": "not_found",
            "complaint_id": cid,
            "message": f"No complaint found matching tracking ID '{cid}'. Please verify the ID format (e.g. NS-DEMO-XXXXXXXX).",
        }

    return {
        "status": "found",
        "complaint_id": record["id"],
        "issue_type": record["issue_type"],
        "current_status": record["status"],
        "department": record["department"],
        "ward": record["ward"],
        "locality": record["locality"],
        "city": record["city"],
        "priority": record["priority"],
        "updated_at": record["updated_at"],
        "description": record["description"],
    }


# Tool 6: get_complaint_timeline
def get_complaint_timeline(complaint_id: str, db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Retrieve the complaint's recorded events in chronological order.
    """
    if not isinstance(complaint_id, str) or not complaint_id.strip():
        return {
            "status": "error",
            "message": "Invalid or missing tracking ID.",
            "events": [],
        }

    cid = complaint_id.strip()
    events = database.get_complaint_timeline(cid, db_path=db_path)
    if not events:
        # Check if complaint even exists
        complaint = database.get_complaint(cid, db_path=db_path)
        if not complaint:
            return {
                "status": "not_found",
                "complaint_id": cid,
                "message": f"Tracking ID '{cid}' does not exist.",
                "events": [],
            }

    return {
        "status": "success",
        "complaint_id": cid,
        "event_count": len(events),
        "events": events,
    }


# OpenAI Function-Calling Tool Definitions
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find_responsible_ward",
            "description": "Look up the ward, zone, and nodal officer for a given Indian city and locality in the approved demo database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name (e.g., Bengaluru, Mumbai, Delhi, Ahmedabad, Pune)."
                    },
                    "locality": {
                        "type": "string",
                        "description": "The neighborhood or locality name (e.g., Indiranagar, Bandra West, Connaught Place)."
                    }
                },
                "required": ["city", "locality"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "select_department",
            "description": "Identify and return the responsible civic department based on the classified issue type.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {
                        "type": "string",
                        "description": "Civic issue classification category."
                    }
                },
                "required": ["issue_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_duplicate",
            "description": "Search for existing unresolved complaints matching issue type, locality, and image SHA-256 hash.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {
                        "type": "string",
                        "description": "Category of civic issue."
                    },
                    "locality": {
                        "type": "string",
                        "description": "Locality/neighborhood."
                    },
                    "image_hash": {
                        "type": "string",
                        "description": "SHA-256 hash of the uploaded image."
                    }
                },
                "required": ["issue_type", "locality", "image_hash"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_complaint_status",
            "description": "Retrieve the current status, department, and location details of a registered complaint using its tracking ID (e.g., NS-DEMO-XXXXXXXX).",
            "parameters": {
                "type": "object",
                "properties": {
                    "complaint_id": {
                        "type": "string",
                        "description": "The unique complaint tracking ID (format NS-DEMO-XXXXXXXX)."
                    }
                },
                "required": ["complaint_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_complaint_timeline",
            "description": "Retrieve the complete audit history and timeline of events for a complaint tracking ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "complaint_id": {
                        "type": "string",
                        "description": "The unique complaint tracking ID."
                    }
                },
                "required": ["complaint_id"]
            }
        }
    }
]


def execute_tool_call(tool_name: str, arguments: Dict[str, Any], db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Safely dispatch and execute a tool function by name.
    Guarantees no crashes on unknown tool names or malformed arguments.
    """
    if tool_name == "find_responsible_ward":
        return find_responsible_ward(
            city=arguments.get("city", ""),
            locality=arguments.get("locality", "")
        )
    elif tool_name == "select_department":
        return select_department(
            issue_type=arguments.get("issue_type", "")
        )
    elif tool_name == "check_duplicate":
        return check_duplicate(
            issue_type=arguments.get("issue_type", ""),
            locality=arguments.get("locality", ""),
            image_hash=arguments.get("image_hash", ""),
            db_path=db_path
        )
    elif tool_name == "register_complaint":
        return register_complaint(
            confirmed_details=arguments.get("confirmed_details", {}),
            db_path=db_path
        )
    elif tool_name == "get_complaint_status":
        return get_complaint_status(
            complaint_id=arguments.get("complaint_id", ""),
            db_path=db_path
        )
    elif tool_name == "get_complaint_timeline":
        return get_complaint_timeline(
            complaint_id=arguments.get("complaint_id", ""),
            db_path=db_path
        )
    else:
        return {
            "status": "error",
            "message": f"Unknown tool requested: '{tool_name}'",
        }
