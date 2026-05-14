from app import db
from datetime import datetime
import uuid

class Developer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    complexes = db.relationship('ResidentialComplex', backref='developer', lazy=True, cascade="all, delete-orphan")
    contacts = db.relationship('Contact', backref='developer', lazy=True, cascade="all, delete-orphan")
    documents = db.relationship('Document', backref='developer', lazy=True, cascade="all, delete-orphan")
    regulation = db.relationship('Regulation', backref='developer', uselist=False, cascade="all, delete-orphan")
    channels = db.Column(db.Text)
    chessboard_link = db.Column(db.String(500))
    feed = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ResidentialComplex(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    commission = db.Column(db.String(100))
    contact_person = db.Column(db.String(200))
    developer_id = db.Column(db.Integer, db.ForeignKey('developer.id'))

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_type = db.Column(db.String(50))
    name = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    developer_id = db.Column(db.Integer, db.ForeignKey('developer.id'))

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300))          # UUID или идентификатор в Supabase
    original_filename = db.Column(db.String(300)) # Оригинальное имя файла
    filepath = db.Column(db.String(500))          # Публичная ссылка
    doc_type = db.Column(db.String(50))
    developer_id = db.Column(db.Integer, db.ForeignKey('developer.id'))

class Regulation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.JSON)
    raw_text = db.Column(db.Text)
    developer_id = db.Column(db.Integer, db.ForeignKey('developer.id'), unique=True)

class Draft(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    data = db.Column(db.JSON)
    session_token = db.Column(db.String(100), index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
