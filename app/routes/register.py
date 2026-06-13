# app/routes/register.py
# ============================================================
#  WayBuddy — Registration Routes
#
#  Handles form submissions from the landing page.
#  Two endpoints:
#    POST /api/register/seeker  — solo traveller signs up
#    POST /api/register/helper  — volunteer helper signs up
#
#  Both endpoints:
#    1. Validate that required fields are present
#    2. Validate phone format and email format
#    3. Check for duplicate active registrations
#    4. Create a new database row
#    5. Return JSON confirming success or describing the error
# ============================================================

from flask    import Blueprint, request, jsonify
from ..models import db, Seeker, Helper
from datetime import datetime
from app.utils.validation import validate_indian_phone, validate_email, check_duplicate

register_bp = Blueprint('register', __name__)


# ── HELPER FUNCTION ──────────────────────────────────────────────────────────

def parse_date(date_str):
    """
    Converts a date string from the HTML form (YYYY-MM-DD)
    into a Python date object that SQLAlchemy can store.
    Returns None if the string is empty or malformed.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


# ── POST /api/register/seeker ────────────────────────────────────────────────

@register_bp.route('/register/seeker', methods=['POST'])
def register_seeker():
    """
    Receives a seeker registration form submission.
    Expects JSON or form data with the seeker's details.
    """
    data = request.get_json(silent=True) or request.form.to_dict()

    # ── HONEYPOT (bot trap) ──────────────────────────────────────────────────
    # Hidden field — humans never fill it; bots usually do.
    if data.get('website'):
        return jsonify({'success': False, 'error': 'Registration failed.'}), 400

    # ── REQUIRED FIELD CHECK ─────────────────────────────────────────────────
    required = [
        'name', 'phone', 'flight_number',
        'departure_airport', 'arrival_airport', 'travel_date'
    ]
    missing = [f for f in required if not data.get(f, '').strip()]
    if missing:
        return jsonify({
            'success': False,
            'error': f'Missing required fields: {", ".join(missing)}'
        }), 400

    # ── PHONE VALIDATION ─────────────────────────────────────────────────────
    phone, phone_err = validate_indian_phone(data.get('phone', ''))
    if phone_err:
        return jsonify({'success': False, 'error': phone_err}), 422

    # ── EMAIL VALIDATION ─────────────────────────────────────────────────────
    email = data.get('email', '').strip().lower() or None
    email_ok, email_err = validate_email(email or '')
    if not email_ok:
        return jsonify({'success': False, 'error': email_err}), 422

    # ── DUPLICATE CHECK ──────────────────────────────────────────────────────
    dup_err = check_duplicate(Seeker, db.session, phone, email)
    if dup_err:
        return jsonify({'success': False, 'error': dup_err}), 409

    # ── CREATE SEEKER ROW ────────────────────────────────────────────────────
    try:
        seeker = Seeker(
            name              = data['name'].strip(),
            phone             = phone,
            email             = email,
            age               = int(data['age']) if data.get('age') else None,
            gender            = data.get('gender', '').strip() or None,
            flight_number     = data['flight_number'].strip().upper(),
            departure_airport = data['departure_airport'].strip(),
            arrival_airport   = data['arrival_airport'].strip(),
            travel_date       = parse_date(data['travel_date']),
            departure_time    = data.get('departure_time', '').strip() or None,
            languages         = data.get('languages', '').strip() or None,
            help_needed       = data.get('help_needed', '').strip() or None,
            notes             = data.get('notes', '').strip() or None,
            status            = 'approved',
            is_paid           = False,
        )
        db.session.add(seeker)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Registration received. We will contact you before your travel date.',
            'seeker_id': seeker.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}'
        }), 500


# ── POST /api/register/helper ────────────────────────────────────────────────

@register_bp.route('/register/helper', methods=['POST'])
def register_helper():
    """
    Receives a helper registration form submission.
    Helper is created with status 'pending_approval' —
    an admin must approve them before they appear in the
    matching pool.
    """
    data = request.get_json(silent=True) or request.form.to_dict()

    # ── HONEYPOT (bot trap) ──────────────────────────────────────────────────
    if data.get('website'):
        return jsonify({'success': False, 'error': 'Registration failed.'}), 400

    # ── REQUIRED FIELD CHECK ─────────────────────────────────────────────────
    required = ['name', 'phone']
    missing = [f for f in required if not data.get(f, '').strip()]
    if missing:
        return jsonify({
            'success': False,
            'error': f'Missing required fields: {", ".join(missing)}'
        }), 400

    # ── PHONE VALIDATION ─────────────────────────────────────────────────────
    phone, phone_err = validate_indian_phone(data.get('phone', ''))
    if phone_err:
        return jsonify({'success': False, 'error': phone_err}), 422

    # ── EMAIL VALIDATION ─────────────────────────────────────────────────────
    email = data.get('email', '').strip().lower() or None
    email_ok, email_err = validate_email(email or '')
    if not email_ok:
        return jsonify({'success': False, 'error': email_err}), 422

    # ── DUPLICATE CHECK ──────────────────────────────────────────────────────
    dup_err = check_duplicate(Helper, db.session, phone, email)
    if dup_err:
        return jsonify({'success': False, 'error': dup_err}), 409

    # ── CREATE HELPER ROW ────────────────────────────────────────────────────
    try:
        helper = Helper(
            name              = data['name'].strip(),
            phone             = phone,
            email             = email,
            age               = int(data['age']) if data.get('age') else None,
            gender            = data.get('gender', '').strip() or None,
            flight_number     = data.get('flight_number', '').strip().upper() or None,
            departure_airport = data.get('departure_airport', '').strip() or None,
            arrival_airport   = data.get('arrival_airport', '').strip() or None,
            travel_date       = parse_date(data.get('travel_date', '')),
            departure_time    = data.get('departure_time', '').strip() or None,
            languages         = data.get('languages', '').strip() or None,
            skills            = data.get('skills', '').strip() or None,
            based_at_airport  = data.get('based_at_airport', '').strip() or None,
            notes             = data.get('notes', '').strip() or None,
            status            = 'pending_approval',
        )
        db.session.add(helper)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Thank you for registering as a helper. Our team will review your profile shortly.',
            'helper_id': helper.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Registration failed: {str(e)}'
        }), 500
