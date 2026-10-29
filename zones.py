"""
zones.py — GHMC (Greater Hyderabad Municipal Corporation) Zonal Divisions & Auto-Zoning Engine.

Hyderabad is officially divided into 6 administrative zones (less than 10):
1. Serilingampally Zone (West) — Hitec City, Gachibowli, Madhapur, Kondapur, Financial District
2. Khairatabad Zone (Central) — Banjara Hills, Jubilee Hills, Ameerpet, Panjagutta, Somajiguda
3. Charminar Zone (South) — Old City, Charminar, Falaknuma, Yakutpura, Bahadurpura
4. Secunderabad Zone (North) — Secunderabad Station, Begumpet, Clock Tower, Marredpally, Alwal
5. Kukatpally Zone (North-West) — Kukatpally, KPHB, Moosapet, Balanagar, Nizampet
6. LB Nagar Zone (East) — LB Nagar, Dilsukhnagar, Saroornagar, Kamineni, Nagole

Provides automatic zone detection from GPS coordinates (nearest centroid) and textual keyword matching.
"""

import math
from typing import Optional, Dict, Any, List

HYDERABAD_ZONES: Dict[str, Dict[str, Any]] = {
    'serilingampally': {
        'id': 'serilingampally',
        'name': 'Serilingampally Zone (West)',
        'short_name': 'Serilingampally',
        'officer_name': 'Er. K. V. Rao',
        'officer_title': 'Superintending Circle Engineer (West)',
        'office_address': 'GHMC Zonal Office, Near Cyber Towers, Hitec City',
        'contact_email': 'serilingampally.circle@ghmc.gov.in',
        'center_lat': 17.4485,
        'center_lng': 78.3750,
        'keywords': [
            'hitec', 'cyber', 'gachibowli', 'madhapur', 'kondapur', 'miyapur',
            'chandanagar', 'inorbit', 'financial district', 'nanakramguda',
            'raidurg', 'hafeezpet', 'bio-diversity', 'biodiversity', 'botanical',
            'durgam cheruvu', 'knowledge city', 'mindspace', 'tcs', 'wipro'
        ],
    },
    'khairatabad': {
        'id': 'khairatabad',
        'name': 'Khairatabad Zone (Central)',
        'short_name': 'Khairatabad',
        'officer_name': 'Er. P. Sunita',
        'officer_title': 'Executive Municipal Engineer (Central)',
        'office_address': 'GHMC Central Zone Office, Anand Nagar Colony, Khairatabad',
        'contact_email': 'khairatabad.circle@ghmc.gov.in',
        'center_lat': 17.4180,
        'center_lng': 78.4480,
        'keywords': [
            'banjara', 'jubilee', 'khairatabad', 'ameerpet', 'somajiguda',
            'panjagutta', 'punjagutta', 'care hospital', 'road no', 'peddamma',
            'srinagar colony', 'masab tank', 'lakdikapul', 'raj bhavan',
            'maitrivanam', 'film nagar', 'kbr park'
        ],
    },
    'charminar': {
        'id': 'charminar',
        'name': 'Charminar Zone (South)',
        'short_name': 'Charminar',
        'officer_name': 'Er. Mohammed Asif',
        'officer_title': 'Zonal Superintending Engineer (South)',
        'office_address': 'GHMC South Zone Complex, Sardar Mahal, Charminar',
        'contact_email': 'charminar.south@ghmc.gov.in',
        'center_lat': 17.3616,
        'center_lng': 78.4747,
        'keywords': [
            'charminar', 'yakutpura', 'old city', 'falaknuma', 'gulzar houz',
            'santoshnagar', 'bahadurpura', 'chandrayangutta', 'mehdipatnam',
            'tolichowki', 'pvnr', 'shah ali banda', 'laad bazaar', 'madina',
            'nayapul', 'salarmasjid', 'choumahalla', 'afzal gunj'
        ],
    },
    'secunderabad': {
        'id': 'secunderabad',
        'name': 'Secunderabad Zone (North)',
        'short_name': 'Secunderabad',
        'officer_name': 'Er. B. Ramesh',
        'officer_title': 'Executive Engineer (North Circle)',
        'office_address': 'GHMC North Zone Complex, West Marredpally, Secunderabad',
        'contact_email': 'secunderabad.circle@ghmc.gov.in',
        'center_lat': 17.4420,
        'center_lng': 78.4980,
        'keywords': [
            'secunderabad', 'begumpet', 'clock tower', 'paradise', 'tank bund',
            'marredpally', 'maredpally', 'alwal', 'tarnaka', 'prakash nagar',
            'bowenpally', 'karkhana', 'hussain sagar', 'ranigunj', 'rasoolpura',
            'station circle'
        ],
    },
    'kukatpally': {
        'id': 'kukatpally',
        'name': 'Kukatpally Zone (North-West)',
        'short_name': 'Kukatpally',
        'officer_name': 'Er. G. Sudhakar',
        'officer_title': 'Executive Engineer (Kukatpally Division)',
        'office_address': 'GHMC Kukatpally Zonal Office, Near Forum Mall, KPHB',
        'contact_email': 'kukatpally.circle@ghmc.gov.in',
        'center_lat': 17.4938,
        'center_lng': 78.3986,
        'keywords': [
            'kukatpally', 'kphb', 'moosapet', 'balanagar', 'nizampet',
            'y-junction', 'pragathi nagar', 'forum mall', 'nexus', 'jntu',
            'allwyn', 'hafeezpet', 'sanathnagar', 'bharat nagar'
        ],
    },
    'lbnagar': {
        'id': 'lbnagar',
        'name': 'LB Nagar Zone (East)',
        'short_name': 'LB Nagar',
        'officer_name': 'Er. M. Srinivas',
        'officer_title': 'Superintending Circle Engineer (East)',
        'office_address': 'GHMC East Zone Office, Ring Road, LB Nagar',
        'contact_email': 'lbnagar.east@ghmc.gov.in',
        'center_lat': 17.3457,
        'center_lng': 78.5522,
        'keywords': [
            'lb nagar', 'l.b. nagar', 'dilsukhnagar', 'saroornagar',
            'kamineni', 'ring road', 'hayathnagar', 'nagole', 'uppal',
            'chaitanyapuri', 'vanasthalipuram', 'kothapet', 'malakpet',
            'kothapet fruit market', 'alkapuri'
        ],
    },
}

DEFAULT_ZONE_ID = 'serilingampally'


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in metres between two GPS points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def detect_zone(lat: Optional[float] = None,
                lng: Optional[float] = None,
                location_name: str = "") -> Dict[str, Any]:
    """
    Automatically determine which GHMC Municipal Zone a hazard belongs to.
    
    Priority:
    1. Textual match on prominent locality keywords.
    2. GPS nearest centroid distance.
    3. Fallback to default zone (Serilingampally).
    """
    loc_lower = (location_name or "").lower()

    # 1. Text keyword search
    if loc_lower:
        best_zone = None
        max_matched_len = 0
        for z_id, z_data in HYDERABAD_ZONES.items():
            for kw in z_data['keywords']:
                if kw in loc_lower and len(kw) > max_matched_len:
                    best_zone = z_data
                    max_matched_len = len(kw)
        if best_zone:
            return best_zone

    # 2. GPS distance search
    if lat is not None and lng is not None:
        closest_zone = None
        min_dist = float('inf')
        for z_id, z_data in HYDERABAD_ZONES.items():
            dist = _haversine_distance(lat, lng, z_data['center_lat'], z_data['center_lng'])
            if dist < min_dist:
                min_dist = dist
                closest_zone = z_data
        if closest_zone:
            return closest_zone

    return HYDERABAD_ZONES[DEFAULT_ZONE_ID]


def get_all_zones() -> List[Dict[str, Any]]:
    """Return all 6 zones in a list."""
    return list(HYDERABAD_ZONES.values())


def get_zone_by_id(zone_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve zone dictionary by ID."""
    if not zone_id:
        return None
    return HYDERABAD_ZONES.get(zone_id.lower())
