$ErrorActionPreference = 'Stop'
$root = 'C:\Users\yasha\waybuddy-deploy'

Write-Host "WayBuddy — Validation update" -ForegroundColor Cyan
Write-Host "Root: $root"
Write-Host ""

# ── STEP 1: requirements.txt ───────────────────────────────────────────────────
$reqPath = Join-Path $root 'requirements.txt'
$req = Get-Content $reqPath -Raw
$added = @()
foreach ($pkg in @('email-validator', 'phonenumbers')) {
    if ($req -notmatch [regex]::Escape($pkg)) {
        $req = $req.TrimEnd("`r`n") + "`n$pkg`n"
        $added += $pkg
    }
}
[System.IO.File]::WriteAllText($reqPath, $req, (New-Object System.Text.UTF8Encoding($false)))
if ($added.Count -gt 0) { Write-Host "requirements.txt  → added: $($added -join ', ')" -ForegroundColor Green }
else                     { Write-Host "requirements.txt  → already up to date" -ForegroundColor Yellow }

# ── STEP 2: app/utils/validation.py (new file) ────────────────────────────────
$utilsDir = Join-Path $root 'app\utils'
if (-not (Test-Path $utilsDir)) { New-Item -ItemType Directory -Path $utilsDir | Out-Null }

$initPath = Join-Path $utilsDir '__init__.py'
if (-not (Test-Path $initPath)) {
    [System.IO.File]::WriteAllText($initPath, '', (New-Object System.Text.UTF8Encoding($false)))
}

$validationPy = @'
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
    Email is optional on both forms — pass empty string to skip.
    """
    if not email:
        return True, None
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, 'Please enter a valid email address.'
    domain = email.split('@')[1].lower()
    if domain in DISPOSABLE_DOMAINS:
        return False, 'Please use a real email address — temporary/disposable emails are not allowed.'
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
'@

$valPath = Join-Path $utilsDir 'validation.py'
[System.IO.File]::WriteAllText($valPath, $validationPy.Replace("`r`n", "`n"), (New-Object System.Text.UTF8Encoding($false)))
Write-Host "app/utils/validation.py → created" -ForegroundColor Green

# ── STEP 3: app/routes/register.py ────────────────────────────────────────────
$regPath = Join-Path $root 'app\routes\register.py'
$reg = Get-Content $regPath -Raw

# 3a: Add import at top (after existing imports)
$importFind    = 'from flask import'
$importReplace = "from app.utils.validation import validate_indian_phone, validate_email, check_duplicate`nfrom flask import"
if ($reg -notmatch 'from app\.utils\.validation import') {
    $reg = $reg.Replace($importFind, $importReplace)
    Write-Host "register.py       → added validation import" -ForegroundColor Green
} else {
    Write-Host "register.py       → import already present" -ForegroundColor Yellow
}

# 3b: Seeker route — inject validation block after data extraction
# We look for the line that reads data from request.json and inject after it
$seekerFind = "data = request.get_json()"
$seekerInject = @'
data = request.get_json()

        # ── HONEYPOT (bot trap) ────────────────────────────────────
        if data.get('website'):
            return jsonify({'success': False, 'error': 'Registration failed.'}), 400

        # ── PHONE VALIDATION ───────────────────────────────────────
        phone_raw = (data.get('phone') or '').strip()
        phone, phone_err = validate_indian_phone(phone_raw)
        if phone_err:
            return jsonify({'success': False, 'error': phone_err}), 422

        # ── EMAIL VALIDATION ───────────────────────────────────────
        email = (data.get('email') or '').strip().lower()
        email_ok, email_err = validate_email(email)
        if not email_ok:
            return jsonify({'success': False, 'error': email_err}), 422

        # ── DUPLICATE CHECK ────────────────────────────────────────
        from app.models import Seeker
        dup_err = check_duplicate(Seeker, db.session, phone, email or None)
        if dup_err:
            return jsonify({'success': False, 'error': dup_err}), 409

        # ── USE CLEANED VALUES ─────────────────────────────────────
        data['phone'] = phone
        data['email'] = email or None
'@

# Only inject if not already present
if ($reg -notmatch 'HONEYPOT \(bot trap\)') {
    # Replace only the FIRST occurrence (seeker route)
    $idx = $reg.IndexOf($seekerFind)
    if ($idx -ge 0) {
        $reg = $reg.Substring(0, $idx) + $seekerInject + $reg.Substring($idx + $seekerFind.Length)
        Write-Host "register.py       → seeker validation injected" -ForegroundColor Green
    } else {
        Write-Host "register.py       → WARNING: could not find seeker injection point" -ForegroundColor Red
    }
} else {
    Write-Host "register.py       → seeker validation already present" -ForegroundColor Yellow
}

# 3c: Helper route — same pattern but only inject ONCE more (second occurrence of get_json)
$helperInject = @'

        # ── HONEYPOT ────────────────────────────────────────────────
        if data.get('website'):
            return jsonify({'success': False, 'error': 'Registration failed.'}), 400

        # ── PHONE VALIDATION ────────────────────────────────────────
        phone_raw = (data.get('phone') or '').strip()
        phone, phone_err = validate_indian_phone(phone_raw)
        if phone_err:
            return jsonify({'success': False, 'error': phone_err}), 422

        # ── EMAIL VALIDATION ────────────────────────────────────────
        email = (data.get('email') or '').strip().lower()
        email_ok, email_err = validate_email(email)
        if not email_ok:
            return jsonify({'success': False, 'error': email_err}), 422

        # ── DUPLICATE CHECK ─────────────────────────────────────────
        from app.models import Helper
        dup_err = check_duplicate(Helper, db.session, phone, email or None)
        if dup_err:
            return jsonify({'success': False, 'error': dup_err}), 409

        # ── USE CLEANED VALUES ───────────────────────────────────────
        data['phone'] = phone
        data['email'] = email or None
'@

if ($reg -notmatch 'DUPLICATE CHECK.*Helper' -and $reg -notmatch 'Helper.*DUPLICATE CHECK') {
    # Find second occurrence of get_json (helper route)
    $firstIdx  = $reg.IndexOf($seekerFind)
    $secondIdx = $reg.IndexOf($seekerFind, $firstIdx + $seekerFind.Length)
    if ($secondIdx -ge 0) {
        $insertAt = $secondIdx + $seekerFind.Length
        $reg = $reg.Substring(0, $insertAt) + $helperInject + $reg.Substring($insertAt)
        Write-Host "register.py       → helper validation injected" -ForegroundColor Green
    } else {
        Write-Host "register.py       → WARNING: could not find helper injection point" -ForegroundColor Red
    }
} else {
    Write-Host "register.py       → helper validation already present" -ForegroundColor Yellow
}

[System.IO.File]::WriteAllText($regPath, $reg, (New-Object System.Text.UTF8Encoding($false)))

# ── STEP 4: seeker-form.html ──────────────────────────────────────────────────
$seekerHtml = Join-Path $root 'static\seeker-form.html'
$sh = Get-Content $seekerHtml -Raw

# 4a: Add pattern + autocomplete to phone input
$oldPhoneInput = '<input type="tel" id="phone" name="phone" placeholder="+91 98765 43210" required/>'
$newPhoneInput = '<input type="tel" id="phone" name="phone" placeholder="+91 98765 43210" pattern="[+0-9\s\-]{10,15}" autocomplete="tel" required/>'
if ($sh -notmatch 'pattern="\[' -and $sh -match [regex]::Escape($oldPhoneInput)) {
    $sh = $sh.Replace($oldPhoneInput, $newPhoneInput)
    Write-Host "seeker-form.html  → phone input updated" -ForegroundColor Green
}

# 4b: Add hint text after phone input
$oldPhoneField = '<input type="tel" id="phone" name="phone" placeholder="+91 98765 43210" pattern="[+0-9\s\-]{10,15}" autocomplete="tel" required/>'
$newPhoneField  = '<input type="tel" id="phone" name="phone" placeholder="+91 98765 43210" pattern="[+0-9\s\-]{10,15}" autocomplete="tel" required/>
        <span class="hint">Enter 10-digit Indian mobile number. e.g. 98765 43210 or +91 98765 43210</span>'
if ($sh -notmatch '10-digit Indian mobile' -and $sh -match [regex]::Escape($oldPhoneField)) {
    $sh = $sh.Replace($oldPhoneField, $newPhoneField)
    Write-Host "seeker-form.html  → phone hint added" -ForegroundColor Green
}

# 4c: Add honeypot field before </form> (after last real field, before submit button)
$oldSubmitArea = '<div class="submit-area">'
$newSubmitArea = '<input type="text" name="website" id="website" style="display:none;position:absolute;left:-9999px" tabindex="-1" autocomplete="off" aria-hidden="true">
    <div class="submit-area">'
if ($sh -notmatch 'name="website"' -and $sh -match [regex]::Escape($oldSubmitArea)) {
    # Replace only first occurrence (inside the form)
    $idx = $sh.IndexOf($oldSubmitArea)
    $sh = $sh.Substring(0, $idx) + $newSubmitArea + $sh.Substring($idx + $oldSubmitArea.Length)
    Write-Host "seeker-form.html  → honeypot added" -ForegroundColor Green
}

# 4d: Add client-side phone + email validation before the server submit
$oldValidation = "const required = ['name','phone','age','flight_number','departure_airport','arrival_airport','travel_date'];"
$newValidation = @"
// ── PHONE FORMAT VALIDATION ──────────────────────────────────
    const phoneRaw = data.phone.replace(/[\s\-\(\)]/g, '');
    const phoneDigits = phoneRaw.startsWith('+91') ? phoneRaw.slice(3)
                      : phoneRaw.startsWith('91') && phoneRaw.length === 12 ? phoneRaw.slice(2)
                      : phoneRaw.startsWith('0') && phoneRaw.length === 11  ? phoneRaw.slice(1)
                      : phoneRaw;
    if (!/^[6-9]\d{9}$/.test(phoneDigits)) {
      banner.className = 'banner error';
      banner.textContent = 'Please enter a valid 10-digit Indian mobile number (starting with 6-9).';
      banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    // ── EMAIL FORMAT VALIDATION (optional field) ─────────────
    if (data.email) {
      const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(data.email);
      if (!emailOk) {
        banner.className = 'banner error';
        banner.textContent = 'Please enter a valid email address.';
        banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
    }

    const required = ['name','phone','age','flight_number','departure_airport','arrival_airport','travel_date'];
"@
if ($sh -notmatch 'PHONE FORMAT VALIDATION' -and $sh -match [regex]::Escape($oldValidation)) {
    $sh = $sh.Replace($oldValidation, $newValidation)
    Write-Host "seeker-form.html  → JS validation added" -ForegroundColor Green
}

[System.IO.File]::WriteAllText($seekerHtml, $sh, (New-Object System.Text.UTF8Encoding($false)))

# ── STEP 5: helper-form.html ──────────────────────────────────────────────────
$helperHtml = Join-Path $root 'static\helper-form.html'
$hh = Get-Content $helperHtml -Raw

# 5a: Phone input update
$oldHPhone = '<input type="tel" id="phone" name="phone" placeholder="+91 98765 43210" required/>'
$newHPhone = '<input type="tel" id="phone" name="phone" placeholder="+91 98765 43210" pattern="[+0-9\s\-]{10,15}" autocomplete="tel" required/>
        <span class="hint">Enter 10-digit Indian mobile number. e.g. 98765 43210 or +91 98765 43210</span>'
if ($hh -notmatch '10-digit Indian mobile' -and $hh -match [regex]::Escape($oldHPhone)) {
    $hh = $hh.Replace($oldHPhone, $newHPhone)
    Write-Host "helper-form.html  → phone input updated + hint added" -ForegroundColor Green
}

# 5b: Honeypot before submit button
$oldHSubmit = '<div class="submit-area">'
$newHSubmit = '<input type="text" name="website" id="website" style="display:none;position:absolute;left:-9999px" tabindex="-1" autocomplete="off" aria-hidden="true">
    <div class="submit-area">'
if ($hh -notmatch 'name="website"' -and $hh -match [regex]::Escape($oldHSubmit)) {
    $idx = $hh.IndexOf($oldHSubmit)
    $hh = $hh.Substring(0, $idx) + $newHSubmit + $hh.Substring($idx + $oldHSubmit.Length)
    Write-Host "helper-form.html  → honeypot added" -ForegroundColor Green
}

# 5c: JS validation in helper form
$oldHValidation = "const required = ['name', 'phone', 'age', 'based_at_airport'];"
$newHValidation = @"
// ── PHONE FORMAT VALIDATION ──────────────────────────────────
    const phoneRaw = data.phone.replace(/[\s\-\(\)]/g, '');
    const phoneDigits = phoneRaw.startsWith('+91') ? phoneRaw.slice(3)
                      : phoneRaw.startsWith('91') && phoneRaw.length === 12 ? phoneRaw.slice(2)
                      : phoneRaw.startsWith('0') && phoneRaw.length === 11  ? phoneRaw.slice(1)
                      : phoneRaw;
    if (!/^[6-9]\d{9}$/.test(phoneDigits)) {
      banner.className = 'banner error';
      banner.textContent = 'Please enter a valid 10-digit Indian mobile number (starting with 6-9).';
      banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    // ── EMAIL FORMAT VALIDATION (optional field) ─────────────
    if (data.email) {
      const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(data.email);
      if (!emailOk) {
        banner.className = 'banner error';
        banner.textContent = 'Please enter a valid email address.';
        banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
    }

    const required = ['name', 'phone', 'age', 'based_at_airport'];
"@
if ($hh -notmatch 'PHONE FORMAT VALIDATION' -and $hh -match [regex]::Escape($oldHValidation)) {
    $hh = $hh.Replace($oldHValidation, $newHValidation)
    Write-Host "helper-form.html  → JS validation added" -ForegroundColor Green
}

[System.IO.File]::WriteAllText($helperHtml, $hh, (New-Object System.Text.UTF8Encoding($false)))

# ── DONE ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "All changes applied. Now:" -ForegroundColor Cyan
Write-Host "  git add ."
Write-Host "  git commit -m 'Add phone/email validation, duplicate check, honeypot'"
Write-Host "  git push origin main"
Write-Host ""
Write-Host "NOTE: register.py changes assume 'data = request.get_json()' appears" -ForegroundColor Yellow
Write-Host "      once per route (seeker, helper). If you see yellow warnings above," -ForegroundColor Yellow
Write-Host "      paste the register.py content here and I will fix it manually." -ForegroundColor Yellow
