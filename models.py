"""
models.py — SQLAlchemy ORM models for SafeRoad.

Tables
------
  reports          — every hazard report submitted by the public
  status_history   — full audit trail of every status change
  confirmations    — community "I saw this too" confirmations
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# ---------------------------------------------------------------------------
# Lookup data shared between the model layer and the application layer
# ---------------------------------------------------------------------------

HAZARD_CATEGORIES = [
    ('pothole',           'Pothole'),
    ('damaged_surface',   'Damaged Road Surface'),
    ('waterlogging',      'Waterlogging'),
    ('missing_crossing',  'Missing Pedestrian Crossing'),
    ('unsafe_intersection', 'Unsafe Intersection'),
    ('damaged_sign',      'Damaged Traffic Sign'),
    ('poor_lighting',     'Inadequate Street Lighting'),
    ('other',             'Other'),
]

STATUS_CHOICES = [
    'Pending Review',
    'Under Review',
    'Action in Progress',
    'Resolved',
    'Rejected',
    'Duplicate',
]

PETITION_STATUS_CHOICES = [
    'Active',
    'Milestone Reached',
    'Under Official Review',
    'Victorious / Repaired',
    'Closed',
]

# Convenience set of valid category keys for validation
VALID_CATEGORIES = {key for key, _ in HAZARD_CATEGORIES}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

class Report(db.Model):
    """
    Core entity representing a single road-hazard report submitted by a
    member of the public.
    """
    __tablename__ = 'reports'

    id              = db.Column(db.Integer, primary_key=True)
    # Human-readable identifier shown in the UI, e.g. "SR-2026-001"
    report_id       = db.Column(db.String(20), unique=True, nullable=False)

    # Hazard classification
    category        = db.Column(db.String(50), nullable=False)

    # Location — plain text is required; GPS coordinates are optional
    location_name   = db.Column(db.String(255), nullable=False)
    lat             = db.Column(db.Float, nullable=True)
    lng             = db.Column(db.Float, nullable=True)

    # Municipal administrative jurisdiction (GHMC Zonal Division)
    zone_id         = db.Column(db.String(50), nullable=True, default='serilingampally')
    zone_name       = db.Column(db.String(100), nullable=True, default='Serilingampally Zone (West)')
    assigned_officer = db.Column(db.String(150), nullable=True, default='Er. K. V. Rao (Circle Engineer)')

    # Details
    description     = db.Column(db.Text, nullable=False)
    severity        = db.Column(db.Integer, nullable=False)    # 1 (low) – 5 (extreme)
    image_path      = db.Column(db.String(255), nullable=True) # relative path under static/

    # Workflow
    status          = db.Column(db.String(50), default='Pending Review')
    priority_score  = db.Column(db.Integer, default=0)
    priority_level  = db.Column(db.String(10), default='Low')  # Low / Medium / High

    # Reporter contact
    submitter_name  = db.Column(db.String(100), nullable=False)
    submitter_email = db.Column(db.String(150), nullable=False)

    # Timestamps
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow,
                                onupdate=datetime.utcnow)

    # Admin notes written when closing / resolving a report
    resolution_note = db.Column(db.Text, nullable=True)

    # Relationships
    status_history  = db.relationship(
        'StatusHistory', backref='report', lazy=True,
        cascade='all, delete-orphan'
    )
    confirmations   = db.relationship(
        'Confirmation', backref='report', lazy=True,
        cascade='all, delete-orphan'
    )

    # ------------------------------------------------------------------
    # Computed properties (no extra DB column needed)
    # ------------------------------------------------------------------

    @property
    def confirmation_count(self) -> int:
        """Number of community confirmations for this report."""
        return len(self.confirmations)

    @property
    def confirmation_list(self) -> list:
        """List of confirmation records for templates."""
        return [
            {
                'name': c.confirmer_name,
                'email': c.confirmer_email,
                'confirmed_at': c.confirmed_at.strftime('%d %b %Y, %H:%M') if c.confirmed_at else '',
            }
            for c in self.confirmations
        ]

    @property
    def latitude(self):
        """Alias for lat to support templates."""
        return self.lat

    @property
    def longitude(self):
        """Alias for lng to support templates."""
        return self.lng

    @property
    def photo_path(self):
        """Alias for image_path to support template variants."""
        return self.image_path

    @property
    def submitted_at(self):
        """Alias for created_at to support UI templates."""
        return self.created_at

    @property
    def priority(self) -> str:
        """Alias for priority_level to support UI templates."""
        return self.priority_level

    @property
    def category_label(self) -> str:
        """Human-readable category label derived from the HAZARD_CATEGORIES list."""
        return dict(HAZARD_CATEGORIES).get(self.category, self.category)

    def to_dict(self, include_history: bool = False) -> dict:
        """
        Serialise the report to a plain dictionary suitable for JSON responses.

        Parameters
        ----------
        include_history : bool
            When True, the full status-history list is embedded in the response.
        """
        data = {
            'id':                 self.id,
            'report_id':          self.report_id,
            'category':           self.category,
            'category_label':     self.category_label,
            'location_name':      self.location_name,
            'lat':                self.lat,
            'lng':                self.lng,
            'latitude':           self.lat,
            'longitude':          self.lng,
            'zone_id':            self.zone_id or 'serilingampally',
            'zone_name':          self.zone_name or 'Serilingampally Zone (West)',
            'assigned_officer':   self.assigned_officer or 'Circle Engineering Cell',
            'description':        self.description,
            'severity':           self.severity,
            'image_path':         self.image_path,
            'status':             self.status,
            'priority_score':     self.priority_score,
            'priority_level':     self.priority_level,
            'submitter_name':     self.submitter_name,
            'submitter_email':    self.submitter_email,
            'confirmation_count': self.confirmation_count,
            'confirmations':      [c.to_dict() for c in self.confirmations],
            'resolution_note':    self.resolution_note,
            'created_at':         self.created_at.isoformat() if self.created_at else None,
            'updated_at':         self.updated_at.isoformat() if self.updated_at else None,
            'submitted_at':       self.created_at.strftime('%d %b %Y') if self.created_at else '—',
            'priority':           self.priority_level,
        }
        if include_history:
            data['status_history'] = [h.to_dict() for h in self.status_history]
        return data

    def __repr__(self) -> str:
        return f'<Report {self.report_id} [{self.status}]>'


# ---------------------------------------------------------------------------
# StatusHistory
# ---------------------------------------------------------------------------

class StatusHistory(db.Model):
    """
    Immutable audit log entry created every time a report's status changes.
    Provides a full timeline visible to both admins and reporters.
    """
    __tablename__ = 'status_history'

    id          = db.Column(db.Integer, primary_key=True)
    report_id   = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False)
    old_status  = db.Column(db.String(50), nullable=True)   # NULL for the initial entry
    new_status  = db.Column(db.String(50), nullable=False)
    note        = db.Column(db.Text, nullable=True)
    changed_by  = db.Column(db.String(100), default='System')
    changed_at  = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def status(self) -> str:
        """Alias for new_status for templates."""
        return self.new_status

    def to_dict(self) -> dict:
        return {
            'id':         self.id,
            'status':     self.new_status,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'note':       self.note,
            'changed_by': self.changed_by,
            'changed_at': self.changed_at.strftime('%d %b %Y, %H:%M') if self.changed_at else None,
        }

    def __repr__(self) -> str:
        return f'<StatusHistory {self.old_status} → {self.new_status}>'


# ---------------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------------

class Confirmation(db.Model):
    """
    A community "I saw this hazard too" vote attached to a report.
    Each unique e-mail address may confirm a given report only once
    (enforced at the application layer).
    """
    __tablename__ = 'confirmations'

    id              = db.Column(db.Integer, primary_key=True)
    report_id       = db.Column(db.Integer, db.ForeignKey('reports.id'), nullable=False)
    confirmer_name  = db.Column(db.String(100), nullable=False)
    confirmer_email = db.Column(db.String(150), nullable=False)
    comment         = db.Column(db.Text, nullable=True)  # Community review / note
    confirmed_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id':             self.id,
            'confirmer_name': self.confirmer_name,
            'comment':        self.comment,
            'confirmed_at':   self.confirmed_at.isoformat() if self.confirmed_at else None,
        }

    def __repr__(self) -> str:
        return f'<Confirmation by {self.confirmer_email}>'


# ---------------------------------------------------------------------------
# Community Petitions & Digital Signatures (Change.org-style for Road Safety)
# ---------------------------------------------------------------------------

class Petition(db.Model):
    """
    Public community petition started by a citizen to escalate an unaddressed
    road hazard into an official civic campaign with verifiable signatures.
    """
    __tablename__ = 'petitions'

    id                 = db.Column(db.Integer, primary_key=True)
    petition_id        = db.Column(db.String(25), unique=True, nullable=False) # e.g. PET-2026-001
    title              = db.Column(db.String(255), nullable=False)
    story              = db.Column(db.Text, nullable=False) # Why this matters
    category           = db.Column(db.String(50), nullable=False)
    location_name      = db.Column(db.String(255), nullable=False)
    lat                = db.Column(db.Float, nullable=True)
    lng                = db.Column(db.Float, nullable=True)
    zone_id            = db.Column(db.String(50), default='serilingampally')
    zone_name          = db.Column(db.String(100), default='Serilingampally Zone (West)')
    target_authority   = db.Column(db.String(200), default='GHMC Circle Engineering Cell & Traffic Police')
    target_signatures  = db.Column(db.Integer, default=50) # Signature goal (e.g. 50, 100, 250)
    creator_name       = db.Column(db.String(100), nullable=False)
    creator_email      = db.Column(db.String(150), nullable=False)
    creator_phone      = db.Column(db.String(20), nullable=True)
    image_path         = db.Column(db.String(255), nullable=True)
    status             = db.Column(db.String(50), default='Active')
    report_id          = db.Column(db.String(25), nullable=True) # Optional link to Report ID SR-2026-xxx
    official_response  = db.Column(db.Text, nullable=True) # Authority note / repair resolution
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at         = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    signatures         = db.relationship('PetitionSignature', backref='petition', lazy=True, cascade='all, delete-orphan')

    @property
    def signature_count(self) -> int:
        return len(self.signatures)

    @property
    def progress_percent(self) -> int:
        if not self.target_signatures or self.target_signatures <= 0:
            return 100
        return min(100, int((len(self.signatures) / self.target_signatures) * 100))

    @property
    def category_label(self) -> str:
        return dict(HAZARD_CATEGORIES).get(self.category, self.category.replace('_', ' ').title())

    def to_dict(self, include_signatures: bool = False) -> dict:
        data = {
            'id':                 self.id,
            'petition_id':        self.petition_id,
            'title':              self.title,
            'story':              self.story,
            'category':           self.category,
            'category_label':     self.category_label,
            'location_name':      self.location_name,
            'lat':                self.lat,
            'lng':                self.lng,
            'zone_id':            self.zone_id,
            'zone_name':          self.zone_name,
            'target_authority':   self.target_authority,
            'target_signatures':  self.target_signatures,
            'signature_count':    self.signature_count,
            'progress_percent':   self.progress_percent,
            'creator_name':       self.creator_name,
            'creator_email':      self.creator_email,
            'image_path':         self.image_path,
            'status':             self.status,
            'report_id':          self.report_id,
            'official_response':  self.official_response,
            'created_at':         self.created_at.strftime('%d %b %Y') if self.created_at else None,
        }
        if include_signatures:
            data['recent_signatures'] = [s.to_dict() for s in sorted(self.signatures, key=lambda x: x.signed_at or datetime.min, reverse=True)[:25]]
        return data

    def __repr__(self) -> str:
        return f'<Petition {self.petition_id} - {self.title[:30]}>'


class PetitionSignature(db.Model):
    """
    A verified community digital signature supporting a road safety petition.
    """
    __tablename__ = 'petition_signatures'

    id            = db.Column(db.Integer, primary_key=True)
    petition_id   = db.Column(db.Integer, db.ForeignKey('petitions.id'), nullable=False)
    signer_name   = db.Column(db.String(100), nullable=False)
    signer_email  = db.Column(db.String(150), nullable=False)
    signer_phone  = db.Column(db.String(20), nullable=True)
    locality      = db.Column(db.String(100), nullable=True) # e.g. "Madhapur resident", "Daily commuter"
    comment       = db.Column(db.Text, nullable=True) # "Reason for signing"
    signed_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id':           self.id,
            'signer_name':  self.signer_name,
            'locality':     self.locality or 'Concerned Resident',
            'comment':      self.comment,
            'signed_at':    self.signed_at.strftime('%d %b %Y, %I:%M %p') if self.signed_at else '',
        }

    def __repr__(self) -> str:
        return f'<PetitionSignature {self.signer_name} on #{self.petition_id}>'
