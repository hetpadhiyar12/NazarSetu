"""
NazarSetu Configuration & Domain Constants.

Defines civic issue types, department routing rules, priority heuristics,
and demo ward dataset configurations.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database
DB_PATH = DATA_DIR / "nazarsetu.db"

# Sample ward mapping CSV
DEMO_WARDS_CSV = DATA_DIR / "demo_wards.csv"

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# Tracking ID Prefix
COMPLAINT_ID_PREFIX = "NS-DEMO-"

# Supported Civic Issue Categories
SUPPORTED_CATEGORIES = [
    "Potholes and damaged roads",
    "Overflowing garbage",
    "Broken streetlights",
    "Waterlogging and drainage issues",
]

# Department Routing Mapping
DEPARTMENT_MAPPING = {
    "Potholes and damaged roads": "Roads & Infrastructure Department",
    "Overflowing garbage": "Solid Waste Management Department",
    "Broken streetlights": "Electrical & Public Lighting Department",
    "Waterlogging and drainage issues": "Stormwater & Drainage Department",
}

# Category Icons & Accents
CATEGORY_METADATA = {
    "Potholes and damaged roads": {
        "icon": "🕳️",
        "short_name": "Road Damage",
        "color": "#F4A340",
    },
    "Overflowing garbage": {
        "icon": "🗑️",
        "short_name": "Garbage",
        "color": "#E53E3E",
    },
    "Broken streetlights": {
        "icon": "💡",
        "short_name": "Streetlight",
        "color": "#DD6B20",
    },
    "Waterlogging and drainage issues": {
        "icon": "🌊",
        "short_name": "Drainage",
        "color": "#3182CE",
    },
}

# Complaint Statuses
STATUS_PENDING = "Pending"
STATUS_IN_PROGRESS = "In Progress"
STATUS_RESOLVED = "Resolved"

VALID_STATUSES = [STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_RESOLVED]

# Documented Priority Heuristic Rules
PRIORITY_RULES = {
    "Potholes and damaged roads": {
        "High": "Severe crater depth > 10cm, spans active traffic lane, or poses immediate vehicular/two-wheeler hazard.",
        "Medium": "Moderate depression or broken asphalt creating traffic slowdowns.",
        "Low": "Surface gravel wear or minor road chipping without structural blockage.",
    },
    "Overflowing garbage": {
        "High": "Massive waste spill blocking sidewalk/roadway, burning trash, or posing severe biohazard/pest infestation.",
        "Medium": "Overfilled dumpster container with waste spilling into immediate perimeter.",
        "Low": "Isolated scattered dry waste or single uncollected bin.",
    },
    "Broken streetlights": {
        "High": "Exposed live wires, fallen lighting pole, or total junction blackout on high-speed road.",
        "Medium": "Complete unlit street lamp on pedestrian thoroughfare or residential street.",
        "Low": "Flickering bulb or timer desynchronization (lamp active during daytime).",
    },
    "Waterlogging and drainage issues": {
        "High": "Deep standing water (> 1 foot) stalling vehicles or breaching residential/commercial thresholds.",
        "Medium": "Clogged storm drain or persistent curb-side pooling impeding pedestrian movement.",
        "Low": "Slow-draining shallow puddle during normal monsoon conditions.",
    },
}

# Hackathon Demo Disclaimer
DEMO_DISCLAIMER = (
    "NazarSetu is an Agentic AI Civic Action prototype built for demonstration. "
    "Ward assignments are mapped against fictional demo datasets. "
    "No municipal departments were officially contacted. ID format: NS-DEMO-XXXXXXXX."
)
