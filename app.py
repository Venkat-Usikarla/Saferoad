"""
app.py — SafeRoad Flask application entry-point.

Public routes
-------------
  GET  /                         Landing / index page
  GET  /report                   Hazard report submission form
  POST /report                   Submit a new hazard report (JSON response)
  GET  /map                      Interactive map page
  GET  /api/reports              JSON list of reports (filterable)
  GET  /api/reports/<report_id>  Single report JSON detail
  GET  /my-reports               Reporter's own report search page
  GET  /api/track/<report_id>    Report detail + full status history (JSON)
  POST /api/confirm/<report_id>  Add a community confirmation to a report

Admin routes (session-protected)
---------------------------------
  GET/POST /admin/login
  GET      /admin/logout
  GET      /admin/               Dashboard with aggregate stats
  GET      /admin/reports        All reports (search / filter / sort)
  GET      /admin/reports/<id>   Single report detail view
  POST     /admin/reports/<id>/update  Update status / priority / note
"""

import math
import os
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from config import Config
from models import (
    HAZARD_CATEGORIES,
    STATUS_CHOICES,
    PETITION_STATUS_CHOICES,
    VALID_CATEGORIES,
    Confirmation,
    Report,
    StatusHistory,
    Petition,
    PetitionSignature,
    db,
)
from mailer import (
    send_report_confirmation,
    send_status_update_notification,
    send_petition_signature_confirmation,
    send_petition_creation_confirmation,
)
from profanity_filter import contains_profanity, sanitize_or_validate
from zones import detect_zone, HYDERABAD_ZONES, get_all_zones, get_zone_by_id
from admin_auth import authenticate_admin, get_all_credentials_for_super_admin, ADMIN_ACCOUNTS
from route_safety import SAMPLE_HYDERABAD_ROUTES, evaluate_route_safety

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def create_app(config_object: object = Config) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config_object)

    # Ensure the upload directory exists before the first request
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialise extensions
    db.init_app(app)

    # Register all routes
    _register_public_routes(app)
    _register_api_routes(app)
    _register_admin_routes(app)

    return app


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def allowed_file(filename: str) -> bool:
    """Return True if *filename* has an allowed extension."""
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower()
        in Config.ALLOWED_EXTENSIONS
    )


def calculate_priority(severity: int, category: str, confirmation_count: int = 0):
    """
    Compute a numeric priority score and a Low/Medium/High label.

    Scoring rules
    -------------
    • Base:            severity × 20
    • Dangerous cats:  +30 for pothole / unsafe_intersection
    • Extreme sev:     +20 when severity == 5
    • Community boost: +10 per confirmation, capped at +30
    """
    score = severity * 20
    if category in ('pothole', 'unsafe_intersection'):
        score += 30
    if severity == 5:
        score += 20
    score += min(confirmation_count * 10, 30)

    if score >= 70:
        level = 'High'
    elif score >= 40:
        level = 'Medium'
    else:
        level = 'Low'

    return score, level


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Return the great-circle distance in **metres** between two GPS points.

    Uses the Haversine formula with Earth radius = 6 371 000 m.
    """
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def generate_report_id(year: int) -> str:
    """
    Generate the next sequential SafeRoad report ID for *year*.

    Format: ``SR-{year}-{seq:03d}`` where *seq* is 1-based and derived
    from the total number of existing reports for the given year.
    """
    prefix = f'SR-{year}-'
    count = Report.query.filter(Report.report_id.like(f'{prefix}%')).count()
    return f'{prefix}{count + 1:03d}'


def generate_petition_id(year: int) -> str:
    """
    Generate the next sequential community petition ID for *year*.
    Format: ``PET-{year}-{seq:03d}``
    """
    prefix = f'PET-{year}-'
    count = Petition.query.filter(Petition.petition_id.like(f'{prefix}%')).count()
    return f'{prefix}{count + 1:03d}'


def save_uploaded_image(file_storage) -> str | None:
    """
    Persist an uploaded image to the configured UPLOAD_FOLDER.

    Returns the relative path suitable for storing in the DB
    (e.g. ``uploads/abc123_photo.jpg``), or *None* if no valid file
    was provided.
    """
    if not file_storage or file_storage.filename == '':
        return None
    if not allowed_file(file_storage.filename):
        return None

    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    safe_name = f'{uuid.uuid4().hex}_{secure_filename(file_storage.filename)}'
    # Trim to avoid excessively long filenames
    if len(safe_name) > 200:
        safe_name = f'{uuid.uuid4().hex}.{ext}'

    dest = os.path.join(Config.UPLOAD_FOLDER, safe_name)
    file_storage.save(dest)
    # Return the path relative to the static/ directory
    return f'uploads/{safe_name}'


# ---------------------------------------------------------------------------
# Admin auth decorator
# ---------------------------------------------------------------------------


def login_required(f):
    """Decorator that redirects unauthenticated requests to /admin/login."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Public route registration
# ---------------------------------------------------------------------------


def _register_public_routes(app: Flask) -> None:

    @app.route('/')
    def index():
        """Landing page with summary statistics."""
        total = Report.query.count()
        resolved = Report.query.filter_by(status='Resolved').count()
        active = Report.query.filter(
            Report.status.notin_(['Resolved', 'Rejected', 'Duplicate'])
        ).count()
        pending = Report.query.filter_by(status='Pending Review').count()

        stats = {
            'total_reports': total,
            'resolved': resolved,
            'active': active,
            'pending': pending,
        }

        # Curate showcase reports for homepage: highlight resolved road repairs
        # alongside high-impact active hazards (avoiding junk/test flooding).
        resolved_reports = (
            Report.query.filter_by(status='Resolved')
            .order_by(Report.updated_at.desc(), Report.created_at.desc())
            .limit(3)
            .all()
        )
        active_reports = (
            Report.query.filter(Report.status.in_(['Action in Progress', 'Under Review', 'Pending Review']))
            .order_by(Report.priority_score.desc(), Report.created_at.desc())
            .limit(6 - len(resolved_reports))
            .all()
        )
        recent_reports = []
        for r in active_reports:
            if r not in recent_reports:
                recent_reports.append(r)
        for r in resolved_reports:
            if r not in recent_reports:
                recent_reports.append(r)

        if not recent_reports:
            recent_reports = (
                Report.query.order_by(Report.created_at.desc()).limit(6).all()
            )

        return render_template('index.html', stats=stats, recent_reports=recent_reports)

    @app.route('/report', methods=['GET'])
    def report_hazard():
        """Render the public hazard-report submission form."""
        return render_template(
            'report.html',
            hazard_categories=HAZARD_CATEGORIES,
        )

    @app.route('/report', methods=['POST'])
    def submit_report():
        """
        Process a hazard report submission.

        Steps
        -----
        1. Validate required fields.
        2. Save any uploaded image.
        3. Check for nearby duplicate reports (same category, within 500 m).
        4. Generate a human-readable report ID.
        5. Calculate priority score and level.
        6. Persist the report and its initial status-history entry.
        7. Return a JSON response.
        """
        # ---- 1. Field validation ------------------------------------------
        required = {
            'category':        request.form.get('category', '').strip(),
            'location_name':   request.form.get('location_name', '').strip(),
            'description':     request.form.get('description', '').strip(),
            'submitter_name':  request.form.get('submitter_name', '').strip(),
            'submitter_email': request.form.get('submitter_email', '').strip(),
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            return jsonify(success=False, error=f'Missing fields: {", ".join(missing)}'), 400

        category = required['category']
        if category not in VALID_CATEGORIES:
            return jsonify(success=False, error='Invalid category.'), 400

        try:
            severity = int(request.form.get('severity', 0))
            if not (1 <= severity <= 5):
                raise ValueError
        except (TypeError, ValueError):
            return jsonify(success=False, error='Severity must be an integer between 1 and 5.'), 400

        if len(required['description']) < 20:
            return jsonify(success=False, error='Description must be at least 20 characters.'), 400

        # ---- Profanity / Inappropriate Language Filter (Smart Word-Boundary)
        for field_text, field_label in [
            (required['description'], 'Description'),
            (required['location_name'], 'Location name'),
            (required['submitter_name'], 'Submitter name'),
        ]:
            is_clean, err_msg = sanitize_or_validate(field_text, field_label)
            if not is_clean:
                return jsonify(success=False, error=err_msg), 400

        # Parse optional GPS coordinates (accepts both lat/latitude and lng/longitude)
        lat = lng = None
        raw_lat = (request.form.get('lat') or request.form.get('latitude') or '').strip()
        raw_lng = (request.form.get('lng') or request.form.get('longitude') or '').strip()
        if raw_lat and raw_lng:
            try:
                lat = float(raw_lat)
                lng = float(raw_lng)
            except ValueError:
                return jsonify(success=False, error='lat/lng must be valid numbers.'), 400

        # ---- 2. Image upload ------------------------------------------------
        image_path = None
        if 'image' in request.files:
            image_path = save_uploaded_image(request.files['image'])
        elif 'photo' in request.files:
            image_path = save_uploaded_image(request.files['photo'])

        # ---- 3. Duplicate detection -----------------------------------------
        duplicate_suggestions = []
        if lat is not None and lng is not None:
            candidates = Report.query.filter_by(category=category).filter(
                Report.lat.isnot(None), Report.lng.isnot(None)
            ).all()
            for cand in candidates:
                dist = haversine(lat, lng, cand.lat, cand.lng)
                if dist <= 500:
                    duplicate_suggestions.append({
                        'report_id': cand.report_id,
                        'location_name': cand.location_name,
                        'status': cand.status,
                        'distance_m': round(dist),
                    })

        # ---- 4. Auto-detect GHMC Municipal Zone & Assign Circle Officer ----
        explicit_zone_id = request.form.get('zone_id', '').strip()
        zone = None
        if explicit_zone_id:
            zone = get_zone_by_id(explicit_zone_id)
        if not zone:
            zone = detect_zone(lat=lat, lng=lng, location_name=required['location_name'])

        # ---- 5. Report ID ---------------------------------------------------
        year = datetime.utcnow().year
        report_id = generate_report_id(year)

        # ---- 6. Priority ----------------------------------------------------
        score, level = calculate_priority(severity, category, 0)

        # ---- 7. Persist report ----------------------------------------------
        report = Report(
            report_id=report_id,
            category=category,
            location_name=required['location_name'],
            lat=lat,
            lng=lng,
            zone_id=zone['id'],
            zone_name=zone['name'],
            assigned_officer=f"{zone['officer_name']} ({zone['officer_title']})",
            description=required['description'],
            severity=severity,
            image_path=image_path,
            status='Pending Review',
            priority_score=score,
            priority_level=level,
            submitter_name=required['submitter_name'],
            submitter_email=required['submitter_email'],
        )
        db.session.add(report)
        db.session.flush()  # Populate report.id before creating history

        initial_history = StatusHistory(
            report_id=report.id,
            old_status=None,
            new_status='Pending Review',
            note=f"Report submitted by citizen. Assigned to {zone['name']} ({zone['officer_name']}).",
            changed_by='System',
        )
        db.session.add(initial_history)
        db.session.commit()

        # Dispatch automated confirmation email (threaded)
        try:
            send_report_confirmation(report, base_url=request.host_url)
        except Exception:
            pass

        # ---- 8. Response ----------------------------------------------------
        return jsonify(
            success=True,
            report_id=report_id,
            category=category,
            category_label=dict(HAZARD_CATEGORIES).get(category, category),
            location_name=required['location_name'],
            priority_level=level,
            priority_score=score,
            zone_id=zone['id'],
            zone_name=zone['name'],
            assigned_officer=zone['officer_name'],
            officer_title=zone['officer_title'],
            office_address=zone['office_address'],
            duplicate_suggestions=duplicate_suggestions,
        ), 201

    @app.route('/map')
    def view_map():
        """Interactive map page (front-end fetches /api/reports for markers)."""
        return render_template(
            'map.html',
            hazard_categories=HAZARD_CATEGORIES,
            status_choices=STATUS_CHOICES,
        )

    @app.route('/my-reports')
    @app.route('/my_reports')
    @app.route('/track')
    @app.route('/track-report')
    def my_reports():
        """Search page for a reporter to look up their submissions."""
        return render_template('my_reports.html')

    # ------------------------------------------------------------------
    # DT Feature 1: SafeRoute — Route Safety Map & Corridor Hazard Assessment
    # ------------------------------------------------------------------

    @app.route('/routes')
    @app.route('/saferoute')
    @app.route('/route-safety')
    def route_safety_page():
        """
        Interactive road-safety route planner. Analyzes commute trajectories
        between starting and destination points in Hyderabad.
        """
        return render_template(
            'routes.html',
            sample_routes=SAMPLE_HYDERABAD_ROUTES,
            hazard_categories=HAZARD_CATEGORIES,
        )

    # ------------------------------------------------------------------
    # DT Feature 2: Community Petitions & Digital Signatures (Change.org-style)
    # ------------------------------------------------------------------

    @app.route('/petitions')
    def petitions_list():
        """Directory of public road safety petitions with live signature counts."""
        query = Petition.query

        search = (request.args.get('q') or request.args.get('search') or '').strip()
        if search:
            like = f'%{search}%'
            query = query.filter(
                Petition.title.ilike(like)
                | Petition.location_name.ilike(like)
                | Petition.story.ilike(like)
            )

        zone = request.args.get('zone', '').strip().lower()
        if zone and zone != 'all':
            query = query.filter_by(zone_id=zone)

        status = request.args.get('status', '').strip()
        if status and status != 'all':
            query = query.filter_by(status=status)

        petitions = query.order_by(Petition.created_at.desc()).all()
        return render_template(
            'petitions/index.html',
            petitions=petitions,
            all_zones=get_all_zones(),
            hazard_categories=HAZARD_CATEGORIES,
        )

    @app.route('/petitions/new', methods=['GET'])
    def new_petition():
        """Render the form to launch a new community road safety petition."""
        prefill = None
        linked_report_id = request.args.get('report_id', '').strip()
        if linked_report_id:
            rep = Report.query.filter_by(report_id=linked_report_id).first()
            if rep:
                prefill = {
                    'report_id': rep.report_id,
                    'title': f'Urgent Action: Fix Dangerous {rep.category_label} at {rep.location_name}',
                    'category': rep.category,
                    'location_name': rep.location_name,
                    'lat': rep.lat,
                    'lng': rep.lng,
                    'description': rep.description,
                    'submitter_name': rep.submitter_name,
                    'submitter_email': rep.submitter_email,
                }

        return render_template(
            'petitions/new.html',
            hazard_categories=HAZARD_CATEGORIES,
            all_zones=get_all_zones(),
            prefill=prefill,
        )

    @app.route('/petitions/new', methods=['POST'])
    def create_petition():
        """Process and persist a new community road petition."""
        title = request.form.get('title', '').strip()
        story = request.form.get('story', '').strip()
        category = request.form.get('category', '').strip()
        location_name = request.form.get('location_name', '').strip()
        creator_name = request.form.get('creator_name', '').strip()
        creator_email = request.form.get('creator_email', '').strip()
        creator_phone = request.form.get('creator_phone', '').strip()
        target_signatures = request.form.get('target_signatures', 50, type=int)
        linked_report_id = request.form.get('report_id', '').strip()

        if not (title and story and category and location_name and creator_name and creator_email):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('new_petition'))

        # Profanity & respect filter
        for txt, label in [(title, 'Petition Title'), (story, 'Petition Story'), (creator_name, 'Name')]:
            clean, msg = sanitize_or_validate(txt, label)
            if not clean:
                flash(msg, 'error')
                return redirect(url_for('new_petition'))

        raw_lat = request.form.get('lat', '').strip()
        raw_lng = request.form.get('lng', '').strip()
        lat = float(raw_lat) if raw_lat else None
        lng = float(raw_lng) if raw_lng else None

        # Auto-detect GHMC Division & Circle Target
        zone = detect_zone(lat=lat, lng=lng, location_name=location_name)

        year = datetime.utcnow().year
        petition_id = generate_petition_id(year)

        petition = Petition(
            petition_id=petition_id,
            title=title,
            story=story,
            category=category,
            location_name=location_name,
            lat=lat,
            lng=lng,
            zone_id=zone['id'],
            zone_name=zone['name'],
            target_authority=f"GHMC {zone['name']} & Hyderabad Traffic Police",
            target_signatures=max(10, target_signatures),
            creator_name=creator_name,
            creator_email=creator_email,
            creator_phone=creator_phone or None,
            report_id=linked_report_id or None,
            status='Active',
        )
        db.session.add(petition)
        db.session.commit()

        # Dispatch automated confirmation email to organizer
        try:
            send_petition_creation_confirmation(petition, base_url=request.host_url)
        except Exception:
            pass

        flash(f'Petition {petition.petition_id} launched successfully! Share it to mobilize signatures.', 'success')
        return redirect(url_for('petition_detail', petition_id=petition.petition_id))

    @app.route('/petitions/<string:petition_id>', methods=['GET'])
    def petition_detail(petition_id: str):
        """View a single community petition with story, signature counter, and sign form."""
        pet = Petition.query.filter_by(petition_id=petition_id.strip()).first()
        if not pet:
            abort(404)
        return render_template('petitions/detail.html', petition=pet)

    @app.route('/petitions/<string:petition_id>/sign', methods=['POST'])
    def sign_petition(petition_id: str):
        """Submit a verified digital signature for a petition."""
        pet = Petition.query.filter_by(petition_id=petition_id.strip()).first()
        if not pet:
            return jsonify(success=False, error='Petition not found.'), 404

        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        locality = request.form.get('locality', '').strip()
        comment = request.form.get('comment', '').strip()

        if not name or not email:
            return jsonify(success=False, error='Name and email are required to sign.'), 400

        # Profanity filter
        for txt, lbl in [(name, 'Name'), (comment, 'Reason for signing')]:
            clean, err_msg = sanitize_or_validate(txt, lbl)
            if not clean:
                return jsonify(success=False, error=err_msg), 400

        # Prevent duplicate signatures from the same email
        existing = PetitionSignature.query.filter_by(petition_id=pet.id, signer_email=email).first()
        if existing:
            return jsonify(success=False, error='You have already signed this road safety petition with this email.'), 400

        sig = PetitionSignature(
            petition_id=pet.id,
            signer_name=name,
            signer_email=email,
            signer_phone=phone or None,
            locality=locality or 'Concerned Resident',
            comment=comment or None,
        )
        db.session.add(sig)
        db.session.flush()

        # Update milestone status if goal reached
        if pet.signature_count >= pet.target_signatures and pet.status == 'Active':
            pet.status = 'Milestone Reached'

        pet.updated_at = datetime.utcnow()
        db.session.commit()

        # Dispatch automated verification email to signer
        try:
            send_petition_signature_confirmation(pet, sig, base_url=request.host_url)
        except Exception:
            pass

        return jsonify(
            success=True,
            signature_count=pet.signature_count,
            progress_percent=pet.progress_percent,
            status=pet.status,
        ), 201


# ---------------------------------------------------------------------------
# API route registration
# ---------------------------------------------------------------------------


def _register_api_routes(app: Flask) -> None:

    @app.route('/api/zones', methods=['GET'])
    def api_zones():
        """Return list of all 6 GHMC Municipal Zones with officer info."""
        return jsonify(get_all_zones())

    @app.route('/api/detect-zone', methods=['GET'])
    def api_detect_zone():
        """
        Dynamically determine the municipal zone based on lat/lng or location name.
        Used by the reporting map when a citizen clicks a location.
        """
        raw_lat = request.args.get('lat')
        raw_lng = request.args.get('lng')
        location = request.args.get('location', '').strip()
        lat = lng = None
        if raw_lat and raw_lng:
            try:
                lat = float(raw_lat)
                lng = float(raw_lng)
            except ValueError:
                pass
        zone = detect_zone(lat=lat, lng=lng, location_name=location)
        return jsonify(zone)

    @app.route('/api/reports', methods=['GET'])
    def api_reports():
        """
        Return a JSON array of reports suitable for map markers.

        Query parameters
        ----------------
        category : str   — filter by hazard category key
        status   : str   — filter by status string
        priority : str   — filter by priority_level (Low/Medium/High)
        """
        query = Report.query

        # Filter categories (support multiple ?category=... or single)
        cats = [c.strip() for c in request.args.getlist('category') if c.strip()]
        if not cats and request.args.get('category'):
            cats = [request.args.get('category').strip()]
        if cats and len(cats) < len(VALID_CATEGORIES):
            query = query.filter(Report.category.in_(cats))

        # Filter statuses (support multiple ?status=... or single, with slug-mapping)
        status_map = {
            'pending':            'Pending Review',
            'pending_review':     'Pending Review',
            'under_review':       'Under Review',
            'in_progress':        'Action in Progress',
            'action_in_progress': 'Action in Progress',
            'resolved':           'Resolved',
            'rejected':           'Rejected',
            'duplicate':          'Duplicate',
        }
        raw_statuses = [s.strip() for s in request.args.getlist('status') if s.strip()]
        if not raw_statuses and request.args.get('status'):
            raw_statuses = [request.args.get('status').strip()]
        if not raw_statuses:
            # Default: show active confirmed road dangers (Action in Progress & Under Review)
            query = query.filter(Report.status.in_(['Action in Progress', 'Under Review']))
        elif len(raw_statuses) < len(STATUS_CHOICES):
            mapped_statuses = [status_map.get(s.lower(), s) for s in raw_statuses]
            query = query.filter(Report.status.in_(mapped_statuses))

        priority = request.args.get('priority', '').strip()
        if priority and priority.lower() != 'all':
            query = query.filter(Report.priority_level.ilike(priority))

        reports = query.order_by(Report.created_at.desc()).all()
        return jsonify(
            total=len(reports),
            reports=[r.to_dict() for r in reports],
        )

    @app.route('/api/reports/<string:report_id>', methods=['GET'])
    def api_report_detail(report_id: str):
        """Return the full JSON detail for a single report by its report_id string."""
        report = Report.query.filter_by(report_id=report_id).first()
        if not report:
            return jsonify(error='Report not found.'), 404
        return jsonify(report=report.to_dict())

    @app.route('/api/track/<string:report_id>', methods=['GET'])
    def api_track_report(report_id: str):
        """
        Return full report detail plus its complete status-history
        timeline for the public tracking page.
        Supports case-insensitive Report ID, ID without prefix, or email address.
        """
        rid = report_id.strip()
        if not rid:
            return jsonify(error='Report ID or email is required.'), 400

        # If user entered an email address into the track path
        if '@' in rid:
            reports = Report.query.filter(Report.submitter_email.ilike(rid))\
                .order_by(Report.created_at.desc()).all()
            if reports:
                return jsonify(
                    total=len(reports),
                    reports=[r.to_dict(include_history=True) for r in reports],
                    report=reports[0].to_dict(include_history=True)
                )
            return jsonify(error=f'No reports found for email: {rid}'), 404

        # 1. Exact or case-insensitive match on report_id (e.g. "sr-2026-001" -> "SR-2026-001")
        report = Report.query.filter(Report.report_id.ilike(rid)).first()

        # 2. If not found, try partial match (e.g. user entered "001" or "2026-001" or "1")
        if not report:
            if rid.isdigit():
                # Try match by database id or suffix
                report = db.session.get(Report, int(rid))
                if not report:
                    report = Report.query.filter(Report.report_id.ilike(f'%{int(rid):03d}')).first()
            else:
                report = Report.query.filter(Report.report_id.ilike(f'%{rid}%')).first()

        if not report:
            return jsonify(error=f'Report "{report_id}" not found.'), 404

        return jsonify(
            report=report.to_dict(include_history=True),
            reports=[report.to_dict(include_history=True)],
            total=1
        )

    @app.route('/api/track-by-email', methods=['GET'])
    @app.route('/api/my_reports', methods=['GET'])
    def api_track_by_email():
        """
        Return all reports submitted by a given email address.
        Case-insensitive, and falls back to report_id if an ID was passed.
        """
        email = request.args.get('email', '').strip()
        if not email:
            return jsonify(error='email parameter is required.'), 400

        # Case-insensitive search by email
        reports = Report.query.filter(Report.submitter_email.ilike(email))\
            .order_by(Report.created_at.desc()).all()

        # If not found by email, check if user passed a report_id by mistake into the email query
        if not reports:
            single = Report.query.filter(Report.report_id.ilike(email)).first()
            if single:
                reports = [single]

        return jsonify(
            total=len(reports),
            reports=[r.to_dict(include_history=True) for r in reports],
            report=reports[0].to_dict(include_history=True) if reports else None
        )

    @app.route('/api/confirm/<string:report_id>', methods=['POST'])
    def api_confirm_report(report_id: str):
        """
        Add a community confirmation to an existing report.

        Expected JSON body (or form data)
        ----------------------------------
        confirmer_name  : str — required
        confirmer_email : str — required

        Rules
        -----
        • A given e-mail address may confirm a report only once.
        • Recalculates priority after each new confirmation.
        """
        report = Report.query.filter_by(report_id=report_id).first()
        if not report:
            return jsonify(error='Report not found.'), 404

        # Accept both JSON and form-data bodies
        if request.is_json:
            body = request.get_json(force=True)
        else:
            body = request.form

        name = (body.get('confirmer_name') or body.get('name') or '').strip()
        email = (body.get('confirmer_email') or body.get('email') or '').strip()
        comment = (body.get('comment') or '').strip()

        if not name or not email:
            return jsonify(error='Name and email are required.'), 400

        # Prevent duplicate confirmations from the same e-mail
        already = Confirmation.query.filter_by(
            report_id=report.id, confirmer_email=email
        ).first()
        if already:
            return jsonify(error='This email has already confirmed this report.'), 400

        # Prevent submitter from confirming their own report
        if email.lower() == report.submitter_email.lower():
            return jsonify(error='You cannot confirm your own report.'), 400

        # Profanity filter on review comment & reviewer name
        if comment:
            is_clean, err_msg = sanitize_or_validate(comment, 'Review comment')
            if not is_clean:
                return jsonify(error=err_msg), 400

        is_clean, err_msg = sanitize_or_validate(name, 'Name')
        if not is_clean:
            return jsonify(error=err_msg), 400

        confirmation = Confirmation(
            report_id=report.id,
            confirmer_name=name,
            confirmer_email=email,
            comment=comment or None,
        )
        db.session.add(confirmation)
        db.session.flush()

        # Recalculate priority with the updated confirmation count
        new_score, new_level = calculate_priority(
            report.severity, report.category, report.confirmation_count
        )
        report.priority_score = new_score
        report.priority_level = new_level
        db.session.commit()

        return jsonify(
            success=True,
            confirmation_count=report.confirmation_count,
            total_confirmations=report.confirmation_count,
            priority_level=new_level,
        ), 201

    @app.route('/api/route-safety', methods=['POST'])
    def api_route_safety():
        """
        Evaluate road safety risks along a route polyline corridor.
        Expects JSON: { polyline: [[lat, lng], ...], corridor_buffer_m: 400 }
        """
        data = request.get_json(force=True) or {}
        raw_polyline = data.get('polyline', [])
        polyline = []
        for pt in raw_polyline:
            try:
                polyline.append((float(pt[0]), float(pt[1])))
            except (ValueError, TypeError, IndexError):
                continue

        buffer_m = float(data.get('corridor_buffer_m', 400))
        # Fetch active road hazard reports that have coordinates
        reports = Report.query.filter(
            Report.lat.isnot(None),
            Report.lng.isnot(None),
            Report.status.in_(['Pending Review', 'Under Review', 'Action in Progress'])
        ).all()
        hazards = [r.to_dict() for r in reports]
        assessment = evaluate_route_safety(polyline, hazards, corridor_buffer_m=buffer_m)
        return jsonify(assessment)


# ---------------------------------------------------------------------------
# Admin route registration
# ---------------------------------------------------------------------------


def _register_admin_routes(app: Flask) -> None:

    # ------------------------------------------------------------------
    # Login / logout
    # ------------------------------------------------------------------

    @app.route('/admin/login', methods=['GET', 'POST'])
    def admin_login():
        """Authenticate an admin user and set a session cookie."""
        if session.get('admin_logged_in'):
            return redirect(url_for('admin_dashboard'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()
            user = authenticate_admin(username, password)
            if user:
                session['admin_logged_in'] = True
                session['admin_user'] = user['username']
                session['admin_role'] = user['role']
                session['admin_zone_id'] = user['zone_id']
                session['admin_zone_name'] = user['zone_name']
                session['admin_officer_name'] = user['officer_name']
                session['admin_title'] = user['title']
                flash(f"Welcome, {user['officer_name']} — {user['title']}", 'success')
                return redirect(url_for('admin_dashboard'))
            flash('Invalid administrative credentials. Please check your username and password.', 'error')

        return render_template('admin/login.html')

    @app.route('/admin/logout')
    def admin_logout():
        """Clear the admin session and redirect to the login page."""
        session.clear()
        flash('You have been logged out.', 'info')
        return redirect(url_for('admin_login'))

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    @app.route('/admin/')
    @login_required
    def admin_dashboard():
        """
        Admin dashboard with hierarchical support (Chief Admin vs Zonal Admin).
        """
        role = session.get('admin_role', 'super_admin')
        admin_zone_id = session.get('admin_zone_id', 'all')

        # Super admin can optionally filter dashboard by ?zone=...
        selected_zone = request.args.get('zone', '').strip().lower()
        if role == 'super_admin':
            if selected_zone and selected_zone != 'all':
                base_query = Report.query.filter_by(zone_id=selected_zone)
            else:
                base_query = Report.query
        else:
            # Regional zonal admin is strictly scoped to their own jurisdiction
            base_query = Report.query.filter_by(zone_id=admin_zone_id)

        total = base_query.count()
        pending = base_query.filter_by(status='Pending Review').count()
        high_priority = base_query.filter_by(priority_level='High').count()
        resolved = base_query.filter_by(status='Resolved').count()

        by_category = {}
        for key, label in HAZARD_CATEGORIES:
            by_category[label] = base_query.filter_by(category=key).count()

        by_status = {}
        for s in STATUS_CHOICES:
            by_status[s] = base_query.filter_by(status=s).count()

        recent = base_query.order_by(Report.created_at.desc()).limit(8).all()

        stats = {
            'total':         total,
            'total_reports': total,
            'pending':       pending,
            'high_priority': high_priority,
            'resolved':      resolved,
            'by_category':   by_category,
            'by_status':     by_status,
        }

        # For Chief Administrator: compute real-time performance breakdown for all 6 zones
        zonal_performance = []
        admin_credentials = []
        if role == 'super_admin':
            admin_credentials = get_all_credentials_for_super_admin()
            for z_id, z_data in HYDERABAD_ZONES.items():
                zq = Report.query.filter_by(zone_id=z_id)
                ztotal = zq.count()
                zpending = zq.filter_by(status='Pending Review').count()
                zin_progress = zq.filter_by(status='Action in Progress').count()
                zresolved = zq.filter_by(status='Resolved').count()
                rate = round((zresolved / ztotal * 100), 1) if ztotal > 0 else 0
                zonal_performance.append({
                    'zone_id': z_id,
                    'zone_name': z_data['name'],
                    'officer_name': z_data['officer_name'],
                    'officer_title': z_data['officer_title'],
                    'office_address': z_data['office_address'],
                    'contact_email': z_data['contact_email'],
                    'total': ztotal,
                    'pending': zpending,
                    'in_progress': zin_progress,
                    'resolved': zresolved,
                    'resolution_rate': rate,
                })

        return render_template(
            'admin/dashboard.html',
            stats=stats,
            recent_reports=recent,
            role=role,
            admin_zone_id=admin_zone_id,
            selected_zone=selected_zone,
            zonal_performance=zonal_performance,
            admin_credentials=admin_credentials,
            all_zones=get_all_zones(),
        )

    # ------------------------------------------------------------------
    # Report list
    # ------------------------------------------------------------------

    @app.route('/admin/reports', methods=['GET'])
    @login_required
    def admin_reports_list():
        """
        Admin view of all reports with optional search, filter, and sort.
        """
        role = session.get('admin_role', 'super_admin')
        admin_zone_id = session.get('admin_zone_id', 'all')

        query = Report.query

        # Zone scoping: zonal admin sees only their own zone; super admin can filter
        selected_zone = request.args.get('zone', '').strip().lower()
        if role == 'super_admin':
            if selected_zone and selected_zone != 'all':
                query = query.filter_by(zone_id=selected_zone)
        else:
            query = query.filter_by(zone_id=admin_zone_id)
            selected_zone = admin_zone_id

        search = (request.args.get('q') or request.args.get('search') or '').strip()
        if search:
            like = f'%{search}%'
            query = query.filter(
                Report.report_id.ilike(like)
                | Report.location_name.ilike(like)
                | Report.description.ilike(like)
                | Report.submitter_name.ilike(like)
            )

        cat = request.args.get('category', '').strip()
        if cat:
            query = query.filter_by(category=cat)

        status = request.args.get('status', '').strip()
        status_map = {
            'pending': 'Pending Review',
            'under_review': 'Under Review',
            'in_progress': 'Action in Progress',
            'resolved': 'Resolved',
            'rejected': 'Rejected',
            'duplicate': 'Duplicate',
        }
        if status in status_map:
            query = query.filter_by(status=status_map[status])
        elif status:
            query = query.filter_by(status=status)

        priority = request.args.get('priority', '').strip()
        if priority:
            query = query.filter(Report.priority_level.ilike(priority))

        sort_col = request.args.get('sort', 'created_at')
        order = request.args.get('order', 'desc')
        allowed_sorts = {
            'created_at':     Report.created_at,
            'date':           Report.created_at,
            'severity':       Report.severity,
            'priority_score': Report.priority_score,
            'status':         Report.status,
        }
        col = allowed_sorts.get(sort_col, Report.created_at)
        query = query.order_by(col.asc() if order == 'asc' else col.desc())

        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = 15
        total = query.count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        reports = query.offset((page - 1) * per_page).limit(per_page).all()

        return render_template(
            'admin/reports_list.html',
            reports=reports,
            hazard_categories=HAZARD_CATEGORIES,
            status_choices=STATUS_CHOICES,
            page=page,
            total_pages=total_pages,
            total=total,
            search=search,
            selected_category=cat,
            selected_status=status,
            selected_priority=priority,
            sort=sort_col,
            order=order,
            role=role,
            selected_zone=selected_zone,
            all_zones=get_all_zones(),
        )

    # ------------------------------------------------------------------
    # Single report detail (admin)
    # ------------------------------------------------------------------

    @app.route('/admin/reports/<report_id>', methods=['GET'])
    @login_required
    def admin_report_detail(report_id):
        """Admin detail view for a single report with its full status history."""
        if str(report_id).isdigit():
            report = db.session.get(Report, int(report_id))
        else:
            report = Report.query.filter_by(report_id=str(report_id)).first()
        if not report:
            abort(404)

        return render_template(
            'admin/report_detail.html',
            report=report,
            status_choices=STATUS_CHOICES,
            hazard_categories=HAZARD_CATEGORIES,
        )

    # ------------------------------------------------------------------
    # Update report status (admin POST)
    # ------------------------------------------------------------------

    @app.route('/admin/reports/<report_id>/update', methods=['POST'])
    @login_required
    def admin_update_report(report_id):
        """
        Update a report's status, priority level, and/or resolution note.

        Automatically creates a StatusHistory entry for every status change.
        """
        if str(report_id).isdigit():
            report = db.session.get(Report, int(report_id))
        else:
            report = Report.query.filter_by(report_id=str(report_id)).first()
        if not report:
            abort(404)

        raw_status = (request.form.get('status') or request.form.get('new_status') or '').strip()
        status_map = {
            'pending': 'Pending Review',
            'under_review': 'Under Review',
            'in_progress': 'Action in Progress',
            'resolved': 'Resolved',
            'rejected': 'Rejected',
            'duplicate': 'Duplicate',
        }
        new_status = status_map.get(raw_status.lower(), raw_status)

        raw_priority = (request.form.get('priority') or request.form.get('priority_level') or '').strip()
        priority_level = raw_priority.capitalize() if raw_priority else ''

        resolution_note = request.form.get('resolution_note', '').strip()
        admin_note = request.form.get('admin_note', '').strip()

        if new_status and new_status not in STATUS_CHOICES:
            abort(400)

        if priority_level and priority_level not in ('Low', 'Medium', 'High'):
            abort(400)

        # Record status change history only when the status actually changes
        status_changed = False
        old_status = report.status
        if new_status and new_status != report.status:
            history_entry = StatusHistory(
                report_id=report.id,
                old_status=report.status,
                new_status=new_status,
                note=admin_note or resolution_note or None,
                changed_by=session.get('admin_user', 'Admin'),
            )
            db.session.add(history_entry)
            report.status = new_status
            status_changed = True

        if priority_level:
            report.priority_level = priority_level

        if resolution_note:
            report.resolution_note = resolution_note

        report.updated_at = datetime.utcnow()
        db.session.commit()

        # Dispatch status update email to citizen if status changed
        if status_changed:
            try:
                send_status_update_notification(
                    report,
                    old_status=old_status,
                    new_status=new_status,
                    note=resolution_note or admin_note or '',
                    base_url=request.host_url,
                )
            except Exception:
                pass

        flash(f'Report {report.report_id} updated successfully.', 'success')
        return redirect(url_for('admin_report_detail', report_id=report.report_id))

    # ------------------------------------------------------------------
    # Petitions management
    # ------------------------------------------------------------------

    @app.route('/admin/petitions', methods=['GET'])
    @login_required
    def admin_petitions():
        """Admin review of citizen road safety petitions."""
        role = session.get('admin_role', 'super_admin')
        admin_zone_id = session.get('admin_zone_id', 'all')
        selected_zone = request.args.get('zone', '').strip().lower()

        if role == 'super_admin':
            if selected_zone and selected_zone != 'all':
                petitions = Petition.query.filter_by(zone_id=selected_zone).order_by(Petition.created_at.desc()).all()
            else:
                petitions = Petition.query.order_by(Petition.created_at.desc()).all()
        else:
            petitions = Petition.query.filter_by(zone_id=admin_zone_id).order_by(Petition.created_at.desc()).all()

        return render_template(
            'admin/petitions.html',
            petitions=petitions,
            all_zones=get_all_zones(),
            selected_zone=selected_zone,
            status_choices=PETITION_STATUS_CHOICES,
        )

    @app.route('/admin/petitions/<string:petition_id>/update', methods=['POST'])
    @login_required
    def admin_update_petition(petition_id: str):
        """Update petition status and post municipal review response."""
        pet = Petition.query.filter_by(petition_id=petition_id.strip()).first_or_404()
        new_status = request.form.get('status', pet.status).strip()
        official_response = request.form.get('official_response', '').strip()

        if new_status in PETITION_STATUS_CHOICES:
            pet.status = new_status
        if official_response:
            pet.official_response = official_response
        pet.updated_at = datetime.utcnow()
        db.session.commit()
        flash(f'Petition {pet.petition_id} updated to "{pet.status}".', 'success')
        return redirect(url_for('admin_petitions'))


# ---------------------------------------------------------------------------
# Application entry-point
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
