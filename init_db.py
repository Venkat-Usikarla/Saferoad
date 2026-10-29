"""
init_db.py — Database initialisation and sample-data seeder for SafeRoad.
Populates Hyderabad-centric road hazards, status history, and community reviews.

Run once or whenever you want to reset sample data:
    python init_db.py
"""

from datetime import datetime, timedelta

from app import app, calculate_priority
from zones import detect_zone
from models import (
    Confirmation,
    Report,
    StatusHistory,
    Petition,
    PetitionSignature,
    db,
)

# ---------------------------------------------------------------------------
# Hyderabad-Centric Sample Reports
# ---------------------------------------------------------------------------
SAMPLE_REPORTS = [
    {
        'category':        'pothole',
        'location_name':   'Cyber Towers Junction, Hitec City, Hyderabad',
        'lat':             17.4504,
        'lng':             78.3808,
        'description':     (
            'Deep cluster of potholes right at the Cyber Towers flyover entrance ramp. '
            'During peak hours, sudden swerving by IT commuters on two-wheelers creates '
            'severe bottlenecks and near-accidents daily.'
        ),
        'severity':        5,
        'status':          'Action in Progress',
        'submitter_name':  'Venkat Reddy',
        'submitter_email': 'venkat.reddy@example.com',
        'days_ago':        8,
        'resolution_note': 'GHMC Serilingampally circle maintenance crew deployed; cold-mix tar patching in progress.',
        'reviews': [
            {
                'name': 'Karthik Rao (TCS Commuter)',
                'email': 'karthik.rao@example.com',
                'comment': 'I commute here everyday on my bike. Almost lost balance yesterday morning. Glad GHMC is finally looking into it.',
                'hours_after': 6,
            },
            {
                'name': 'Divya Teja',
                'email': 'divya.teja@example.com',
                'comment': 'Traffic crawls from Mindspace to Cyber Towers purely because of this crater in the right lane.',
                'hours_after': 14,
            },
        ],
    },
    {
        'category':        'waterlogging',
        'location_name':   'Ayyappa Society 100 Feet Road, Madhapur, Hyderabad',
        'lat':             17.4475,
        'lng':             78.3915,
        'description':     (
            'Severe waterlogging opposite Meridian School stretch. Even with moderate showers, '
            'knee-deep water accumulates for 300 metres because roadside storm-water inlets '
            'are clogged with construction silt.'
        ),
        'severity':        4,
        'status':          'Under Review',
        'submitter_name':  'Sravani Krishna',
        'submitter_email': 'sravani.k@example.com',
        'days_ago':        4,
        'resolution_note': None,
        'reviews': [
            {
                'name': 'Mahesh Babu V.',
                'email': 'mahesh.v@example.com',
                'comment': 'Water was waist-deep during last Thursday rain! Autos got stalled and pedestrians had no footpath to walk on.',
                'hours_after': 5,
            },
        ],
    },
    {
        'category':        'unsafe_intersection',
        'location_name':   'Bio-Diversity Junction, Gachibowli, Hyderabad',
        'lat':             17.4294,
        'lng':             78.3687,
        'description':     (
            'Chaotic merge between the Old Mumbai Highway traffic and the Bio-Diversity flyover '
            'exit. Signal timings are unsynchronised and vehicles cross from the slip lane '
            'without warning, creating extreme collision risk.'
        ),
        'severity':        5,
        'status':          'Under Review',
        'submitter_name':  'Aditya Vardhan',
        'submitter_email': 'aditya.v@example.com',
        'days_ago':        6,
        'resolution_note': None,
        'reviews': [
            {
                'name': 'Rohit Sharma (Cyberabad Traffic Volunteer)',
                'email': 'rohit.ctv@example.com',
                'comment': 'Observed 3 near-misses in just 30 minutes during evening rush hour. Need rumble strips and clearer lane dividers immediately.',
                'hours_after': 8,
            },
            {
                'name': 'Sneha Nair',
                'email': 'sneha.n@example.com',
                'comment': 'Taking a right turn towards Meenakshi Tech Park is a nightmare here due to blind spots.',
                'hours_after': 18,
            },
        ],
    },
    {
        'category':        'damaged_surface',
        'location_name':   'Road No. 12, Banjara Hills (near Care Hospital), Hyderabad',
        'lat':             17.4156,
        'lng':             78.4358,
        'description':     (
            'Pipeline trench dug up for underground utility work has been left unpaved with '
            'loose gravel and sunken asphalt over a 200m stretch. Ambulances approaching the hospital '
            'experience harsh vibrations.'
        ),
        'severity':        4,
        'status':          'Action in Progress',
        'submitter_name':  'Dr. Pradeep Chandran',
        'submitter_email': 'dr.pradeep@example.com',
        'days_ago':        10,
        'resolution_note': 'Water Board and GHMC coordinated; asphalt re-laying work scheduled for night shift.',
        'reviews': [
            {
                'name': 'Fareed Ahmed',
                'email': 'fareed.a@example.com',
                'comment': 'Very critical since hospital ambulances use this road round the clock. Glad it is being surfaced.',
                'hours_after': 12,
            },
        ],
    },
    {
        'category':        'missing_crossing',
        'location_name':   'Jubilee Hills Checkpost (Road No. 36), Hyderabad',
        'lat':             17.4319,
        'lng':             78.4073,
        'description':     (
            'No pedestrian zebra crossing or pelican signal between Jubilee Hills Checkpost Metro '
            'and Peddamma Temple road. High-speed traffic on this 6-lane road forces metro commuters '
            'to sprint across the road dangerously.'
        ),
        'severity':        4,
        'status':          'Pending Review',
        'submitter_name':  'Deepika Rao',
        'submitter_email': 'deepika.rao@example.com',
        'days_ago':        2,
        'resolution_note': None,
        'reviews': [
            {
                'name': 'Sanjay Gupta',
                'email': 'sanjay.g@example.com',
                'comment': 'Saw an elderly gentleman unable to cross for over 15 minutes yesterday. A designated crossing with a signal is urgently needed.',
                'hours_after': 10,
            },
        ],
    },
    {
        'category':        'poor_lighting',
        'location_name':   'PVNR Expressway Pillar 45, Mehdipatnam, Hyderabad',
        'lat':             17.3917,
        'lng':             78.4398,
        'description':     (
            'Under-deck streetlights beneath the PVNR Expressway have been non-functional for '
            'over three weeks. Dense pedestrian footfall near Rythu Bazar combined with pitch-black '
            'blind spots has led to accidents and purse-snatching incidents.'
        ),
        'severity':        4,
        'status':          'Pending Review',
        'submitter_name':  'Mohammad Zeeshan',
        'submitter_email': 'm.zeeshan@example.com',
        'days_ago':        3,
        'resolution_note': None,
        'reviews': [
            {
                'name': 'Mirza Baig',
                'email': 'mirza.baig@example.com',
                'comment': 'Completely pitch black past 8 PM. Bus commuters crossing towards Rythu Bazar are totally invisible to oncoming vehicles.',
                'hours_after': 6,
            },
        ],
    },
    {
        'category':        'damaged_sign',
        'location_name':   'Secunderabad Railway Station Circle near Clock Tower, Hyderabad',
        'lat':             17.4399,
        'lng':             78.4983,
        'description':     (
            'Major overhead directional overhead signboard indicating Paradise / Tank Bund has broken '
            'brackets and is dangling at a hazardous angle directly over traffic lanes.'
        ),
        'severity':        3,
        'status':          'Resolved',
        'submitter_name':  'Pooja Nair',
        'submitter_email': 'pooja.nair@example.com',
        'days_ago':        15,
        'resolution_note': 'Traffic engineering wing removed the dangling signboard and installed a fresh reflectorized sign on 14 Oct.',
        'reviews': [
            {
                'name': 'G. Srinivas',
                'email': 'srinivas.g@example.com',
                'comment': 'Saw the repair team take it down safely. Fast resolution, good job SafeRoad team!',
                'hours_after': 18,
            },
        ],
    },
    {
        'category':        'damaged_surface',
        'location_name':   'Gulzar Houz to Charminar Stretch, Old City, Hyderabad',
        'lat':             17.3616,
        'lng':             78.4747,
        'description':     (
            'Heritage cobblestone and asphalt boundary along the Charminar pedestrianization buffer '
            'has collapsed, exposing stone slabs and deep ruts. Two-wheelers frequently skid here.'
        ),
        'severity':        3,
        'status':          'Pending Review',
        'submitter_name':  'Syed Khaja',
        'submitter_email': 'syed.khaja@example.com',
        'days_ago':        1,
        'resolution_note': None,
        'reviews': [
            {
                'name': 'Ibrahim Qureshi',
                'email': 'ibrahim.q@example.com',
                'comment': 'Tourists and elderly shoppers regularly trip on these broken slabs. Needs quick cobblestone realignment.',
                'hours_after': 4,
            },
        ],
    },
    {
        'category':        'pothole',
        'location_name':   'Kukatpally Y-Junction (near Forum Nexus Mall), Hyderabad',
        'lat':             17.4938,
        'lng':             78.3986,
        'description':     (
            'Extremely wide crater on the left-most lane approaching the Y-junction flyover. '
            'Water gathers inside making it look like a puddle; vehicles hitting it at 40 km/h suffer '
            'suspension and tyre blowouts.'
        ),
        'severity':        5,
        'status':          'Action in Progress',
        'submitter_name':  'T. Balakrishna',
        'submitter_email': 'bala.t@example.com',
        'days_ago':        7,
        'resolution_note': 'GHMC Kukatpally division inspected; premix filling ongoing tonight.',
        'reviews': [
            {
                'name': 'Harish Varma',
                'email': 'harish.v@example.com',
                'comment': 'My car wheel rim bent because of this exact pothole on Monday evening. Very dangerous!',
                'hours_after': 8,
            },
            {
                'name': 'Sunita Chary',
                'email': 'sunita.c@example.com',
                'comment': 'Confirmed! Heavy RTC buses also tilt dangerously when tyres dip into it.',
                'hours_after': 22,
            },
        ],
    },
    {
        'category':        'waterlogging',
        'location_name':   'Prakash Nagar Metro Station, Begumpet Main Road, Hyderabad',
        'lat':             17.4442,
        'lng':             78.4682,
        'description':     (
            'Heavy waterlogging beneath the Begumpet metro flyover. Runoff from the Rasoolpura slope '
            'converges here, shutting down the left 2 lanes and causing 3 km tailbacks towards Punjagutta.'
        ),
        'severity':        4,
        'status':          'Under Review',
        'submitter_name':  'Manish Kumar',
        'submitter_email': 'manish.k@example.com',
        'days_ago':        5,
        'resolution_note': None,
        'reviews': [
            {
                'name': 'Anuradha Deshpande',
                'email': 'anuradha.d@example.com',
                'comment': 'Happens every monsoon without fail. Drainage desilting work must be executed prior to heavy rains.',
                'hours_after': 12,
            },
        ],
    },
    {
        'category':        'missing_crossing',
        'location_name':   'Dilsukhnagar Main Road near Metro Pillar 1520, Hyderabad',
        'lat':             17.3688,
        'lng':             78.5247,
        'description':     (
            'Massive pedestrian density near commercial complex and coaching centres, but '
            'zebra crossing markings have completely faded away. Auto-rickshaws block pedestrian vision.'
        ),
        'severity':        3,
        'status':          'Pending Review',
        'submitter_name':  'N. Praveen Kumar',
        'submitter_email': 'praveen.n@example.com',
        'days_ago':        2,
        'resolution_note': None,
        'reviews': [
            {
                'name': 'Swathi K.',
                'email': 'swathi.k@example.com',
                'comment': 'College students have to dodge speeding RTC buses here every morning. Repainting zebra markings is a must.',
                'hours_after': 7,
            },
        ],
    },
    {
        'category':        'other',
        'location_name':   'Botanical Garden Road, Kondapur, Hyderabad',
        'lat':             17.4589,
        'lng':             78.3642,
        'description':     (
            'Broken metal drainage grate left protruding 6 inches above road surface. '
            'Two bike riders were injured when front wheels snagged on the exposed sharp edges.'
        ),
        'severity':        5,
        'status':          'Resolved',
        'submitter_name':  'Goutham Raj',
        'submitter_email': 'goutham.raj@example.com',
        'days_ago':        20,
        'resolution_note': 'Replaced broken grate with heavy-duty ductile iron grating on 12 Oct 2026.',
        'reviews': [
            {
                'name': 'Nikhil Reddy',
                'email': 'nikhil.r@example.com',
                'comment': 'Saw the repair done. The new cast iron grill is completely flush with the road now. Thank you!',
                'hours_after': 24,
            },
        ],
    },
    {
        'category':        'pothole',
        'location_name':   'Yakutpura Station Road, Old City, Hyderabad',
        'lat':             17.3592,
        'lng':             78.4984,
        'description':     (
            'Deep, hazardous pothole and sunken storm-drain slab directly outside Yakutpura '
            'railway station entrance. Two-wheelers and auto-rickshaws continually skid during rush hours.'
        ),
        'severity':        4,
        'status':          'Action in Progress',
        'submitter_name':  'Mirza Hussain',
        'submitter_email': 'mirza.h@example.com',
        'days_ago':        3,
        'resolution_note': 'GHMC Charminar zone engineers have cordoned off the area; concrete patching underway.',
        'reviews': [
            {
                'name': 'Mohammed Aslam (Daily Local Train Commuter)',
                'email': 'aslam.m@example.com',
                'comment': 'Commuters walking out of the station in the dark trip over this every single night. Very dangerous!',
                'hours_after': 5,
            },
            {
                'name': 'Farooq Ali',
                'email': 'farooq.ali@example.com',
                'comment': 'Autos avoid the left lane completely, causing sudden jams on this narrow road.',
                'hours_after': 12,
            },
        ],
    },
    {
        'category':        'damaged_surface',
        'location_name':   'Ameerpet Metro Junction (opposite Maitrivanam), Hyderabad',
        'lat':             17.4375,
        'lng':             78.4482,
        'description':     (
            'Road surface is severely eroded and uneven with sunken utility trenches opposite '
            'Maitrivanam coaching hub. Loose blue metal gravel causes bikes to slide during braking.'
        ),
        'severity':        4,
        'status':          'Under Review',
        'submitter_name':  'Sunil Varma',
        'submitter_email': 'sunil.v@example.com',
        'days_ago':        5,
        'resolution_note': None,
        'reviews': [
            {
                'name': 'Ramesh Kumar (Faculty)',
                'email': 'ramesh.k@example.com',
                'comment': 'Thousands of students walk through here. Loose stones fly when RTC buses brake hard.',
                'hours_after': 6,
            },
        ],
    },
    {
        'category':        'waterlogging',
        'location_name':   'Tolichowki Flyover Underpass (near Galaxy Theatre), Hyderabad',
        'lat':             17.4011,
        'lng':             78.4125,
        'description':     (
            'Under-flyover junction fills with 2 feet of stagnant water even after brief rain. '
            'Vehicles heading towards Gachibowli from Mehdipatnam get trapped in 2km queues.'
        ),
        'severity':        5,
        'status':          'Pending Review',
        'submitter_name':  'Salman Khan',
        'submitter_email': 'salman.k@example.com',
        'days_ago':        2,
        'resolution_note': None,
        'reviews': [
            {
                'name': 'Azharuddin Quadri',
                'email': 'azhar.q@example.com',
                'comment': 'The stormwater drain line below the flyover seems completely choked with plastic garbage.',
                'hours_after': 4,
            },
        ],
    },
    {
        'category':        'unsafe_intersection',
        'location_name':   'LB Nagar Ring Road Junction (near Kamineni Hospital), Hyderabad',
        'lat':             17.3457,
        'lng':             78.5522,
        'description':     (
            'Heavy inter-city bus and truck traffic merges at high speed with local vehicles. '
            'Traffic signal countdown timers are broken and lane demarcation is completely missing.'
        ),
        'severity':        5,
        'status':          'Action in Progress',
        'submitter_name':  'P. Venkateshwarlu',
        'submitter_email': 'p.venkat@example.com',
        'days_ago':        7,
        'resolution_note': 'Rachakonda Traffic Police installing new digital countdown signals and high-visibility bollards.',
        'reviews': [
            {
                'name': 'Vijay Bhaskar',
                'email': 'vijay.b@example.com',
                'comment': 'Pedestrians crossing towards the hospital have no pedestrian refuge island. Very critical spot.',
                'hours_after': 9,
            },
        ],
    },
    {
        'category':        'missing_crossing',
        'location_name':   'Panjagutta Central Mall / Metro Station Stretch, Hyderabad',
        'lat':             17.4265,
        'lng':             78.4516,
        'description':     (
            'Pedestrians exiting Panjagutta Metro station have no designated crossing or pelican light '
            'to cross the busy 6-lane road towards the commercial complex.'
        ),
        'severity':        4,
        'status':          'Pending Review',
        'submitter_name':  'Ananya Joshi',
        'submitter_email': 'ananya.j@example.com',
        'days_ago':        1,
        'resolution_note': None,
        'reviews': [
            {
                'name': 'M. Sandeep',
                'email': 'm.sandeep@example.com',
                'comment': 'People are forced to jump over the central concrete divider. Need a zebra crossing with button-operated signal.',
                'hours_after': 3,
            },
        ],
    },
    {
        'category':        'poor_lighting',
        'location_name':   'Moosapet Junction towards Balanagar Industrial Area, Hyderabad',
        'lat':             17.4716,
        'lng':             78.4287,
        'description':     (
            'Series of 8 consecutive streetlights on the central median are completely dark at night. '
            'Heavy trucks turning towards Balanagar cannot see two-wheelers in blind spots.'
        ),
        'severity':        4,
        'status':          'Resolved',
        'submitter_name':  'K. Chandrasekhar',
        'submitter_email': 'k.chandra@example.com',
        'days_ago':        25,
        'resolution_note': 'TSSPDCL replaced underground cable fault and restored all 8 LED median luminaires on 8 Oct 2026.',
        'reviews': [
            {
                'name': 'Satish Reddy',
                'email': 'satish.r@example.com',
                'comment': 'Median lights are working now! Commuting back home past 10 PM is much safer.',
                'hours_after': 26,
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Status Transitions for Seeding Timeline
# ---------------------------------------------------------------------------
STATUS_TRANSITIONS = {
    'Under Review': [
        (None,            'Pending Review',  'Report submitted by citizen.'),
        ('Pending Review', 'Under Review',   'Report reviewed and accepted by Traffic & GHMC cell.'),
    ],
    'Action in Progress': [
        (None,               'Pending Review',    'Report submitted by citizen.'),
        ('Pending Review',   'Under Review',      'Report reviewed and accepted by Traffic & GHMC cell.'),
        ('Under Review',     'Action in Progress', 'Work order issued and field engineering crew dispatched.'),
    ],
    'Resolved': [
        (None,               'Pending Review',    'Report submitted by citizen.'),
        ('Pending Review',   'Under Review',      'Report reviewed and accepted by Traffic & GHMC cell.'),
        ('Under Review',     'Action in Progress', 'Work order issued and field engineering crew dispatched.'),
        ('Action in Progress', 'Resolved',         'Hazard inspected, repair certified and road safety verified.'),
    ],
    'Rejected': [
        (None,            'Pending Review', 'Report submitted by citizen.'),
        ('Pending Review', 'Rejected',      'Report rejected — outside jurisdiction or duplicate.'),
    ],
    'Pending Review': [
        (None, 'Pending Review', 'Report submitted by citizen.'),
    ],
}

SAMPLE_PETITIONS = [
    {
        'petition_id': 'PET-2026-001',
        'title': 'Urgent Re-carpeting & Pothole Repair at Cyber Towers Junction Flyover Ramp',
        'category': 'pothole',
        'location_name': 'Cyber Towers Junction, Hitec City, Hyderabad',
        'lat': 17.4504,
        'lng': 78.3808,
        'zone_id': 'serilingampally',
        'zone_name': 'Serilingampally Zone (West)',
        'target_authority': 'GHMC Serilingampally Circle & Cyberabad Traffic Police',
        'target_signatures': 50,
        'creator_name': 'Venkat Reddy (IT Corridor Commuter)',
        'creator_email': 'venkat.reddy@example.com',
        'creator_phone': '+91 98490 12345',
        'status': 'Active',
        'story': (
            'Over 40,000 two-wheeler commuters use the Cyber Towers flyover ramp daily. '
            'Multiple deep craters right at the merge point have caused at least 4 known bike skids '
            'and severe suspension damage this month. Temporary mud fillings wash away in 24 hours. '
            'We demand permanent hot-mix asphalt resurfacing and high-friction anti-skid overlay before '
            'a fatal accident occurs.'
        ),
        'signatures': [
            {'name': 'Karthik Rao', 'email': 'karthik.rao@example.com', 'locality': 'Madhapur', 'comment': 'I ride my scooter here daily. Almost fell under an RTC bus last Tuesday!'},
            {'name': 'Sravanthi V.', 'email': 'sravanthi.v@example.com', 'locality': 'Kondapur', 'comment': 'Traffic backs up till Mindspace purely because of this pothole choke point.'},
            {'name': 'Dr. Pradeep Chandran', 'email': 'dr.pradeep@example.com', 'locality': 'Gachibowli', 'comment': 'Emergency vehicles get stuck during peak evening hours.'},
            {'name': 'Fareed Ahmed', 'email': 'fareed.a@example.com', 'locality': 'Hitec City', 'comment': 'Fully support this! GHMC must deploy heavy-duty road machinery immediately.'},
            {'name': 'Divya Teja', 'email': 'divya.teja@example.com', 'locality': 'Chandanagar', 'comment': 'Signed! Please share this with all IT employees in Hitec City.'},
        ]
    },
    {
        'petition_id': 'PET-2026-002',
        'title': 'Install Pelican Crossing & Pedestrian Signal at Jubilee Hills Checkpost Metro',
        'category': 'missing_crossing',
        'location_name': 'Jubilee Hills Checkpost (Road No. 36), Hyderabad',
        'lat': 17.4319,
        'lng': 78.4073,
        'zone_id': 'khairatabad',
        'zone_name': 'Khairatabad Zone (Central)',
        'target_authority': 'Hyderabad City Police Traffic Engineering Cell & GHMC Central',
        'target_signatures': 50,
        'creator_name': 'Deepika Rao',
        'creator_email': 'deepika.rao@example.com',
        'creator_phone': '+91 97012 34567',
        'status': 'Active',
        'story': (
            'Pedestrians exiting the Jubilee Hills Checkpost Metro station have no designated pedestrian '
            'crossing or pelican light to reach Road No. 36 commercial establishments. Elderly shoppers and '
            'college students are forced to jump median dividers and sprint through speeding vehicular traffic. '
            'We demand immediate installation of an automated push-button pelican crossing signal and high-visibility zebra markings.'
        ),
        'signatures': [
            {'name': 'Sanjay Gupta', 'email': 'sanjay.g@example.com', 'locality': 'Jubilee Hills', 'comment': 'My elderly mother cannot cross this road safely. A signal is urgently needed.'},
            {'name': 'Ananya Joshi', 'email': 'ananya.j@example.com', 'locality': 'Banjara Hills', 'comment': 'Speeding cars do not slow down at all near the metro exit.'},
            {'name': 'N. Praveen Kumar', 'email': 'praveen.n@example.com', 'locality': 'Somajiguda', 'comment': 'Signed. Hyderabad needs to prioritize pedestrian safety over just car speed.'},
        ]
    },
    {
        'petition_id': 'PET-2026-003',
        'title': 'Emergency Stormwater Pipeline Upgrade to End Chronic Flooding at Ayyappa Society',
        'category': 'waterlogging',
        'location_name': 'Ayyappa Society 100 Feet Road, Madhapur, Hyderabad',
        'lat': 17.4475,
        'lng': 78.3915,
        'zone_id': 'serilingampally',
        'zone_name': 'Serilingampally Zone (West)',
        'target_authority': 'GHMC Stormwater Drainage Wing & Circle Engineer',
        'target_signatures': 30,
        'creator_name': 'Sravani Krishna',
        'creator_email': 'sravani.k@example.com',
        'creator_phone': '+91 99887 66554',
        'status': 'Milestone Reached',
        'story': (
            'Every monsoon shower turns Ayyappa Society 100 Feet Road into a 2-foot deep stagnant canal '
            'outside Meridian School. School buses get stalled, shop basements get flooded with sewage silt, '
            'and electric transformer boxes get submerged creating electrocution risks. '
            'We petition for immediate widening of box drains and desilting of downstream connecting culverts.'
        ),
        'signatures': [
            {'name': 'Mahesh Babu V.', 'email': 'mahesh.v@example.com', 'locality': 'Ayyappa Society', 'comment': 'Water entered my apartment ground floor twice last season!'},
            {'name': 'Sunita Chary', 'email': 'sunita.c@example.com', 'locality': 'Madhapur', 'comment': 'Children going to school have to wade through dirty stagnant water.'},
            {'name': 'Harish Varma', 'email': 'harish.v@example.com', 'locality': 'Kavuri Hills', 'comment': 'Drainage inlet pipes are choked with construction debris. Must be cleaned.'},
        ]
    }
]

# ---------------------------------------------------------------------------
# Seeder function
# ---------------------------------------------------------------------------

def seed_database() -> None:
    """Drop all existing data and insert fresh Hyderabad-centric records with reviews and petitions."""
    PetitionSignature.query.delete()
    Petition.query.delete()
    StatusHistory.query.delete()
    Confirmation.query.delete()
    Report.query.delete()
    db.session.commit()

    year = datetime.now().year

    for idx, data in enumerate(SAMPLE_REPORTS, start=1):
        days_ago = data.get('days_ago', 1)
        created_at = datetime.now() - timedelta(days=days_ago)
        report_id = f'SR-{year}-{idx:03d}'

        reviews = data.get('reviews', [])
        conf_count = len(reviews)
        score, level = calculate_priority(data['severity'], data['category'], conf_count)

        zone_info = detect_zone(lat=data.get('lat'), lng=data.get('lng'), location_name=data['location_name'])

        report = Report(
            report_id=report_id,
            category=data['category'],
            location_name=data['location_name'],
            lat=data.get('lat'),
            lng=data.get('lng'),
            zone_id=zone_info['id'],
            zone_name=zone_info['name'],
            assigned_officer=f"{zone_info['officer_name']} ({zone_info['officer_title']})",
            description=data['description'],
            severity=data['severity'],
            image_path=None,
            status=data['status'],
            priority_score=score,
            priority_level=level,
            submitter_name=data['submitter_name'],
            submitter_email=data['submitter_email'],
            resolution_note=data.get('resolution_note'),
            created_at=created_at,
            updated_at=created_at,
        )
        db.session.add(report)
        db.session.flush()

        # Add Status History
        transitions = STATUS_TRANSITIONS.get(data['status'], STATUS_TRANSITIONS['Pending Review'])
        for offset_days, (old_s, new_s, note) in enumerate(transitions):
            history = StatusHistory(
                report_id=report.id,
                old_status=old_s,
                new_status=new_s,
                note=note,
                changed_by='System' if old_s is None else 'GHMC Admin',
                changed_at=created_at + timedelta(days=offset_days + 1),
            )
            db.session.add(history)

        # Add Community Reviews / Confirmations
        for r_info in reviews:
            confirmation = Confirmation(
                report_id=report.id,
                confirmer_name=r_info['name'],
                confirmer_email=r_info['email'],
                comment=r_info['comment'],
                confirmed_at=created_at + timedelta(hours=r_info.get('hours_after', 4)),
            )
            db.session.add(confirmation)

    # Seed Community Petitions & Signatures
    for p_data in SAMPLE_PETITIONS:
        pet = Petition(
            petition_id=p_data['petition_id'],
            title=p_data['title'],
            story=p_data['story'],
            category=p_data['category'],
            location_name=p_data['location_name'],
            lat=p_data['lat'],
            lng=p_data['lng'],
            zone_id=p_data['zone_id'],
            zone_name=p_data['zone_name'],
            target_authority=p_data['target_authority'],
            target_signatures=p_data['target_signatures'],
            creator_name=p_data['creator_name'],
            creator_email=p_data['creator_email'],
            creator_phone=p_data.get('creator_phone'),
            status=p_data.get('status', 'Active'),
        )
        db.session.add(pet)
        db.session.flush()

        for s_data in p_data.get('signatures', []):
            sig = PetitionSignature(
                petition_id=pet.id,
                signer_name=s_data['name'],
                signer_email=s_data['email'],
                locality=s_data.get('locality', 'Hyderabad Resident'),
                comment=s_data.get('comment'),
                signed_at=datetime.utcnow() - timedelta(hours=12),
            )
            db.session.add(sig)

    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        # Drop and recreate tables to ensure updated schema with review comments
        db.drop_all()
        db.create_all()
        print("[OK] Tables dropped & recreated with latest schema.")
        seed_database()
        print("[OK] Database populated with Hyderabad places and citizen reviews.")
        print()
        print("  Admin credentials:")
        print(f"    Username : {app.config['ADMIN_USERNAME']}")
        print(f"    Password : {app.config['ADMIN_PASSWORD']}")
        print()
        print("  Map Center: Hyderabad (17.3850 N, 78.4867 E)")
        print("  Admin Logout available in Navbar and Dashboard.")
