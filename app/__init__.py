import os
from flask import Flask
from flask_cors import CORS
from .models import db


def create_app():
    app = Flask(__name__)

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

    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'waybuddy-api'}, 200

    return app
