# Dockerfile
# ============================================================
#  WayBuddy — Docker Image
#
#  Builds a container image that runs the Flask app using
#  Gunicorn as the production WSGI server.
#
#  Gunicorn is a production-grade server that runs multiple
#  worker processes to handle concurrent requests. Flask's
#  built-in development server (flask run) is single-threaded
#  and not suitable for production use.
#
#  Build:  docker build -t waybuddy-api .
#  Run:    docker run -p 5000:5000 --env-file .env waybuddy-api
# ============================================================

# ── BASE IMAGE ───────────────────────────────────────────────
# python:3.11-slim is a minimal Python image. The 'slim'
# variant excludes build tools and documentation, keeping
# the final image small (~150MB vs ~900MB for the full image).
FROM python:3.11-slim

# ── WORKING DIRECTORY ────────────────────────────────────────
# All subsequent commands run from this directory inside the
# container. Creates the directory if it doesn't exist.
WORKDIR /waybuddy

# ── INSTALL DEPENDENCIES ─────────────────────────────────────
# Copy requirements.txt first (before the rest of the code).
# Docker caches each step — if requirements.txt hasn't changed,
# Docker reuses the cached pip install layer and skips it.
# This makes rebuilds much faster during development.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── COPY APPLICATION CODE ────────────────────────────────────
COPY app/     ./app/
COPY wsgi.py   .

# ── PORT ─────────────────────────────────────────────────────
# Documents that the container listens on port 5000.
# Does not actually publish the port — that's done with -p
# when running the container.
EXPOSE 5000

# ── START COMMAND ────────────────────────────────────────────
# Gunicorn starts the Flask app with 3 worker processes.
# Format: gunicorn module:variable
#   app       = the app.py file
#   flask_app = the variable name inside app.py
CMD ["gunicorn", "--workers=3", "--bind=0.0.0.0:5000", "wsgi:flask_app"]
