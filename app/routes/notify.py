# app/routes/notify.py
# ============================================================
#  WayBuddy — Notification Route
#
#  Sends match confirmation emails to both the seeker and
#  helper after an admin confirms a match.
#
#  Endpoint:
#    POST /api/notify/match   — send emails to matched pair
#
#  Email is sent via SMTP. Configure these environment
#  variables on EC2:
#    SMTP_HOST     — e.g. smtp.gmail.com
#    SMTP_PORT     — e.g. 587
#    SMTP_USER     — your sending email address
#    SMTP_PASSWORD — your email password or app password
#    SMTP_FROM     — display name + address, e.g. WayBuddy <hello@waybuddy.in>
#
#  Gmail note: use an App Password, not your account password.
#  Generate one at myaccount.google.com/apppasswords
# ============================================================

import os
import smtplib
from email.mime.text      import MIMEText
from email.mime.multipart import MIMEMultipart
from flask                import Blueprint, request, jsonify
from ..models             import db, Match
from datetime             import datetime, timezone

notify_bp = Blueprint('notify', __name__)


# ── EMAIL HELPER ────────────────────────────────────────────

def send_email(to_address, subject, body_text, body_html=None):
    """
    Sends a single email via SMTP.
    Reads credentials from environment variables.
    Returns (True, None) on success or (False, error_message) on failure.
    """
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASSWORD')
    smtp_from = os.environ.get('SMTP_FROM', smtp_user)

    if not smtp_user or not smtp_pass:
        return False, 'SMTP_USER and SMTP_PASSWORD environment variables are not set'

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = smtp_from
    msg['To']      = to_address

    msg.attach(MIMEText(body_text, 'plain'))
    if body_html:
        msg.attach(MIMEText(body_html, 'html'))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, to_address, msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)


# ── EMAIL TEMPLATES ─────────────────────────────────────────

def seeker_email(seeker, helper):
    subject = f"WayBuddy — You have been matched with {helper.name}"

    text = f"""
Hi {seeker.name},

Great news! We have matched you with a volunteer helper for your upcoming trip.

YOUR HELPER
-----------
Name:    {helper.name}
Phone:   {helper.phone}
Email:   {helper.email or 'Not provided'}
Skills:  {helper.skills or 'General assistance'}

YOUR FLIGHT
-----------
Flight:  {seeker.flight_number}
Route:   {seeker.departure_airport} to {seeker.arrival_airport}
Date:    {seeker.travel_date}
Time:    {seeker.departure_time or 'Not specified'}

Please reach out to your helper at least 24 hours before your flight to
coordinate where and when to meet at the airport.

Safe travels,
The WayBuddy Team
"""

    html = f"""
<html><body style="font-family:Arial,sans-serif;color:#1a1a1a;max-width:560px;margin:0 auto;padding:24px">
<h2 style="color:#1A3E5C">You have been matched!</h2>
<p>Hi {seeker.name},</p>
<p>Great news — we have matched you with a volunteer helper for your upcoming trip.</p>

<h3 style="color:#2E7D9F">Your helper</h3>
<table style="border-collapse:collapse;width:100%">
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold;width:120px">Name</td><td style="padding:6px 12px">{helper.name}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Phone</td><td style="padding:6px 12px">{helper.phone}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Email</td><td style="padding:6px 12px">{helper.email or 'Not provided'}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Skills</td><td style="padding:6px 12px">{helper.skills or 'General assistance'}</td></tr>
</table>

<h3 style="color:#2E7D9F">Your flight</h3>
<table style="border-collapse:collapse;width:100%">
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold;width:120px">Flight</td><td style="padding:6px 12px">{seeker.flight_number}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Route</td><td style="padding:6px 12px">{seeker.departure_airport} → {seeker.arrival_airport}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Date</td><td style="padding:6px 12px">{seeker.travel_date}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Time</td><td style="padding:6px 12px">{seeker.departure_time or 'Not specified'}</td></tr>
</table>

<p style="margin-top:24px">Please reach out to your helper at least <strong>24 hours before your flight</strong> to coordinate where and when to meet.</p>
<p>Safe travels,<br><strong>The WayBuddy Team</strong></p>
</body></html>
"""
    return subject, text, html


def helper_email(helper, seeker):
    subject = f"WayBuddy — You have been matched with {seeker.name}"

    text = f"""
Hi {helper.name},

Thank you for volunteering. We have matched you with a solo traveller who needs your help.

THE TRAVELLER
-------------
Name:         {seeker.name}
Phone:        {seeker.phone}
Email:        {seeker.email or 'Not provided'}
Help needed:  {seeker.help_needed or 'General assistance'}
Notes:        {seeker.notes or 'None'}

THEIR FLIGHT
------------
Flight:  {seeker.flight_number}
Route:   {seeker.departure_airport} to {seeker.arrival_airport}
Date:    {seeker.travel_date}
Time:    {seeker.departure_time or 'Not specified'}

Please reach out to the traveller at least 24 hours before the flight to
agree on a meeting point at the airport.

Thank you for making travel easier for someone,
The WayBuddy Team
"""

    html = f"""
<html><body style="font-family:Arial,sans-serif;color:#1a1a1a;max-width:560px;margin:0 auto;padding:24px">
<h2 style="color:#1A3E5C">You have been matched with a traveller!</h2>
<p>Hi {helper.name},</p>
<p>Thank you for volunteering. Here are the details of the traveller who needs your help.</p>

<h3 style="color:#2E7D9F">The traveller</h3>
<table style="border-collapse:collapse;width:100%">
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold;width:140px">Name</td><td style="padding:6px 12px">{seeker.name}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Phone</td><td style="padding:6px 12px">{seeker.phone}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Email</td><td style="padding:6px 12px">{seeker.email or 'Not provided'}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Help needed</td><td style="padding:6px 12px">{seeker.help_needed or 'General assistance'}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Notes</td><td style="padding:6px 12px">{seeker.notes or 'None'}</td></tr>
</table>

<h3 style="color:#2E7D9F">Their flight</h3>
<table style="border-collapse:collapse;width:100%">
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold;width:140px">Flight</td><td style="padding:6px 12px">{seeker.flight_number}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Route</td><td style="padding:6px 12px">{seeker.departure_airport} → {seeker.arrival_airport}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Date</td><td style="padding:6px 12px">{seeker.travel_date}</td></tr>
  <tr><td style="padding:6px 12px;background:#EBF4FA;font-weight:bold">Time</td><td style="padding:6px 12px">{seeker.departure_time or 'Not specified'}</td></tr>
</table>

<p style="margin-top:24px">Please reach out to the traveller at least <strong>24 hours before the flight</strong> to agree on a meeting point.</p>
<p>Thank you for making travel easier for someone,<br><strong>The WayBuddy Team</strong></p>
</body></html>
"""
    return subject, text, html


# ── POST /api/notify/match ───────────────────────────────────

@notify_bp.route('/notify/match', methods=['POST'])
def notify_match():
    """
    Sends confirmation emails to both the seeker and helper
    for a given match. Called by the admin dashboard after
    confirming a match.
    Expects JSON: { "match_id": 5 }
    """
    data = request.get_json(silent=True)
    if not data or not data.get('match_id'):
        return jsonify({'success': False, 'error': 'match_id is required'}), 400

    match = Match.query.get(data['match_id'])
    if not match:
        return jsonify({'success': False, 'error': 'Match not found'}), 404

    seeker = match.seeker
    helper = match.helper

    results = {'seeker_email': None, 'helper_email': None, 'errors': []}

    # ── SEND TO SEEKER ───────────────────────────────────────
    if seeker.email:
        subject, text, html = seeker_email(seeker, helper)
        ok, err = send_email(seeker.email, subject, text, html)
        results['seeker_email'] = 'sent' if ok else f'failed: {err}'
        if not ok:
            results['errors'].append(f'Seeker email: {err}')
    else:
        results['seeker_email'] = 'skipped — no email address on file'

    # ── SEND TO HELPER ───────────────────────────────────────
    if helper.email:
        subject, text, html = helper_email(helper, seeker)
        ok, err = send_email(helper.email, subject, text, html)
        results['helper_email'] = 'sent' if ok else f'failed: {err}'
        if not ok:
            results['errors'].append(f'Helper email: {err}')
    else:
        results['helper_email'] = 'skipped — no email address on file'

    # ── UPDATE MATCH STATUS ──────────────────────────────────
    if not results['errors']:
        match.status      = 'notified'
        match.notified_at = datetime.now(timezone.utc)
        db.session.commit()

    return jsonify({
        'success': len(results['errors']) == 0,
        'results': results
    }), 200 if not results['errors'] else 207
