# ============================================================
#  WayBuddy — SQLAlchemy Models
#  File: models.py
#  Place this in your Flask project root or in a /models folder.
#
#  Usage in app.py:
#    from models import db, Seeker, Helper, Match, Payment
#    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
#    db.init_app(app)
# ============================================================

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def now_utc():
    """Returns the current UTC time. Used as a default for timestamp columns."""
    return datetime.now(timezone.utc)


# ── SEEKER ──────────────────────────────────────────────────

class Seeker(db.Model):
    __tablename__ = 'seekers'

    id                = db.Column(db.Integer, primary_key=True)

    # Personal info
    name              = db.Column(db.String(120), nullable=False)
    phone             = db.Column(db.String(20),  nullable=False)
    email             = db.Column(db.String(200))
    age               = db.Column(db.SmallInteger)
    gender            = db.Column(db.String(30))

    # Flight info
    flight_number     = db.Column(db.String(20),  nullable=False)
    departure_airport = db.Column(db.String(100), nullable=False)
    arrival_airport   = db.Column(db.String(100), nullable=False)
    travel_date       = db.Column(db.Date,        nullable=False)
    departure_time    = db.Column(db.String(10))

    # Needs & preferences (stored as comma-separated strings)
    languages         = db.Column(db.Text)
    help_needed       = db.Column(db.Text)
    notes             = db.Column(db.Text)

    # System fields
    status            = db.Column(db.String(20), nullable=False, default='pending')
    is_paid           = db.Column(db.Boolean,    nullable=False, default=False)
    created_at        = db.Column(db.DateTime(timezone=True), default=now_utc)
    updated_at        = db.Column(db.DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relationships
    match             = db.relationship('Match',   back_populates='seeker', uselist=False)
    payments          = db.relationship('Payment', back_populates='seeker')

    def to_dict(self):
        """Serialise to a dict for JSON API responses."""
        return {
            'id':                 self.id,
            'name':               self.name,
            'phone':              self.phone,
            'email':              self.email,
            'age':                self.age,
            'gender':             self.gender,
            'flight_number':      self.flight_number,
            'departure_airport':  self.departure_airport,
            'arrival_airport':    self.arrival_airport,
            'travel_date':        str(self.travel_date),
            'departure_time':     self.departure_time,
            'languages':          self.languages.split(',') if self.languages else [],
            'help_needed':        self.help_needed.split(',') if self.help_needed else [],
            'notes':              self.notes,
            'status':             self.status,
            'is_paid':            self.is_paid,
            'created_at':         self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Seeker {self.id}: {self.name} ({self.flight_number})>'


# ── HELPER ──────────────────────────────────────────────────

class Helper(db.Model):
    __tablename__ = 'helpers'

    id                = db.Column(db.Integer, primary_key=True)

    # Personal info
    name              = db.Column(db.String(120), nullable=False)
    phone             = db.Column(db.String(20),  nullable=False)
    email             = db.Column(db.String(200))
    age               = db.Column(db.SmallInteger)
    gender            = db.Column(db.String(30))

    # Flight info
    flight_number     = db.Column(db.String(20))
    departure_airport = db.Column(db.String(100))
    arrival_airport   = db.Column(db.String(100))
    travel_date       = db.Column(db.Date)
    departure_time    = db.Column(db.String(10))

    # Skills & availability
    languages         = db.Column(db.Text)
    skills            = db.Column(db.Text)
    based_at_airport  = db.Column(db.String(100))
    notes             = db.Column(db.Text)

    # System fields
    # pending_approval → approved → matched → unavailable
    status            = db.Column(db.String(20), nullable=False, default='pending_approval')
    created_at        = db.Column(db.DateTime(timezone=True), default=now_utc)
    updated_at        = db.Column(db.DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relationships
    matches           = db.relationship('Match', back_populates='helper')

    def to_dict(self):
        return {
            'id':                 self.id,
            'name':               self.name,
            'phone':              self.phone,
            'email':              self.email,
            'age':                self.age,
            'gender':             self.gender,
            'flight_number':      self.flight_number,
            'departure_airport':  self.departure_airport,
            'arrival_airport':    self.arrival_airport,
            'travel_date':        str(self.travel_date) if self.travel_date else None,
            'departure_time':     self.departure_time,
            'languages':          self.languages.split(',') if self.languages else [],
            'skills':             self.skills.split(',') if self.skills else [],
            'based_at_airport':   self.based_at_airport,
            'notes':              self.notes,
            'status':             self.status,
            'created_at':         self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Helper {self.id}: {self.name} ({self.status})>'


# ── MATCH ───────────────────────────────────────────────────

class Match(db.Model):
    __tablename__ = 'matches'

    id            = db.Column(db.Integer, primary_key=True)

    seeker_id     = db.Column(db.Integer, db.ForeignKey('seekers.id', ondelete='CASCADE'), nullable=False, unique=True)
    helper_id     = db.Column(db.Integer, db.ForeignKey('helpers.id', ondelete='CASCADE'), nullable=False)

    # pending → confirmed → notified → completed  (or → cancelled)
    status        = db.Column(db.String(20), nullable=False, default='pending')

    matched_at    = db.Column(db.DateTime(timezone=True), default=now_utc)
    notified_at   = db.Column(db.DateTime(timezone=True))
    completed_at  = db.Column(db.DateTime(timezone=True))

    admin_notes   = db.Column(db.Text)
    created_at    = db.Column(db.DateTime(timezone=True), default=now_utc)
    updated_at    = db.Column(db.DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Relationships
    seeker        = db.relationship('Seeker',  back_populates='match')
    helper        = db.relationship('Helper',  back_populates='matches')
    payments      = db.relationship('Payment', back_populates='match')

    def to_dict(self):
        return {
            'id':           self.id,
            'seeker_id':    self.seeker_id,
            'helper_id':    self.helper_id,
            'status':       self.status,
            'matched_at':   self.matched_at.isoformat() if self.matched_at else None,
            'notified_at':  self.notified_at.isoformat() if self.notified_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'admin_notes':  self.admin_notes,
            # Embed name + flight for convenience in the dashboard
            'seeker_name':  self.seeker.name if self.seeker else None,
            'helper_name':  self.helper.name if self.helper else None,
        }

    def __repr__(self):
        return f'<Match {self.id}: seeker={self.seeker_id} ↔ helper={self.helper_id} [{self.status}]>'


# ── PAYMENT ─────────────────────────────────────────────────

class Payment(db.Model):
    __tablename__ = 'payments'

    id                      = db.Column(db.Integer, primary_key=True)

    seeker_id               = db.Column(db.Integer, db.ForeignKey('seekers.id', ondelete='CASCADE'), nullable=False)
    match_id                = db.Column(db.Integer, db.ForeignKey('matches.id', ondelete='SET NULL'), nullable=True)

    # Razorpay fields
    razorpay_order_id       = db.Column(db.String(100), unique=True)
    razorpay_payment_id     = db.Column(db.String(100), unique=True)
    razorpay_signature      = db.Column(db.String(300))

    # Amount in paise (INR smallest unit). e.g. ₹99 = 9900
    amount_paise            = db.Column(db.Integer, nullable=False, default=0)
    currency                = db.Column(db.String(5), nullable=False, default='INR')

    # created → paid → failed  (or → refunded)
    status                  = db.Column(db.String(20), nullable=False, default='created')

    created_at              = db.Column(db.DateTime(timezone=True), default=now_utc)
    paid_at                 = db.Column(db.DateTime(timezone=True))

    # Relationships
    seeker                  = db.relationship('Seeker',  back_populates='payments')
    match                   = db.relationship('Match',   back_populates='payments')

    def to_dict(self):
        return {
            'id':                   self.id,
            'seeker_id':            self.seeker_id,
            'match_id':             self.match_id,
            'razorpay_order_id':    self.razorpay_order_id,
            'razorpay_payment_id':  self.razorpay_payment_id,
            'amount_paise':         self.amount_paise,
            'amount_inr':           self.amount_paise / 100,
            'currency':             self.currency,
            'status':               self.status,
            'created_at':           self.created_at.isoformat() if self.created_at else None,
            'paid_at':              self.paid_at.isoformat() if self.paid_at else None,
        }

    def __repr__(self):
        return f'<Payment {self.id}: seeker={self.seeker_id} [{self.status}] {self.amount_paise}p>'
