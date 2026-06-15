import os

BASE = r"C:\Users\yasha\waybuddy-deploy\static"
files = {
    "seeker-form.html": os.path.join(BASE, "seeker-form.html"),
    "helper-form.html": os.path.join(BASE, "helper-form.html"),
}

# Each tuple: (corrupted_bytes, replacement_bytes, description)
# These cover all the corruption patterns visible in the screenshots:
# - em dash (U+2014, UTF-8: E2 80 94) corrupted through double-encoding
# - right arrow emoji (U+27A1, UTF-8: E2 9E A1) corrupted
# - airplane emoji (U+2708, UTF-8: E2 9C 88) corrupted
# - plane/flight emoji variants
# - checkmark emoji (U+2705, UTF-8: E2 9C 85) - already fixed but kept for safety

FIXES = [
    # ── em dash variants ──────────────────────────────────────────────────
    # Original: U+2014 em dash, UTF-8: E2 80 94
    # After double-encoding through Windows-1252: C3 A2 E2 80 9C / variants
    (bytes([0xc3, 0xa2, 0xe2, 0x80, 0x9c, 0xc2, 0x94]), b"&mdash;", "em dash variant 1"),
    (bytes([0xc3, 0xa2, 0xc2, 0x80, 0xc2, 0x94]),        b"&mdash;", "em dash variant 2"),
    (bytes([0xe2, 0x80, 0x94]),                           b"&mdash;", "em dash plain UTF-8"),

    # ── right arrow emoji (used in submit button) ─────────────────────────
    # U+27A1 = E2 9E A1
    (bytes([0xc3, 0xa2, 0xc5, 0x93, 0xc2, 0xa1]),        b"&rarr;",  "right arrow variant 1"),
    (bytes([0xe2, 0x9e, 0xa1]),                           b"&rarr;",  "right arrow plain"),

    # ── airplane emoji (U+2708 = E2 9C 88) ───────────────────────────────
    (bytes([0xc3, 0xa2, 0xc5, 0x93, 0xe2, 0x80, 0x8b]),    b"",        "airplane variant 1"),
    (bytes([0xe2, 0x9c, 0x88]),                           b"",        "airplane plain"),

    # ── generic â œ pattern (covers hero section emoji) ───────────────────
    # The large background glyphs in images 5 and 6 are likely decorative
    # emoji rendered as background content in a CSS ::before or a div.
    # We'll catch all remaining high-byte sequences with the scan below.
]

# Actually, let's do this properly: scan first, then fix specifically.
print("=" * 60)
print("SCAN — finding all non-ASCII byte sequences")
print("=" * 60)

all_sequences = {}  # file -> list of (pos, hex, context_repr)

for fname, fpath in files.items():
    with open(fpath, "rb") as f:
        content = f.read()

    sequences = []
    i = 0
    while i < len(content):
        if content[i] > 127:
            start = i
            while i < len(content) and content[i] > 127:
                i += 1
            seq = content[start:i]
            ctx = content[max(0, start - 40):i + 40]
            sequences.append((start, seq, ctx))
        else:
            i += 1

    all_sequences[fname] = (content, sequences)
    print(f"\n{fname}: {len(sequences)} non-ASCII sequences found")
    for pos, seq, ctx in sequences:
        print(f"  pos={pos:5d}  bytes={seq.hex()!r:30s}  ctx={repr(ctx)}")

print("\n" + "=" * 60)
print("FIX — replacing all non-ASCII sequences")
print("=" * 60)

# Build a comprehensive replacement map from the scan results
# Maps: bytes_sequence -> replacement
# We'll replace:
#   - Anything that looks like a corrupted em dash -> &mdash;
#   - Anything that looks like a corrupted arrow   -> &rarr;
#   - Any remaining decorative emoji sequences     -> '' (remove)

def classify_and_fix(seq_bytes):
    h = seq_bytes.hex()
    # em dash signatures
    if h in ('e2809e', 'c3a2e2809c', 'c3a2c280c294', 'e28094',
              'c3a2e2809494', 'c3a2e280', 'c280c294'):
        return b"&mdash;"
    # right arrow / forward arrow
    if h in ('e29ea1', 'c3a2c593c2a1', 'e28692', 'c3a2e2869221'):
        return b"&rarr;"
    # airplane / flight emoji
    if h in ('e29c88', 'c3a2c593e2808b', 'e28c88'):
        return b""
    # checkmark (already handled but just in case)
    if h in ('e29c85', 'c3a2c593e28085'):
        return b"&#10003;"
    # Any other non-ASCII: remove it (it's decorative)
    return b""

for fname, fpath in files.items():
    content, sequences = all_sequences[fname]
    if not sequences:
        print(f"{fname}: nothing to fix")
        continue

    # Build sorted list of (start, end, replacement) — process in reverse to preserve positions
    patches = []
    for pos, seq, ctx in sequences:
        repl = classify_and_fix(seq)
        patches.append((pos, pos + len(seq), repl))

    # Apply patches in reverse order
    content_bytearray = bytearray(content)
    for start, end, repl in sorted(patches, reverse=True):
        content_bytearray[start:end] = repl

    with open(fpath, "wb") as f:
        f.write(bytes(content_bytearray))

    print(f"{fname}: fixed {len(patches)} sequences")

print("\nDone. Run git add / commit / push to deploy.")
