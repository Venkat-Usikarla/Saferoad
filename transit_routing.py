"""
transit_routing.py — Hyderabad Public Transport Route Finder (Metro, TSRTC Bus, MMTS).

Computes optimal multi-modal public transport routes between any Origin (A) and
Destination (B) in Hyderabad, including:
1. Hyderabad Metro Rail (Red, Blue, Green lines with automatic interchanges)
2. TSRTC City Bus Corridors (Metro Express / AC / Ordinary routes)
3. MMTS Suburban Rail
4. SafeRoad Last-Mile Hazard Warnings near boarding/alighting stations
"""

import math
from collections import deque
from typing import List, Dict, Any, Tuple, Optional

# ---------------------------------------------------------------------------
# Geospatial helpers
# ---------------------------------------------------------------------------

def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Hyderabad Metro Rail (HMRL) Network Data
# ---------------------------------------------------------------------------

METRO_STATIONS: Dict[str, Dict[str, Any]] = {
    # Red Line (Corridor I: Miyapur -> LB Nagar)
    'miyapur': {'name': 'Miyapur', 'lat': 17.4966, 'lng': 78.3731, 'lines': ['Red']},
    'jntu': {'name': 'JNTU College', 'lat': 17.4987, 'lng': 78.3888, 'lines': ['Red']},
    'kphb': {'name': 'KPHB Colony', 'lat': 17.4937, 'lng': 78.4017, 'lines': ['Red']},
    'kukatpally': {'name': 'Kukatpally', 'lat': 17.4850, 'lng': 78.4116, 'lines': ['Red']},
    'balanagar': {'name': 'Balanagar', 'lat': 17.4762, 'lng': 78.4215, 'lines': ['Red']},
    'moosapet': {'name': 'Moosapet', 'lat': 17.4682, 'lng': 78.4264, 'lines': ['Red']},
    'bharat_nagar': {'name': 'Bharat Nagar', 'lat': 17.4606, 'lng': 78.4316, 'lines': ['Red']},
    'erragadda': {'name': 'Erragadda', 'lat': 17.4533, 'lng': 78.4366, 'lines': ['Red']},
    'esi': {'name': 'ESI Hospital', 'lat': 17.4472, 'lng': 78.4408, 'lines': ['Red']},
    'sr_nagar': {'name': 'SR Nagar', 'lat': 17.4418, 'lng': 78.4446, 'lines': ['Red']},
    'ameerpet': {'name': 'Ameerpet (Interchange)', 'lat': 17.4357, 'lng': 78.4447, 'lines': ['Red', 'Blue']},
    'panjagutta': {'name': 'Panjagutta', 'lat': 17.4258, 'lng': 78.4512, 'lines': ['Red']},
    'irrum_manzil': {'name': 'Irrum Manzil', 'lat': 17.4202, 'lng': 78.4552, 'lines': ['Red']},
    'khairatabad': {'name': 'Khairatabad', 'lat': 17.4109, 'lng': 78.4607, 'lines': ['Red']},
    'lakdikapul': {'name': 'Lakdikapul', 'lat': 17.4046, 'lng': 78.4631, 'lines': ['Red']},
    'assembly': {'name': 'Assembly', 'lat': 17.3982, 'lng': 78.4685, 'lines': ['Red']},
    'nampally': {'name': 'Nampally', 'lat': 17.3921, 'lng': 78.4697, 'lines': ['Red']},
    'gandhi_bhavan': {'name': 'Gandhi Bhavan', 'lat': 17.3863, 'lng': 78.4735, 'lines': ['Red']},
    'omc': {'name': 'Osmania Medical College', 'lat': 17.3821, 'lng': 78.4810, 'lines': ['Red']},
    'mgbs': {'name': 'MGBS (Interchange)', 'lat': 17.3782, 'lng': 78.4864, 'lines': ['Red', 'Green']},
    'malakpet': {'name': 'Malakpet', 'lat': 17.3752, 'lng': 78.4976, 'lines': ['Red']},
    'new_market': {'name': 'New Market', 'lat': 17.3735, 'lng': 78.5042, 'lines': ['Red']},
    'musarambagh': {'name': 'Musarambagh', 'lat': 17.3712, 'lng': 78.5123, 'lines': ['Red']},
    'dilsukhnagar': {'name': 'Dilsukhnagar', 'lat': 17.3688, 'lng': 78.5250, 'lines': ['Red']},
    'chaitanyapuri': {'name': 'Chaitanyapuri', 'lat': 17.3682, 'lng': 78.5356, 'lines': ['Red']},
    'victoria_memorial': {'name': 'Victoria Memorial', 'lat': 17.3610, 'lng': 78.5442, 'lines': ['Red']},
    'lb_nagar': {'name': 'LB Nagar', 'lat': 17.3497, 'lng': 78.5478, 'lines': ['Red']},

    # Blue Line (Corridor III: Raidurg -> Nagole)
    'raidurg': {'name': 'Raidurg (Mindspace)', 'lat': 17.4422, 'lng': 78.3772, 'lines': ['Blue']},
    'hitec_city': {'name': 'Hitec City', 'lat': 17.4488, 'lng': 78.3831, 'lines': ['Blue']},
    'durgam_cheruvu': {'name': 'Durgam Cheruvu', 'lat': 17.4429, 'lng': 78.3895, 'lines': ['Blue']},
    'madhapur': {'name': 'Madhapur', 'lat': 17.4373, 'lng': 78.3982, 'lines': ['Blue']},
    'peddamma_gudi': {'name': 'Peddamma Gudi', 'lat': 17.4307, 'lng': 78.4084, 'lines': ['Blue']},
    'jubilee_checkpost': {'name': 'Jubilee Hills Checkpost', 'lat': 17.4287, 'lng': 78.4148, 'lines': ['Blue']},
    'road_no_5': {'name': 'Road No 5 Jubilee Hills', 'lat': 17.4297, 'lng': 78.4235, 'lines': ['Blue']},
    'yusufguda': {'name': 'Yusufguda', 'lat': 17.4342, 'lng': 78.4314, 'lines': ['Blue']},
    'madhura_nagar': {'name': 'Madhura Nagar', 'lat': 17.4368, 'lng': 78.4383, 'lines': ['Blue']},
    # ameerpet already defined
    'begumpet': {'name': 'Begumpet', 'lat': 17.4375, 'lng': 78.4567, 'lines': ['Blue']},
    'prakash_nagar': {'name': 'Prakash Nagar', 'lat': 17.4418, 'lng': 78.4660, 'lines': ['Blue']},
    'rasoolpura': {'name': 'Rasoolpura', 'lat': 17.4435, 'lng': 78.4754, 'lines': ['Blue']},
    'paradise': {'name': 'Paradise', 'lat': 17.4435, 'lng': 78.4852, 'lines': ['Blue']},
    'parade_ground': {'name': 'Parade Ground (Interchange)', 'lat': 17.4433, 'lng': 78.4975, 'lines': ['Blue', 'Green']},
    'secunderabad_east': {'name': 'Secunderabad East', 'lat': 17.4357, 'lng': 78.5050, 'lines': ['Blue']},
    'mettuguda': {'name': 'Mettuguda', 'lat': 17.4339, 'lng': 78.5186, 'lines': ['Blue']},
    'tarnaka': {'name': 'Tarnaka', 'lat': 17.4280, 'lng': 78.5326, 'lines': ['Blue']},
    'habsiguda': {'name': 'Habsiguda', 'lat': 17.4201, 'lng': 78.5403, 'lines': ['Blue']},
    'ngri': {'name': 'NGRI', 'lat': 17.4137, 'lng': 78.5484, 'lines': ['Blue']},
    'stadium': {'name': 'Stadium', 'lat': 17.4071, 'lng': 78.5546, 'lines': ['Blue']},
    'uppal': {'name': 'Uppal', 'lat': 17.4005, 'lng': 78.5601, 'lines': ['Blue']},
    'nagole': {'name': 'Nagole', 'lat': 17.3908, 'lng': 78.5586, 'lines': ['Blue']},

    # Green Line (Corridor II: JBS Parade Ground -> MGBS)
    'secunderabad_west': {'name': 'Secunderabad West', 'lat': 17.4337, 'lng': 78.4988, 'lines': ['Green']},
    'gandhi_hospital': {'name': 'Gandhi Hospital', 'lat': 17.4254, 'lng': 78.5015, 'lines': ['Green']},
    'musheerabad': {'name': 'Musheerabad', 'lat': 17.4193, 'lng': 78.4989, 'lines': ['Green']},
    'rtc_x_roads': {'name': 'RTC X Roads', 'lat': 17.4067, 'lng': 78.4968, 'lines': ['Green']},
    'chikkadpally': {'name': 'Chikkadpally', 'lat': 17.4003, 'lng': 78.4956, 'lines': ['Green']},
    'narayanguda': {'name': 'Narayanguda', 'lat': 17.3941, 'lng': 78.4932, 'lines': ['Green']},
    'sultan_bazaar': {'name': 'Sultan Bazaar', 'lat': 17.3865, 'lng': 78.4882, 'lines': ['Green']},
}

METRO_LINES: Dict[str, List[str]] = {
    'Red': [
        'miyapur', 'jntu', 'kphb', 'kukatpally', 'balanagar', 'moosapet',
        'bharat_nagar', 'erragadda', 'esi', 'sr_nagar', 'ameerpet',
        'panjagutta', 'irrum_manzil', 'khairatabad', 'lakdikapul', 'assembly',
        'nampally', 'gandhi_bhavan', 'omc', 'mgbs', 'malakpet', 'new_market',
        'musarambagh', 'dilsukhnagar', 'chaitanyapuri', 'victoria_memorial', 'lb_nagar'
    ],
    'Blue': [
        'raidurg', 'hitec_city', 'durgam_cheruvu', 'madhapur', 'peddamma_gudi',
        'jubilee_checkpost', 'road_no_5', 'yusufguda', 'madhura_nagar',
        'ameerpet', 'begumpet', 'prakash_nagar', 'rasoolpura', 'paradise',
        'parade_ground', 'secunderabad_east', 'mettuguda', 'tarnaka',
        'habsiguda', 'ngri', 'stadium', 'uppal', 'nagole'
    ],
    'Green': [
        'parade_ground', 'secunderabad_west', 'gandhi_hospital', 'musheerabad',
        'rtc_x_roads', 'chikkadpally', 'narayanguda', 'sultan_bazaar', 'mgbs'
    ],
}

LINE_COLORS = {
    'Red': '#e63946',
    'Blue': '#1d4ed8',
    'Green': '#15803d',
}


def _build_metro_graph() -> Dict[str, List[Tuple[str, str]]]:
    graph: Dict[str, List[Tuple[str, str]]] = {s: [] for s in METRO_STATIONS}
    for line_name, stations in METRO_LINES.items():
        for i in range(len(stations) - 1):
            u, v = stations[i], stations[i + 1]
            graph[u].append((v, line_name))
            graph[v].append((u, line_name))
    return graph


METRO_GRAPH = _build_metro_graph()


def find_nearest_metro(lat: float, lng: float) -> Tuple[str, float]:
    best_id = None
    best_dist = float('inf')
    for sid, sdata in METRO_STATIONS.items():
        d = haversine_m(lat, lng, sdata['lat'], sdata['lng'])
        if d < best_dist:
            best_dist = d
            best_id = sid
    return best_id, best_dist


def find_metro_path(start_id: str, end_id: str) -> List[Tuple[str, Optional[str]]]:
    """BFS shortest path returning [(station_id, line_used_to_reach_it), ...]."""
    if start_id == end_id:
        return [(start_id, None)]
    queue = deque([(start_id, [(start_id, None)])])
    visited = {start_id}
    while queue:
        curr, path = queue.popleft()
        for nxt, line_name in METRO_GRAPH.get(curr, []):
            if nxt in visited:
                continue
            new_path = path + [(nxt, line_name)]
            if nxt == end_id:
                return new_path
            visited.add(nxt)
            queue.append((nxt, new_path))
    return []


# ---------------------------------------------------------------------------
# MMTS Suburban Rail Network Data
# ---------------------------------------------------------------------------

MMTS_STATIONS = [
    {'id': 'lingampalli', 'name': 'Lingampalli MMTS', 'lat': 17.4840, 'lng': 78.3168},
    {'id': 'hitec_mmts', 'name': 'Hitec City MMTS', 'lat': 17.4682, 'lng': 78.3831},
    {'id': 'borabanda', 'name': 'Borabanda MMTS', 'lat': 17.4547, 'lng': 78.4146},
    {'id': 'begumpet_mmts', 'name': 'Begumpet MMTS', 'lat': 17.4395, 'lng': 78.4578},
    {'id': 'secunderabad_mmts', 'name': 'Secunderabad Junction MMTS', 'lat': 17.4344, 'lng': 78.5016},
    {'id': 'nampally_mmts', 'name': 'Hyderabad (Nampally) MMTS', 'lat': 17.3902, 'lng': 78.4675},
    {'id': 'kachiguda_mmts', 'name': 'Kachiguda MMTS', 'lat': 17.3879, 'lng': 78.4988},
    {'id': 'falaknuma_mmts', 'name': 'Falaknuma MMTS', 'lat': 17.3340, 'lng': 78.4686},
]


# ---------------------------------------------------------------------------
# TSRTC City Bus Hubs & Corridors
# ---------------------------------------------------------------------------

TSRTC_HUBS = [
    {'name': 'Gachibowli Bus Stop', 'lat': 17.4401, 'lng': 78.3489, 'routes': ['216', '195', '217']},
    {'name': 'Hitec City / Mindspace Stop', 'lat': 17.4435, 'lng': 78.3772, 'routes': ['10H', '127K', '195', '222A']},
    {'name': 'Madhapur Bus Stop', 'lat': 17.4483, 'lng': 78.3915, 'routes': ['10H', '127K', '194']},
    {'name': 'Jubilee Hills Checkpost', 'lat': 17.4287, 'lng': 78.4148, 'routes': ['127K', '47L', '113M']},
    {'name': 'Banjara Hills Rd 12 / Care', 'lat': 17.4126, 'lng': 78.4398, 'routes': ['127K', '47L', '19M']},
    {'name': 'Mehdipatnam Bus Terminal', 'lat': 17.3958, 'lng': 78.4312, 'routes': ['49M', '5K', '216', '113M']},
    {'name': 'Ameerpet / Maitrivanam', 'lat': 17.4375, 'lng': 78.4482, 'routes': ['10H', '218', '222A', '9X']},
    {'name': 'Begumpet / Shoppers Stop', 'lat': 17.4447, 'lng': 78.4664, 'routes': ['10H', '49M', '47L']},
    {'name': 'Secunderabad Rathifile Bus Station', 'lat': 17.4368, 'lng': 78.5008, 'routes': ['10H', '49M', '5K', '47L', '290U']},
    {'name': 'Koti / Sultan Bazaar Bus Terminal', 'lat': 17.3850, 'lng': 78.4867, 'routes': ['127K', '9X', '290U', '113M']},
    {'name': 'Charminar Bus Terminal', 'lat': 17.3616, 'lng': 78.4747, 'routes': ['2Z', '7Z', '8A', '65S']},
    {'name': 'LB Nagar Ring Road Hub', 'lat': 17.3457, 'lng': 78.5522, 'routes': ['290U', '113M', '277']},
    {'name': 'Kukatpally / KPHB Bus Stop', 'lat': 17.4849, 'lng': 78.4138, 'routes': ['218', '222A', '10H']},
    {'name': 'Miyapur X Roads Bus Hub', 'lat': 17.4969, 'lng': 78.3614, 'routes': ['218', '222A', '219']},
    {'name': 'Uppal X Roads Bus Hub', 'lat': 17.4058, 'lng': 78.5591, 'routes': ['113M', '290U', '18']},
]


def _find_nearest_hub(lat: float, lng: float, hubs: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], float]:
    best = hubs[0]
    best_d = float('inf')
    for h in hubs:
        d = haversine_m(lat, lng, h['lat'], h['lng'])
        if d < best_d:
            best_d = d
            best = h
    return best, best_d


def _check_station_hazards(lat: float, lng: float, hazards: List[Dict[str, Any]], radius_m: float = 500.0) -> List[Dict[str, Any]]:
    nearby = []
    for h in hazards:
        hlat, hlng = h.get('lat'), h.get('lng')
        if hlat is None or hlng is None:
            continue
        d = haversine_m(lat, lng, hlat, hlng)
        if d <= radius_m:
            nearby.append({
                'report_id': h.get('report_id'),
                'category_label': h.get('category_label', h.get('category')),
                'location_name': h.get('location_name'),
                'severity': h.get('severity', 3),
                'distance_m': round(d),
            })
    return nearby


# ---------------------------------------------------------------------------
# Public API: Find Best Public Transport Options (A -> B)
# ---------------------------------------------------------------------------

def find_public_transport_routes(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    hazards: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Compute ranked public transport options (Metro, TSRTC Bus, MMTS) from A to B
    with fares, estimated times, transfers, map polylines, and SafeRoad warnings.
    """
    hazards = hazards or []
    direct_dist_km = haversine_m(start_lat, start_lng, end_lat, end_lng) / 1000.0
    options = []

    # ------------------------------------------------------------------
    # 1. HYDERABAD METRO RAIL OPTION
    # ------------------------------------------------------------------
    start_st_id, start_walk_m = find_nearest_metro(start_lat, start_lng)
    end_st_id, end_walk_m = find_nearest_metro(end_lat, end_lng)
    start_st = METRO_STATIONS[start_st_id]
    end_st = METRO_STATIONS[end_st_id]

    metro_path = find_metro_path(start_st_id, end_st_id)
    if len(metro_path) >= 2:
        # Group into line segments (detect interchanges)
        segments = []
        curr_line = metro_path[1][1]
        seg_start = metro_path[0][0]
        seg_stations = [METRO_STATIONS[seg_start]['name']]
        seg_coords = [[METRO_STATIONS[seg_start]['lat'], METRO_STATIONS[seg_start]['lng']]]

        for idx in range(1, len(metro_path)):
            st_id, used_line = metro_path[idx]
            st_obj = METRO_STATIONS[st_id]
            if used_line != curr_line:
                segments.append({
                    'line': curr_line,
                    'color': LINE_COLORS.get(curr_line, '#1d4ed8'),
                    'from_station': seg_stations[0],
                    'to_station': seg_stations[-1],
                    'stops': len(seg_stations) - 1,
                    'coords': list(seg_coords),
                })
                curr_line = used_line
                seg_stations = [seg_stations[-1], st_obj['name']]
                seg_coords = [seg_coords[-1], [st_obj['lat'], st_obj['lng']]]
            else:
                seg_stations.append(st_obj['name'])
                seg_coords.append([st_obj['lat'], st_obj['lng']])

        segments.append({
            'line': curr_line,
            'color': LINE_COLORS.get(curr_line, '#1d4ed8'),
            'from_station': seg_stations[0],
            'to_station': seg_stations[-1],
            'stops': len(seg_stations) - 1,
            'coords': list(seg_coords),
        })

        total_stops = len(metro_path) - 1
        transfers = len(segments) - 1
        # Metro speed ~2.2 mins per stop + 4 mins per transfer + last-mile access
        access_min = round((start_walk_m + end_walk_m) / 350.0) + 4
        metro_ride_min = round(total_stops * 2.2) + (transfers * 4)
        total_metro_min = max(12, access_min + metro_ride_min)

        # HMRL Fare table approximation (Rs 10 to Rs 60)
        metro_fare = min(60, max(10, 10 + (total_stops // 2) * 5))

        steps = []
        if start_walk_m <= 900:
            steps.append(f"Walk {round(start_walk_m)} m ({max(2, round(start_walk_m/80))} min) to {start_st['name']} Metro Station")
        else:
            steps.append(f"Take Auto / Rapido ({round(start_walk_m/1000, 1)} km) to {start_st['name']} Metro Station")

        for i, seg in enumerate(segments):
            steps.append(
                f"Board {seg['line']} Line Metro at {seg['from_station']} → Get off at {seg['to_station']} ({seg['stops']} stops)"
            )
            if i < len(segments) - 1:
                steps.append(f"Interchange at {seg['to_station']} to {segments[i+1]['line']} Line")

        if end_walk_m <= 900:
            steps.append(f"Walk {round(end_walk_m)} m ({max(2, round(end_walk_m/80))} min) to Destination")
        else:
            steps.append(f"Take Auto / Feeder Bus ({round(end_walk_m/1000, 1)} km) from {end_st['name']} to Destination")

        station_hazards = (
            _check_station_hazards(start_st['lat'], start_st['lng'], hazards, 500)
            + _check_station_hazards(end_st['lat'], end_st['lng'], hazards, 500)
        )

        # Full polyline for map
        full_coords = [[start_lat, start_lng]]
        for seg in segments:
            full_coords.extend(seg['coords'])
        full_coords.append([end_lat, end_lng])

        options.append({
            'id': 'metro',
            'mode': 'Hyderabad Metro Rail',
            'badge': 'Fastest & Traffic-Free',
            'badge_color': '#1d4ed8',
            'icon': 'fa-train-subway',
            'duration_min': total_metro_min,
            'fare_inr': metro_fare,
            'frequency': 'Every 4–6 mins',
            'transfers': transfers,
            'stops_count': total_stops,
            'boarding_point': start_st['name'],
            'alighting_point': end_st['name'],
            'segments': segments,
            'polyline': full_coords,
            'steps': steps,
            'station_hazards': station_hazards,
        })

    # ------------------------------------------------------------------
    # 2. HYBRID MULTI-MODAL OPTION: TSRTC FEEDER BUS + METRO RAIL
    # ------------------------------------------------------------------
    # Real-world Hyderabad commute: Takes a TSRTC feeder bus to avoid traffic
    # congestion, rides the high-speed Metro spine, and connects via bus/walk.
    bus_start, bus_start_dist = _find_nearest_hub(start_lat, start_lng, TSRTC_HUBS)
    bus_end, bus_end_dist = _find_nearest_hub(end_lat, end_lng, TSRTC_HUBS)

    if len(metro_path) >= 2:
        hybrid_segments = []
        hybrid_steps = []
        hybrid_polyline = [[start_lat, start_lng]]
        hybrid_duration = 0
        hybrid_fare = 0
        hybrid_transfers = 0
        hybrid_stops = 0

        # Leg 1: TSRTC Feeder Bus to Metro (if distance > 600m or bus stop closer)
        feeder_dist_km = haversine_m(bus_start['lat'], bus_start['lng'], start_st['lat'], start_st['lng']) / 1000.0
        if start_walk_m > 650 or feeder_dist_km >= 1.2:
            f_stops = max(2, round(feeder_dist_km * 1.6))
            f_time = max(8, round(feeder_dist_km * 3.2) + 5)
            f_route = bus_start['routes'][0] if bus_start['routes'] else 'Feeder'
            hybrid_steps.append(
                f"1. Board TSRTC Feeder Bus ({f_route}) at {bus_start['name']} → Alight at {start_st['name']} Metro ({f_stops} stops, ~{f_time} min)"
            )
            hybrid_segments.append({
                'line': f'TSRTC Feeder Bus ({f_route})',
                'color': '#15803d',
                'from_station': bus_start['name'],
                'to_station': f"{start_st['name']} Metro",
                'stops': f_stops,
                'coords': [[start_lat, start_lng], [bus_start['lat'], bus_start['lng']], [start_st['lat'], start_st['lng']]],
            })
            hybrid_polyline.extend([[bus_start['lat'], bus_start['lng']], [start_st['lat'], start_st['lng']]])
            hybrid_fare += 15
            hybrid_duration += f_time
            hybrid_stops += f_stops
            hybrid_transfers += 1
        else:
            w_time = max(2, round(start_walk_m / 80))
            hybrid_steps.append(f"1. Walk {round(start_walk_m)} m (~{w_time} min) to {start_st['name']} Metro Station")
            hybrid_duration += w_time
            hybrid_polyline.append([start_st['lat'], start_st['lng']])

        # Leg 2: Metro Rail Core Spine (high speed, avoids city road jams)
        for s_idx, seg in enumerate(segments):
            hybrid_segments.append(dict(seg))
            hybrid_steps.append(
                f"2.{s_idx + 1} Board {seg['line']} Line Metro: {seg['from_station']} → {seg['to_station']} ({seg['stops']} stops)"
            )
            if s_idx < len(segments) - 1:
                hybrid_steps.append(f"   ↳ Interchange at {seg['to_station']} to {segments[s_idx + 1]['line']} Line")
                hybrid_transfers += 1

        hybrid_fare += metro_fare
        hybrid_duration += metro_ride_min
        hybrid_stops += total_stops
        for seg in segments:
            hybrid_polyline.extend(seg['coords'])

        # Leg 3: Last-mile TSRTC Connecting Bus or Walk
        last_bus_dist_km = haversine_m(end_st['lat'], end_st['lng'], bus_end['lat'], bus_end['lng']) / 1000.0
        if end_walk_m > 650 or last_bus_dist_km >= 1.2:
            c_stops = max(2, round(last_bus_dist_km * 1.6))
            c_time = max(8, round(last_bus_dist_km * 3.2) + 5)
            c_route = bus_end['routes'][0] if bus_end['routes'] else 'Connecting'
            hybrid_steps.append(
                f"3. At {end_st['name']} Metro, board TSRTC Connecting Bus ({c_route}) → Alight at {bus_end['name']} ({c_stops} stops, ~{c_time} min)"
            )
            hybrid_segments.append({
                'line': f'TSRTC Connecting Bus ({c_route})',
                'color': '#15803d',
                'from_station': f"{end_st['name']} Metro",
                'to_station': bus_end['name'],
                'stops': c_stops,
                'coords': [[end_st['lat'], end_st['lng']], [bus_end['lat'], bus_end['lng']], [end_lat, end_lng]],
            })
            hybrid_polyline.extend([[bus_end['lat'], bus_end['lng']], [end_lat, end_lng]])
            hybrid_fare += 15
            hybrid_duration += c_time
            hybrid_stops += c_stops
            hybrid_transfers += 1
        else:
            w_time = max(2, round(end_walk_m / 80))
            hybrid_steps.append(f"3. Walk {round(end_walk_m)} m (~{w_time} min) from {end_st['name']} Metro to Destination")
            hybrid_duration += w_time
            hybrid_polyline.append([end_lat, end_lng])

        hybrid_hazards = (
            _check_station_hazards(bus_start['lat'], bus_start['lng'], hazards, 500)
            + _check_station_hazards(start_st['lat'], start_st['lng'], hazards, 500)
            + _check_station_hazards(end_st['lat'], end_st['lng'], hazards, 500)
            + _check_station_hazards(bus_end['lat'], bus_end['lng'], hazards, 500)
        )
        # Deduplicate hazards by report_id
        seen_hids = set()
        unique_hybrid_hazards = []
        for h in hybrid_hazards:
            if h['report_id'] not in seen_hids:
                seen_hids.add(h['report_id'])
                unique_hybrid_hazards.append(h)

        options.append({
            'id': 'hybrid',
            'mode': 'Hybrid: TSRTC Feeder Bus + Hyderabad Metro',
            'badge': 'Integrated Multi-Modal (Best Balance)',
            'badge_color': '#d97706',
            'icon': 'fa-shuffle',
            'duration_min': hybrid_duration,
            'fare_inr': hybrid_fare,
            'frequency': 'Bus every 8–10m + Metro every 4–6m',
            'transfers': hybrid_transfers,
            'stops_count': hybrid_stops,
            'boarding_point': f"{bus_start['name']} / {start_st['name']} Metro",
            'alighting_point': f"{end_st['name']} Metro / {bus_end['name']}",
            'segments': hybrid_segments,
            'polyline': hybrid_polyline,
            'steps': hybrid_steps,
            'station_hazards': unique_hybrid_hazards,
        })

    # ------------------------------------------------------------------
    # 2. TSRTC CITY BUS OPTION
    # ------------------------------------------------------------------
    bus_start, bus_start_dist = _find_nearest_hub(start_lat, start_lng, TSRTC_HUBS)
    bus_end, bus_end_dist = _find_nearest_hub(end_lat, end_lng, TSRTC_HUBS)

    common_routes = [r for r in bus_start['routes'] if r in bus_end['routes']]
    if common_routes:
        route_label = f"Direct Bus {', '.join(common_routes[:2])}"
        bus_transfers = 0
        bus_steps = [
            f"Walk / Auto ({round(bus_start_dist)} m) to {bus_start['name']}",
            f"Board TSRTC Metro Express Bus ({', '.join(common_routes[:2])}) towards {bus_end['name']}",
            f"Alight at {bus_end['name']} and proceed {round(bus_end_dist)} m to Destination",
        ]
    else:
        r1 = bus_start['routes'][0]
        r2 = bus_end['routes'][0]
        route_label = f"Bus {r1} → Transfer → Bus {r2}"
        bus_transfers = 1
        bus_steps = [
            f"Walk / Auto ({round(bus_start_dist)} m) to {bus_start['name']}",
            f"Board TSRTC Bus {r1} towards Central Hub (Ameerpet / Secunderabad / Koti)",
            f"Transfer to TSRTC Bus {r2} towards {bus_end['name']}",
            f"Alight at {bus_end['name']} and proceed {round(bus_end_dist)} m to Destination",
        ]

    bus_duration = max(18, round(direct_dist_km * 3.8) + (bus_transfers * 10) + 6)
    bus_fare = min(45, max(15, 15 + round(direct_dist_km * 1.5)))
    bus_hazards = (
        _check_station_hazards(bus_start['lat'], bus_start['lng'], hazards, 500)
        + _check_station_hazards(bus_end['lat'], bus_end['lng'], hazards, 500)
    )

    options.append({
        'id': 'bus',
        'mode': f'TSRTC City Bus ({route_label})',
        'badge': 'Most Economical',
        'badge_color': '#15803d',
        'icon': 'fa-bus',
        'duration_min': bus_duration,
        'fare_inr': bus_fare,
        'frequency': 'Every 10–15 mins',
        'transfers': bus_transfers,
        'stops_count': max(3, round(direct_dist_km * 1.4)),
        'boarding_point': bus_start['name'],
        'alighting_point': bus_end['name'],
        'segments': [{
            'line': 'TSRTC Bus',
            'color': '#15803d',
            'from_station': bus_start['name'],
            'to_station': bus_end['name'],
            'coords': [[bus_start['lat'], bus_start['lng']], [bus_end['lat'], bus_end['lng']]],
        }],
        'polyline': [
            [start_lat, start_lng],
            [bus_start['lat'], bus_start['lng']],
            [bus_end['lat'], bus_end['lng']],
            [end_lat, end_lng],
        ],
        'steps': bus_steps,
        'station_hazards': bus_hazards,
    })

    # ------------------------------------------------------------------
    # 3. MMTS SUBURBAN RAIL OPTION
    # ------------------------------------------------------------------
    mmts_start, mmts_start_dist = _find_nearest_hub(start_lat, start_lng, MMTS_STATIONS)
    mmts_end, mmts_end_dist = _find_nearest_hub(end_lat, end_lng, MMTS_STATIONS)
    if mmts_start['id'] != mmts_end['id'] and mmts_start_dist <= 5500 and mmts_end_dist <= 5500:
        mmts_dist_km = haversine_m(mmts_start['lat'], mmts_start['lng'], mmts_end['lat'], mmts_end['lng']) / 1000.0
        mmts_duration = max(20, round(mmts_dist_km * 2.1) + round((mmts_start_dist + mmts_end_dist) / 400.0) + 8)
        mmts_hazards = (
            _check_station_hazards(mmts_start['lat'], mmts_start['lng'], hazards, 500)
            + _check_station_hazards(mmts_end['lat'], mmts_end['lng'], hazards, 500)
        )
        options.append({
            'id': 'mmts',
            'mode': 'MMTS Suburban Rail',
            'badge': 'Ultra-Low Fare (₹5–₹15)',
            'badge_color': '#7c3aed',
            'icon': 'fa-train',
            'duration_min': mmts_duration,
            'fare_inr': 10 if mmts_dist_km < 15 else 15,
            'frequency': 'Every 25–35 mins',
            'transfers': 0,
            'stops_count': max(2, round(mmts_dist_km / 2.5)),
            'boarding_point': mmts_start['name'],
            'alighting_point': mmts_end['name'],
            'segments': [{
                'line': 'MMTS Rail',
                'color': '#7c3aed',
                'from_station': mmts_start['name'],
                'to_station': mmts_end['name'],
                'coords': [[mmts_start['lat'], mmts_start['lng']], [mmts_end['lat'], mmts_end['lng']]],
            }],
            'polyline': [
                [start_lat, start_lng],
                [mmts_start['lat'], mmts_start['lng']],
                [mmts_end['lat'], mmts_end['lng']],
                [end_lat, end_lng],
            ],
            'steps': [
                f"Take Auto / Walk ({round(mmts_start_dist/1000, 1)} km) to {mmts_start['name']}",
                f"Board MMTS Local Train towards {mmts_end['name']}",
                f"Alight at {mmts_end['name']} and take Auto / Walk ({round(mmts_end_dist/1000, 1)} km) to Destination",
            ],
            'station_hazards': mmts_hazards,
        })

    return {
        'direct_distance_km': round(direct_dist_km, 1),
        'options': options,
    }
