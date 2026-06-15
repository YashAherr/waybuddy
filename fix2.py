import os

BASE = r"C:\Users\yasha\waybuddy-deploy"

# ── Fix 1: Helper form handshake ─────────────────────────────────────────────
# U+1F91D is above BMP — CSS \1F91D doesn't work cross-browser.
# Use the HTML entity approach: put it directly in the HTML as &#x1F91D;
# by changing the CSS content property to use a data attribute trick,
# OR simplest: just swap the emoji for a pair of open hands U+1F450 (also 4-byte)
# Actually cleanest: use a different in-BMP symbol.
# Two-person silhouette U+1F465 also 4-byte. 
# Best option: use a simple heart U+2665 (in BMP, works perfectly in CSS)
# OR keep travel theme: use U+2764 (heavy heart) or U+1F46B via HTML not CSS.
#
# Decision: replace the CSS ::before approach with an actual HTML element
# so we can use &#x1F91D; as an HTML entity (HTML handles 4-byte emoji fine).
# We'll change .form-hero::before content to empty and add an HTML div instead.
#
# Simplest fix that preserves the visual: use U+2764 (heavy heart, in BMP)
# or U+1F500 (twisted arrows) — but to keep the handshake specifically,
# we put it in the HTML markup as &#x1F91D; rather than CSS content.

helper_path = os.path.join(BASE, r"static\helper-form.html")
with open(helper_path, "rb") as f:
    content = f.read()

# Replace the broken CSS unicode escape with empty (remove from CSS)
old_css = b"content: '\\1F91D';"
new_css = b"content: '';"
if old_css in content:
    content = content.replace(old_css, new_css, 1)
    print("helper-form.html: removed broken CSS emoji")
else:
    print("helper-form.html: CSS pattern not found, checking...")
    idx = content.find(b"form-hero::before")
    print(repr(content[idx:idx+100]))

# Add an HTML overlay div inside .form-hero that shows the handshake
# Find the opening .form-hero div and insert a span after it
old_hero = b'<div class="form-hero">'
new_hero = b'<div class="form-hero"><span class="hero-glyph" aria-hidden="true">&#x1F91D;</span>'
if old_hero in content:
    content = content.replace(old_hero, new_hero, 1)
    print("helper-form.html: added HTML handshake glyph")
else:
    print("helper-form.html: form-hero div not found")

# Add CSS for the hero-glyph span (insert before </style>)
old_style_end = b"</style>"
new_glyph_css = b"""    .hero-glyph {
      position: absolute;
      font-size: 12rem;
      opacity: 0.12;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      pointer-events: none;
      user-select: none;
      line-height: 1;
    }
</style>"""
if old_style_end in content:
    content = content.replace(old_style_end, new_glyph_css, 1)
    print("helper-form.html: added hero-glyph CSS")

with open(helper_path, "wb") as f:
    f.write(content)

# ── Fix 2: em dash in validation.py ──────────────────────────────────────────
val_path = os.path.join(BASE, r"app\utils\validation.py")
with open(val_path, "rb") as f:
    val = f.read()

# Find any em dash bytes (E2 80 94) or corrupted variants and replace with hyphen
emdash_utf8 = bytes([0xe2, 0x80, 0x94])
corrupted1   = bytes([0xc3, 0xa2, 0xe2, 0x80, 0x9c, 0xc2, 0x94])
corrupted2   = bytes([0xc3, 0xa2, 0xc2, 0x80, 0xc2, 0x94])

replaced = False
for pattern in [corrupted1, corrupted2, emdash_utf8]:
    if pattern in val:
        val = val.replace(pattern, b" - ")
        print(f"validation.py: replaced {pattern.hex()} with hyphen")
        replaced = True

# Also fix via string: find the message and replace inline
val_str = val.decode("utf-8", errors="replace")
targets = [
    ("temporary/disposable emails are not allowed", "temporary or disposable emails are not allowed"),
    ("\u2014", " - "),   # em dash character
    ("\u00e2\u0080\u0094", " - "),  # mojibake sequence as string
]
for old_s, new_s in targets:
    if old_s in val_str:
        val_str = val_str.replace(old_s, new_s)
        print(f"validation.py: fixed string: {repr(old_s)} -> {repr(new_s)}")
        replaced = True

if not replaced:
    print("validation.py: nothing to replace - checking the error message lines...")
    for line in val_str.split("\n"):
        if "temporary" in line or "disposable" in line or "real email" in line:
            print(f"  {repr(line)}")
else:
    with open(val_path, "wb") as f:
        f.write(val_str.encode("utf-8"))
    print("validation.py: saved")

print("\nAll done. Run: git add . && git commit -m 'Fix handshake glyph and em dash' && git push origin main")
