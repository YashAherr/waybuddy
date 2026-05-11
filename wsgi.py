# app.py
# ============================================================
#  WayBuddy — Application Entry Point
#
#  This is the file that starts the Flask server.
#  It imports the application factory from app/__init__.py
#  and runs it.
#
#  Development:  python app.py
#  Production:   gunicorn runs this via the Dockerfile
# ============================================================

from app import create_app

flask_app = create_app()

if __name__ == '__main__':
    # debug=False in production — Dockerfile sets FLASK_ENV
    flask_app.run(
        host='0.0.0.0',   # listen on all network interfaces
        port=5000,
        debug=False
    )
