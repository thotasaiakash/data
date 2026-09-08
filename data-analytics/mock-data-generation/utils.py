"""
Shared helpers for the Virginia analytics mock-data generator.

Everything here is deterministic given a seed, so re-running the generator
produces the same data (useful for reviewable PR diffs and repeatable tests).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from faker import Faker

fake = Faker()


# ---------------------------------------------------------------------------
# Reference / lookup data (small, curated, and geographically consistent)
# ---------------------------------------------------------------------------

# A representative set of countries. country_id is assigned sequentially
# starting at 1 in the order below.
COUNTRIES = [
    {"country_name": "United States", "phone_code": "+1", "country_code": "US", "is_eu_member": False},
    {"country_name": "Canada", "phone_code": "+1", "country_code": "CA", "is_eu_member": False},
    {"country_name": "United Kingdom", "phone_code": "+44", "country_code": "GB", "is_eu_member": False},
    {"country_name": "Germany", "phone_code": "+49", "country_code": "DE", "is_eu_member": True},
    {"country_name": "France", "phone_code": "+33", "country_code": "FR", "is_eu_member": True},
    {"country_name": "India", "phone_code": "+91", "country_code": "IN", "is_eu_member": False},
    {"country_name": "Australia", "phone_code": "+61", "country_code": "AU", "is_eu_member": False},
    {"country_name": "Mexico", "phone_code": "+52", "country_code": "MX", "is_eu_member": False},
    {"country_name": "Ireland", "phone_code": "+353", "country_code": "IE", "is_eu_member": True},
    {"country_name": "Sweden", "phone_code": "+46", "country_code": "SE", "is_eu_member": True},
]

# US states (the region the schema is themed around: "Virginia" dev schema).
# Every state belongs to country index 0 ("United States").
# Coordinates are approximate state centroids, used to jitter city/user/
# volunteer coordinates so they land in a plausible spot.
US_STATES = [
    ("Virginia", "VA", 37.4316, -78.6569),
    ("California", "CA", 36.7783, -119.4179),
    ("Texas", "TX", 31.9686, -99.9018),
    ("New York", "NY", 43.2994, -74.2179),
    ("North Carolina", "NC", 35.7596, -79.0193),
    ("Washington", "WA", 47.7511, -120.7401),
    ("Florida", "FL", 27.9944, -81.7603),
    ("Illinois", "IL", 40.6331, -89.3985),
    ("Georgia", "GA", 32.1656, -82.9001),
    ("Ohio", "OH", 40.4173, -82.9071),
    ("Pennsylvania", "PA", 41.2033, -77.1945),
    ("Colorado", "CO", 39.5501, -105.7821),
    ("Massachusetts", "MA", 42.4072, -71.3824),
    ("Arizona", "AZ", 34.0489, -111.0937),
    ("Maryland", "MD", 39.0458, -76.6413),
]

# A few real cities per state (name, lat, lon) — used to keep
# country -> state -> city geographically sane.
STATE_CITIES = {
    "Virginia": [("Richmond", 37.5407, -77.4360), ("Arlington", 38.8816, -77.0910), ("Norfolk", 36.8508, -76.2859)],
    "California": [("San Jose", 37.3382, -121.8863), ("Los Angeles", 34.0522, -118.2437), ("Sacramento", 38.5816, -121.4944)],
    "Texas": [("Austin", 30.2672, -97.7431), ("Houston", 29.7604, -95.3698), ("Dallas", 32.7767, -96.7970)],
    "New York": [("New York City", 40.7128, -74.0060), ("Buffalo", 42.8864, -78.8784), ("Albany", 42.6526, -73.7562)],
    "North Carolina": [("Charlotte", 35.2271, -80.8431), ("Raleigh", 35.7796, -78.6382), ("Durham", 35.9940, -78.8986)],
    "Washington": [("Seattle", 47.6062, -122.3321), ("Spokane", 47.6588, -117.4260), ("Tacoma", 47.2529, -122.4443)],
    "Florida": [("Miami", 25.7617, -80.1918), ("Orlando", 28.5383, -81.3792), ("Tampa", 27.9506, -82.4572)],
    "Illinois": [("Chicago", 41.8781, -87.6298), ("Springfield", 39.7817, -89.6501), ("Naperville", 41.7508, -88.1535)],
    "Georgia": [("Atlanta", 33.7490, -84.3880), ("Savannah", 32.0809, -81.0912), ("Augusta", 33.4735, -82.0105)],
    "Ohio": [("Columbus", 39.9612, -82.9988), ("Cleveland", 41.4993, -81.6944), ("Cincinnati", 39.1031, -84.5120)],
    "Pennsylvania": [("Philadelphia", 39.9526, -75.1652), ("Pittsburgh", 40.4406, -79.9959), ("Allentown", 40.6084, -75.4902)],
    "Colorado": [("Denver", 39.7392, -104.9903), ("Boulder", 40.0150, -105.2705), ("Aurora", 39.7294, -104.8319)],
    "Massachusetts": [("Boston", 42.3601, -71.0589), ("Worcester", 42.2626, -71.8023), ("Cambridge", 42.3736, -71.1097)],
    "Arizona": [("Phoenix", 33.4484, -112.0740), ("Tucson", 32.2226, -110.9747), ("Mesa", 33.4152, -111.8315)],
    "Maryland": [("Baltimore", 39.2904, -76.6122), ("Rockville", 39.0840, -77.1528), ("Annapolis", 38.9784, -76.4922)],
}

# Saayam help categories: cat_id follows the schema's hierarchical string
# convention (e.g. '1', '1.1'). A handful of top-level + child categories.
HELP_CATEGORIES = [
    ("1", "FOOD_ASSISTANCE", "Help accessing food, groceries, or meals"),
    ("1.1", "FOOD_DELIVERY", "Delivering food to those in need"),
    ("2", "SHELTER", "Help finding or maintaining shelter/housing"),
    ("2.1", "SHELTER_TEMPORARY", "Temporary/emergency shelter assistance"),
    ("3", "HEALTHCARE", "Health and medical assistance"),
    ("3.1", "HEALTHCARE_MENTAL", "Mental health support"),
    ("4", "EDUCATION", "Tutoring, mentoring, and educational support"),
    ("5", "TRANSPORTATION", "Rides and transportation assistance"),
    ("6", "CLOTHING", "Clothing donations and distribution"),
    ("7", "ELDER_CARE", "Assistance for elderly individuals"),
    ("8", "CHILD_CARE", "Childcare and youth support"),
    ("9", "DISASTER_RELIEF", "Disaster and emergency relief"),
    ("10", "LEGAL_AID", "Legal assistance and advocacy"),
    ("11", "EMPLOYMENT", "Job search and employment support"),
    ("12", "TRANSLATION", "Language translation/interpretation help"),
]

SKILL_LEVELS = ["BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"]

ORG_TYPES = ["non_profit", "for_profit"]
ORG_SIZES = ["small", "medium", "large"]

GENDERS = ["Male", "Female", "Non-binary", "Prefer not to say"]
TIME_ZONES = [
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
]


# ---------------------------------------------------------------------------
# ID generators (mimic the format used by the real schema's triggers)
# ---------------------------------------------------------------------------
def make_user_id(seq: int) -> str:
    """Mimics generate_sid(): SID-00-XXX-XXX-XXX-XXX-XXX (15-digit padded seq)."""
    padded = str(seq).zfill(15)
    parts = [padded[0:3], padded[3:6], padded[6:9], padded[9:12], padded[12:15]]
    return "SID-00-" + "-".join(parts)


def make_org_id(seq: int) -> str:
    """Mimics generate_org_id(): ORG-XXX-XXX-XXX-XXXX (13-digit padded seq)."""
    padded = str(seq).zfill(13)
    parts = [padded[0:3], padded[3:6], padded[6:9], padded[9:13]]
    return "ORG-" + "-".join(parts)


def make_state_id(state_code: str) -> str:
    """states.state_id is VARCHAR — use 'US-<code>' to keep it human-readable
    and guaranteed unique."""
    return f"US-{state_code}"


# ---------------------------------------------------------------------------
# Geo helpers
# ---------------------------------------------------------------------------
def jitter_point(lat: float, lon: float, max_offset_deg: float = 0.05) -> tuple[float, float]:
    """Nudge a lat/lon slightly so many records don't collide on the exact
    same point, while staying plausibly within the same city/state."""
    return (
        round(lat + random.uniform(-max_offset_deg, max_offset_deg), 6),
        round(lon + random.uniform(-max_offset_deg, max_offset_deg), 6),
    )


def to_wkt_point(lat: float, lon: float) -> str:
    """geography(Point, 4326) expects (lon lat) ordering in WKT."""
    return f"POINT({lon} {lat})"


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------
EPOCH_START = datetime(2025, 1, 1)
EPOCH_END = datetime(2026, 8, 31)


def random_created_at() -> datetime:
    delta = EPOCH_END - EPOCH_START
    return EPOCH_START + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def random_updated_after(created_at: datetime) -> datetime:
    """Return a timestamp >= created_at (satisfies created_at <= last_updated_at)."""
    delta = EPOCH_END - created_at
    if delta.total_seconds() <= 0:
        return created_at
    return created_at + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fmt_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")
