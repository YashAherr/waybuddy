import os
from flask import Flask, send_from_directory, redirect, request, session, jsonify
from flask_cors import CORS
from .models import db


def create_app():
    app = Flask(__name__,
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'),
                static_url_path='')

    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise RuntimeError('DATABASE_URL environment variable is not set.')

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

    CORS(app)
    db.init_app(app)

    from .routes.register import register_bp
    from .routes.admin import admin_bp
    from .routes.notify import notify_bp

    app.register_blueprint(register_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(notify_bp, url_prefix='/api')

    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'changeme')

    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'waybuddy-api'}, 200

    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    @app.route('/index.html')
    def index_redirect():
        return redirect('/', 301)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            data = request.get_json()
            if data and data.get('username') == ADMIN_USERNAME and data.get('password') == ADMIN_PASSWORD:
                session['admin'] = True
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        return send_from_directory(app.static_folder, 'login.html')

    @app.route('/logout')
    def logout():
        session.pop('admin', None)
        return redirect('/login')

    @app.route('/dashboard')
    def dashboard():
        if not session.get('admin'):
            return redirect('/login')
        return send_from_directory(app.static_folder, 'dashboard.html')

    @app.route('/dashboard.html')
    def dashboard_redirect():
        return redirect('/dashboard', 301)

    @app.route('/seeker-form')
    def seeker_form():
        return send_from_directory(app.static_folder, 'seeker-form.html')

    @app.route('/seeker-form.html')
    def seeker_form_redirect():
        return redirect('/seeker-form', 301)

    @app.route('/helper-form')
    def helper_form():
        return send_from_directory(app.static_folder, 'helper-form.html')

    @app.route('/helper-form.html')
    def helper_form_redirect():
        return redirect('/helper-form', 301)

    return app