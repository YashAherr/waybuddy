import re

DISPOSABLE_DOMAINS = {
    'mailinator.com', '10minutemail.com', 'guerrillamail.com',
    'throwam.com', 'yopmail.com', 'trashmail.com', 'fakeinbox.com',
    'maildrop.cc', 'dispostable.com', 'tempmail.com', 'getnada.com',
    'sharklasers.com', 'guerrillamailblock.com', 'grr.la',
}

def validate_indian_phone(raw):
    """
    Accepts: +919876543210, 09876543210, 9876543210, 98765 43210
    Returns: (cleaned_10_digit_string, None) on success
             (None, error_message) on failure
    """
    if not raw:
        return None, 'Phone number is required.'
    digits = re.sub(r'[\s\-\(\)]', '', raw)
    if digits.startswith('+91'):
        digits = digits[3:]
    elif digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith('0') and len(digits) == 11:
        digits = digits[1:]
    if not re.fullmatch(r'[6-9]\d{9}', digits):
        return None, 'Please enter a valid 10-digit Indian mobile number (starting with 6-9).'
    return digits, None

def validate_email(email):
    """
    Returns: (True, None) on success
             (False, error_message) on failure
    Email is optional on both forms â€” pass empty string to skip.
    """
    if not email:
        return True, None
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, 'Please enter a valid email address.'
    domain = email.split('@')[1].lower()
    if domain in DISPOSABLE_DOMAINS:
        return False, 'Please use a real email address â€” temporary or disposable emails are not allowed.'
    return True, None

def check_duplicate(model, db_session, phone, email):
    """
    Check if an active registration already exists for this phone or email.
    Active = status is 'approved' or 'matched' (not cancelled or old completed trips).
    Returns error message string, or None if no duplicate found.
    """
    active_statuses = ('approved', 'matched')
    if phone:
        existing = db_session.query(model).filter(
            model.phone == phone,
            model.status.in_(active_statuses)
        ).first()
        if existing:
            return 'An active registration already exists for this phone number. Contact us if you need to update your details.'
    if email:
        existing = db_session.query(model).filter(
            model.email == email,
            model.status.in_(active_statuses)
        ).first()
        if existing:
            return 'An active registration already exists for this email address. Contact us if you need to update your details.'
    return None