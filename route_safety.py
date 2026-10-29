"""
route_safety.py — SafeRoute: Road Safety Corridor & Route Hazard Assessment Engine.

Analyzes driving trajectories between any starting and ending GPS points in Hyderabad,
detects all active road hazards along the route corridor (within buffer distance),
calculates a quantitative Route Safety Score (0–100), and generates localized safety advisories.
"""

import math
from typing import List, Dict, Any, Tuple

# Pre-configured popular commuter routes in Hyderabad for instant 1-click testing
SAMPLE_HYDERABAD_ROUTES = [
    {
        'id': 'hitec_to_charminar',
        'name': 'Hitec City to Charminar (IT Corridor to Old City)',
        'description': 'Commute from Cyber Towers through Mehdipatnam to historic Charminar',
        'start': {'name': 'Cyber Towers, Hitec City', 'lat': 17.4504, 'lng': 78.3808},
        'end': {'name': 'Charminar, Old City', 'lat': 17.3616, 'lng': 78.4747},
    },
    {
        'id': 'gachibowli_to_secunderabad',
        'name': 'Gachibowli to Secunderabad Station',
        'description': 'Major commuter corridor via Bio-Diversity, Begumpet, and Paradise',
        'start': {'name': 'Bio-Diversity Junction, Gachibowli', 'lat': 17.4294, 'lng': 78.3687},
        'end': {'name': 'Secunderabad Railway Station', 'lat': 17.4399, 'lng': 78.4983},
    },
    {
        'id': 'banjara_to_kukatpally',
        'name': 'Banjara Hills to Kukatpally (Road 12 to Nexus Mall)',
        'description': 'Cross-city transit through Jubilee Hills, Ameerpet and Moosapet',
        'start': {'name': 'Road No. 12, Banjara Hills', 'lat': 17.4156, 'lng': 78.4358},
        'end': {'name': 'Forum Nexus Mall, Kukatpally', 'lat': 17.4938, 'lng': 78.3986},
    },
    {
        'id': 'begumpet_to_lbnagar',
        'name': 'Begumpet to LB Nagar Ring Road',
        'description': 'North-to-East corridor traversing Tank Bund, Dilsukhnagar, and Ring Road',
        'start': {'name': 'Begumpet Metro Station', 'lat': 17.4442, 'lng': 78.4682},
        'end': {'name': 'LB Nagar Ring Road Junction', 'lat': 17.3457, 'lng': 78.5522},
    },
]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters between two coordinates."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def point_to_segment_distance(plat: float, plng: float,
                              alat: float, alng: float,
                              blat: float, blng: float) -> float:
    """
    Compute shortest distance in meters from point P to line segment AB.
    Projects onto the segment with Euclidean approximation for small distances.
    """
    dx = (blng - alng) * math.cos(math.radians((alat + blat) / 2))
    dy = blat - alat
    if dx == 0 and dy == 0:
        return haversine_m(plat, plng, alat, alng)

    # Parametric t on segment AB
    px = (plng - alng) * math.cos(math.radians((alat + blat) / 2))
    py = plat - alat
    t = (px * dx + py * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    closest_lat = alat + t * (blat - alat)
    closest_lng = alng + t * (blng - alng)
    return haversine_m(plat, plng, closest_lat, closest_lng)


def min_distance_to_polyline(plat: float, plng: float,
                             polyline: List[Tuple[float, float]]) -> float:
    """Return minimum distance in meters from point P to polyline [(lat, lng), ...]."""
    if not polyline:
        return float('inf')
    if len(polyline) == 1:
        return haversine_m(plat, plng, polyline[0][0], polyline[0][1])

    min_dist = float('inf')
    for i in range(len(polyline) - 1):
        d = point_to_segment_distance(
            plat, plng,
            polyline[i][0], polyline[i][1],
            polyline[i + 1][0], polyline[i + 1][1]
        )
        if d < min_dist:
            min_dist = d
    return min_dist


def evaluate_route_safety(polyline: List[Tuple[float, float]],
                          hazards: List[Dict[str, Any]],
                          corridor_buffer_m: float = 350.0) -> Dict[str, Any]:
    """
    Evaluate road safety along a driving route polyline.

    Parameters:
    - polyline: list of (lat, lng) tuples representing the driving trajectory
    - hazards: list of active hazard report dicts with 'lat', 'lng', 'severity', etc.
    - corridor_buffer_m: buffer radius in meters around the road centerline

    Returns:
    - Comprehensive safety report with score, classification, hazards list, and travel warnings.
    """
    detected_hazards = []
    total_penalty = 0

    # Total route distance estimation
    route_distance_km = 0.0
    for i in range(len(polyline) - 1):
        route_distance_km += haversine_m(
            polyline[i][0], polyline[i][1],
            polyline[i + 1][0], polyline[i + 1][1]
        ) / 1000.0

    for h in hazards:
        hlat = h.get('lat') or h.get('latitude')
        hlng = h.get('lng') or h.get('longitude')
        if hlat is None or hlng is None:
            continue

        dist_to_route = min_distance_to_polyline(hlat, hlng, polyline)
        if dist_to_route <= corridor_buffer_m:
            sev = int(h.get('severity', 3))
            
            # Severity penalty weighting
            penalty_map = {5: 22, 4: 14, 3: 8, 2: 4, 1: 2}
            penalty = penalty_map.get(sev, 8)
            
            # Critical hazard types get an extra alertness penalty
            if h.get('category') in ('pothole', 'unsafe_intersection', 'waterlogging'):
                penalty += 4
                
            total_penalty += penalty

            # Calculate approx distance from route start
            approx_dist_from_start_km = haversine_m(polyline[0][0], polyline[0][1], hlat, hlng) / 1000.0

            hazard_entry = dict(h)
            hazard_entry['distance_to_route_m'] = round(dist_to_route)
            hazard_entry['distance_from_start_km'] = round(approx_dist_from_start_km, 1)
            detected_hazards.append(hazard_entry)

    # Sort hazards by distance from starting point
    detected_hazards.sort(key=lambda x: x.get('distance_from_start_km', 0))

    # Safety Score calculation (0 to 100)
    safety_score = max(5, min(100, 100 - total_penalty))

    if safety_score >= 82:
        rating = 'Safe'
        rating_color = '#2a9d8f' # green
        rating_badge = 'Low Hazard Corridor'
        advisory = 'Route is generally in good condition. Standard road vigilance is advised.'
    elif safety_score >= 60:
        rating = 'Moderate Caution'
        rating_color = '#f4a261' # amber
        rating_badge = 'Moderate Hazards Present'
        advisory = f'{len(detected_hazards)} road hazard(s) flagged along this corridor. Maintain cautious speeds and stay alert.'
    else:
        rating = 'High Risk'
        rating_color = '#e63946' # danger red
        rating_badge = 'High Risk Route Alert'
        advisory = f'Critical road damage and severe hazards detected ({len(detected_hazards)} total). Two-wheelers and night commuters should consider alternative routes or reduce speeds.'

    return {
        'safety_score': safety_score,
        'rating': rating,
        'rating_color': rating_color,
        'rating_badge': rating_badge,
        'advisory': advisory,
        'hazard_count': len(detected_hazards),
        'hazards': detected_hazards,
        'route_distance_km': round(route_distance_km, 1),
        'corridor_buffer_m': corridor_buffer_m,
    }
