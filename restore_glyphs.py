import os

BASE = r"C:\Users\yasha\waybuddy-deploy\static"

# Seeker form: restore airplane (U+2708) in .form-hero::before
seeker_path = os.path.join(BASE, "seeker-form.html")
with open(seeker_path, "rb") as f:
    content = f.read()

# After the fix script ran, the content property now has empty quotes: content: '';
# We replace it with the CSS unicode escape for airplane: \2708
old = b"content: '';"
new_seeker = b"content: '\\2708';"

count = content.count(old)
print(f"seeker-form.html: found {count} occurrence(s) of empty content property")

if count >= 1:
    content = content.replace(old, new_seeker, 1)
    with open(seeker_path, "wb") as f:
        f.write(content)
    print("seeker-form.html: airplane restored")
else:
    print("seeker-form.html: pattern not found - checking what's there...")
    idx = content.find(b"form-hero::before")
    print(repr(content[idx:idx+100]))

# Helper form: restore handshake (U+1F91D) in .form-hero::before
helper_path = os.path.join(BASE, "helper-form.html")
with open(helper_path, "rb") as f:
    content = f.read()

new_helper = b"content: '\\1F91D';"

count = content.count(old)
print(f"\nhelper-form.html: found {count} occurrence(s) of empty content property")

if count >= 1:
    content = content.replace(old, new_helper, 1)
    with open(helper_path, "wb") as f:
        f.write(content)
    print("helper-form.html: handshake restored")
else:
    print("helper-form.html: pattern not found - checking what's there...")
    idx = content.find(b"form-hero::before")
    print(repr(content[idx:idx+100]))

print("\nDone.")
