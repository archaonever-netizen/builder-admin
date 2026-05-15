import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from config import Config
from supabase import create_client, Client

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    supabase: Client = create_client(app.config['SUPABASE_URL'], app.config['SUPABASE_SERVICE_ROLE_KEY'])
    app.supabase = supabase

    @app.route('/')
    def role_selection():
        return render_template('index.html')

    # Регистрируем blueprint администратора (существующий)
    from app.admin.routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Регистрируем blueprint менеджера (НОВЫЙ)
    from app.manager.routes import manager_bp
    app.register_blueprint(manager_bp, url_prefix='/manager')

    with app.app_context():
        from app.models import Developer, Draft, ResidentialComplex, Contact, Document, Regulation
        from app.models import Agent, Employee, Presentation   # <-- новые модели
        db.create_all()

    return app
