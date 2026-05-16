# app/routes/admin.py
# ============================================================
#  WayBuddy — Admin Routes
#
#  All routes in this file are for the admin dashboard only.
#  They are prefixed with /api/admin (set in __init__.py).
#
#  Endpoints:
#    GET  /api/admin/seekers          — list all seekers
#    GET  /api/admin/helpers          — list all helpers
#    POST /api/admin/match            — confirm a seeker-helper pair
#    POST /api/admin/approve-helper   — approve a pending helper
#    POST /api/admin/unmatch          — remove a confirmed match
#
#  IMPORTANT: These routes have no authentication yet.
#  In Phase 3 a simple password check will be added before
#  any of these routes can be called.
# ============================================================

from flask      import Blueprint, request, jsonify
from ..models   import db, Seeker, Helper, Match
from datetime   import datetime, timezone

admin_bp = Blueprint('admin', __name__)


# ── GET /api/admin/seekers ───────────────────────────────────

@admin_bp.route('/seekers', methods=['GET'])
def get_seekers():
    """
    Returns all seekers ordered by travel date (soonest first).
    The dashboard calls this on load and on every refresh.
    Query param ?status=pending filters by status if provided.
    """
    status = request.args.get('status')

    query = Seeker.query.order_by(Seeker.travel_date.asc())
    if status:
        query = query.filter(Seeker.status == status)

    seekers = query.all()

    return jsonify({
        'success': True,
        'seekers': [s.to_dict() for s in seekers],
        'count':   len(seekers),
        'fetched': datetime.now(timezone.utc).isoformat()
    }), 200


# ── GET /api/admin/helpers ───────────────────────────────────

@admin_bp.route('/helpers', methods=['GET'])
def get_helpers():
    """
    Returns all approved helpers ordered by travel date.
    Only helpers with status 'approved' appear in the matching
    pool — pending_approval helpers are excluded by default.
    Query param ?status=all overrides this to show all helpers.
    """
    status = request.args.get('status', 'approved')

    query = Helper.query.order_by(Helper.travel_date.asc())
    if status != 'all':
        query = query.filter(Helper.status == status)

    helpers = query.all()

    return jsonify({
        'success': True,
        'helpers': [h.to_dict() for h in helpers],
        'count':   len(helpers),
        'fetched': datetime.now(timezone.utc).isoformat()
    }), 200


# ── POST /api/admin/match ────────────────────────────────────

@admin_bp.route('/match', methods=['POST'])
def create_match():
    """
    Confirms a seeker-helper pairing.
    Expects JSON: { "seeker_id": 1, "helper_id": 2, "admin_notes": "..." }

    What this does:
      1. Validates both IDs exist and are not already matched
      2. Creates a new row in the matches table
      3. Updates seeker status to 'matched'
      4. Updates helper status to 'matched'
      5. Returns the created match
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'No JSON body provided'}), 400

    seeker_id = data.get('seeker_id')
    helper_id = data.get('helper_id')

    if not seeker_id or not helper_id:
        return jsonify({'success': False, 'error': 'seeker_id and helper_id are required'}), 400

    # ── FETCH BOTH RECORDS ───────────────────────────────────
    seeker = Seeker.query.get(seeker_id)
    helper = Helper.query.get(helper_id)

    if not seeker:
        return jsonify({'success': False, 'error': f'Seeker {seeker_id} not found'}), 404
    if not helper:
        return jsonify({'success': False, 'error': f'Helper {helper_id} not found'}), 404

    # ── GUARD: ALREADY MATCHED ───────────────────────────────
    # The database has a UNIQUE constraint on matches.seeker_id,
    # but checking here gives a friendlier error message.
    existing = Match.query.filter_by(seeker_id=seeker_id).first()
    if existing:
        return jsonify({
            'success': False,
            'error':   f'Seeker {seeker.name} is already matched (match ID {existing.id})'
        }), 409

    if seeker.status == 'matched':
        return jsonify({'success': False, 'error': f'Seeker {seeker.name} is already matched'}), 409
    if helper.status == 'matched':
        return jsonify({'success': False, 'error': f'Helper {helper.name} is already matched'}), 409

    # ── CREATE MATCH ─────────────────────────────────────────
    try:
        match = Match(
            seeker_id   = seeker_id,
            helper_id   = helper_id,
            status      = 'confirmed',
            admin_notes = data.get('admin_notes', '').strip() or None,
            matched_at  = datetime.now(timezone.utc),
        )
        db.session.add(match)

        seeker.status = 'matched'
        helper.status = 'matched'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Matched {seeker.name} with {helper.name}',
            'match':   match.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ── POST /api/admin/approve-helper ──────────────────────────

@admin_bp.route('/approve-helper', methods=['POST'])
def approve_helper():
    """
    Approves a helper who is in 'pending_approval' status.
    Once approved they appear in the matching pool.
    Expects JSON: { "helper_id": 3 }
    """
    data = request.get_json(silent=True)
    if not data or not data.get('helper_id'):
        return jsonify({'success': False, 'error': 'helper_id is required'}), 400

    helper = Helper.query.get(data['helper_id'])
    if not helper:
        return jsonify({'success': False, 'error': 'Helper not found'}), 404

    if helper.status != 'pending_approval':
        return jsonify({
            'success': False,
            'error':   f'Helper status is already "{helper.status}" — only pending_approval helpers can be approved'
        }), 409

    try:
        helper.status = 'approved'
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'{helper.name} has been approved and added to the matching pool',
            'helper':  helper.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ── POST /api/admin/unmatch ──────────────────────────────────

@admin_bp.route('/unmatch', methods=['POST'])
def unmatch():
    """
    Removes a confirmed match and sets both seeker and helper
    back to their previous available status.
    Expects JSON: { "match_id": 5 }
    """
    data = request.get_json(silent=True)
    if not data or not data.get('match_id'):
        return jsonify({'success': False, 'error': 'match_id is required'}), 400

    match = Match.query.get(data['match_id'])
    if not match:
        return jsonify({'success': False, 'error': 'Match not found'}), 404

    try:
        seeker = Seeker.query.get(match.seeker_id)
        helper = Helper.query.get(match.helper_id)

        if seeker: seeker.status = 'approved'
        if helper: helper.status = 'approved'

        db.session.delete(match)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Match cancelled. Both seeker and helper are back in the pool.'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ── GET /api/admin/matches ───────────────────────────────────

@admin_bp.route('/matches', methods=['GET'])
def get_matches():
    """
    Returns all confirmed matches for the dashboard
    matches panel. Excludes cancelled matches by default.
    """
    matches = Match.query.filter(
        Match.status != 'cancelled'
    ).order_by(Match.matched_at.desc()).all()

    return jsonify({
        'success': True,
        'matches': [m.to_dict() for m in matches],
        'count':   len(matches)
    }), 200
