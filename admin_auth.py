"""
admin_auth.py — Hierarchical Municipal Administration Accounts & Zonal Permissions.

Two-Tier Administrative Hierarchy:
1. Chief Municipal Administrator ("Super Admin" / Central Commissioner):
   - City-wide oversight across all 6 zones of Hyderabad.
   - Access to central analytics, zonal comparison & audit credentials directory.
2. Regional Circle Administrators (6 GHMC Zonal Admins):
   - Strictly scoped to manage hazards within their respective geographic circles.
"""

from typing import Dict, Any, Optional

ADMIN_ACCOUNTS: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Tier 1: Chief Municipal Administrator (Central Super Admin)
    # -------------------------------------------------------------------------
    'admin': {
        'username': 'admin',
        'password': 'saferoad2026',
        'role': 'super_admin',
        'title': 'Chief Municipal Engineer & Central Commissioner',
        'zone_id': 'all',
        'zone_name': 'All Zones (City-Wide Jurisdiction)',
        'officer_name': 'Er. Venkat Usikarla',
        'office_address': 'GHMC Head Office, Tank Bund Road, Hyderabad',
        'email': 'commissioner.ghmc@saferoad.org',
    },
    'chief_admin': {
        'username': 'chief_admin',
        'password': 'saferoad2026',
        'role': 'super_admin',
        'title': 'Chief Municipal Engineer & Central Commissioner',
        'zone_id': 'all',
        'zone_name': 'All Zones (City-Wide Jurisdiction)',
        'officer_name': 'Er. Venkat Usikarla',
        'office_address': 'GHMC Head Office, Tank Bund Road, Hyderabad',
        'email': 'commissioner.ghmc@saferoad.org',
    },

    # -------------------------------------------------------------------------
    # Tier 2: Regional Zonal Circle Administrators (< 10 Hyderabad divisions)
    # -------------------------------------------------------------------------
    'admin_serilingampally': {
        'username': 'admin_serilingampally',
        'password': 'seri2026',
        'role': 'zonal_admin',
        'title': 'Superintending Circle Engineer (West)',
        'zone_id': 'serilingampally',
        'zone_name': 'Serilingampally Zone (West)',
        'officer_name': 'Er. K. V. Rao',
        'office_address': 'GHMC Zonal Office, Near Cyber Towers, Hitec City',
        'email': 'serilingampally.circle@ghmc.gov.in',
    },
    'admin_khairatabad': {
        'username': 'admin_khairatabad',
        'password': 'khair2026',
        'role': 'zonal_admin',
        'title': 'Executive Municipal Engineer (Central)',
        'zone_id': 'khairatabad',
        'zone_name': 'Khairatabad Zone (Central)',
        'officer_name': 'Er. P. Sunita',
        'office_address': 'GHMC Central Zone Office, Anand Nagar Colony, Khairatabad',
        'email': 'khairatabad.circle@ghmc.gov.in',
    },
    'admin_charminar': {
        'username': 'admin_charminar',
        'password': 'char2026',
        'role': 'zonal_admin',
        'title': 'Zonal Superintending Engineer (South)',
        'zone_id': 'charminar',
        'zone_name': 'Charminar Zone (South)',
        'officer_name': 'Er. Mohammed Asif',
        'office_address': 'GHMC South Zone Complex, Sardar Mahal, Charminar',
        'email': 'charminar.south@ghmc.gov.in',
    },
    'admin_secunderabad': {
        'username': 'admin_secunderabad',
        'password': 'sec2026',
        'role': 'zonal_admin',
        'title': 'Executive Engineer (North Circle)',
        'zone_id': 'secunderabad',
        'zone_name': 'Secunderabad Zone (North)',
        'officer_name': 'Er. B. Ramesh',
        'office_address': 'GHMC North Zone Complex, West Marredpally, Secunderabad',
        'email': 'secunderabad.circle@ghmc.gov.in',
    },
    'admin_kukatpally': {
        'username': 'admin_kukatpally',
        'password': 'kukat2026',
        'role': 'zonal_admin',
        'title': 'Executive Engineer (Kukatpally Division)',
        'zone_id': 'kukatpally',
        'zone_name': 'Kukatpally Zone (North-West)',
        'officer_name': 'Er. G. Sudhakar',
        'office_address': 'GHMC Kukatpally Zonal Office, Near Forum Mall, KPHB',
        'email': 'kukatpally.circle@ghmc.gov.in',
    },
    'admin_lbnagar': {
        'username': 'admin_lbnagar',
        'password': 'lbn2026',
        'role': 'zonal_admin',
        'title': 'Superintending Circle Engineer (East)',
        'zone_id': 'lbnagar',
        'zone_name': 'LB Nagar Zone (East)',
        'officer_name': 'Er. M. Srinivas',
        'office_address': 'GHMC East Zone Office, Ring Road, LB Nagar',
        'email': 'lbnagar.east@ghmc.gov.in',
    },
}


def authenticate_admin(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Validate credentials and return user profile if correct."""
    if not username or not password:
        return None
    user = ADMIN_ACCOUNTS.get(username.strip())
    if user and user['password'] == password.strip():
        return user
    return None


def get_all_credentials_for_super_admin() -> list:
    """Return public list of all administrator credentials for the Super Admin audit panel."""
    # Exclude alias duplicate
    accounts = []
    seen_users = set()
    for u, data in ADMIN_ACCOUNTS.items():
        if u == 'chief_admin':
            continue
        if u not in seen_users:
            seen_users.add(u)
            accounts.append({
                'username': data['username'],
                'password': data['password'],
                'role': data['role'],
                'role_label': 'Chief Administrator' if data['role'] == 'super_admin' else 'Zonal Circle Admin',
                'title': data['title'],
                'zone_name': data['zone_name'],
                'officer_name': data['officer_name'],
                'email': data['email'],
                'office_address': data['office_address'],
            })
    return accounts
