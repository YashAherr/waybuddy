import os, re

path = r"C:\Users\yasha\waybuddy-deploy\static\helper-form.html"
with open(path, "rb") as f:
    content = f.read()
text = content.decode("utf-8", errors="replace")

# Remove any existing hero-glyph CSS and span from previous attempts
text = re.sub(r"\s*\/\* Decorative background glyph[^}]+\}", "", text, flags=re.DOTALL)
text = re.sub(r"\s*\.hero-glyph \{[^}]+\}", "", text)
text = re.sub(r'<span class="hero-glyph"[^>]*>.*?</span>', "", text)
print("Cleared previous hero-glyph attempts")

# Clear the ::before content (whatever garbled bytes are there)
text = re.sub(
    r"(\.form-hero::before \{[^}]*content:\s*')[^']*(')",
    r"\1\2", text, count=1
)
print("Cleared ::before content")

# Add CSS for the span — same position as airplane, opacity tuned for green bg
glyph_css = """
    /* Decorative glyph — matches airplane position in seeker form */
    .hero-glyph {
      position: absolute;
      font-size: 12rem;
      opacity: 0.12;
      top: -2rem;
      right: -2rem;
      line-height: 1;
      pointer-events: none;
      user-select: none;
      filter: grayscale(1) brightness(0.45);
    }
"""
text = text.replace("</style>", glyph_css + "  </style>", 1)
print("Added hero-glyph CSS")

# Add handshake span inside form-hero div
old_hero = '<div class="form-hero">'
new_hero = '<div class="form-hero"><span class="hero-glyph" aria-hidden="true">&#x1F91D;</span>'
if old_hero in text:
    text = text.replace(old_hero, new_hero, 1)
    print("Added handshake span")
else:
    print("WARNING: form-hero div not found")

# Fix Back to home corruption
text = re.sub(r'class="back-link">[^B]*Back to home', 'class="back-link">Back to home', text)
print("Fixed Back to home link")

# Fix em dash in error messages
text = re.sub(r'real email address [^\w]*temporary', 'real email address - temporary', text)
print("Fixed em dash")

with open(path, "wb") as f:
    f.write(text.encode("utf-8"))
print("\nDone. Run: git add . && git commit -m 'Restore helper glyph' && git push origin main")
