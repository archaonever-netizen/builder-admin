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
    chessboard_updated = db.Column(db.DateTime)
    feed = db.Column(db.Text)
    feed_updated = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ResidentialComplex(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    city = db.Column(db.String(200))
    region = db.Column(db.String(200))
    property_type = db.Column(db.String(200))
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
    filename = db.Column(db.String(300))
    original_filename = db.Column(db.String(300))
    filepath = db.Column(db.String(500))
    doc_type = db.Column(db.String(50))
    developer_id = db.Column(db.Integer, db.ForeignKey('developer.id'))

class Regulation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.JSON)
    raw_text = db.Column(db.Text)
    status = db.Column(db.String(50), default='')
    developer_id = db.Column(db.Integer, db.ForeignKey('developer.id'), unique=True)

class Draft(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    data = db.Column(db.JSON)
    session_token = db.Column(db.String(100), index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# =================== МОДЕЛИ МЕНЕДЖЕРА ===================
class Agent(db.Model):
    """Контрагент (агентство/агент)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)                 # Юридическое название
    director_name = db.Column(db.String(200))                        # ФИО директора
    director_phone = db.Column(db.String(50))                        # Телефон директора
    contact_name = db.Column(db.String(200))                         # ФИО контактного лица
    contact_phone = db.Column(db.String(50))                         # Телефон контактного лица
    messenger_linked = db.Column(db.Boolean, default=True)           # Мессенджер привязан к номеру?
    messenger_contact = db.Column(db.String(200))                    # Ссылка/номер, если не привязан
    website = db.Column(db.String(500))                              # Сайт
    active_agents_count = db.Column(db.Integer, default=0)           # Исходное количество (введённое)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employees = db.relationship('Employee', backref='agent', lazy=True, cascade="all, delete-orphan")
    presentations = db.relationship('Presentation', backref='agent', lazy=True, cascade="all, delete-orphan")

class Employee(db.Model):
    """Сотрудник агентства"""
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50))
    messenger = db.Column(db.String(200))                            # Идентификатор мессенджера
    fixations_count = db.Column(db.Integer, default=0)
    bookings_count = db.Column(db.Integer, default=0)
    deals_count = db.Column(db.Integer, default=0)
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'))

class Presentation(db.Model):
    """Презентации (заглушка под будущий блок)"""
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey('agent.id'))
    presentation_date = db.Column(db.Date)
    material = db.Column(db.String(500))                             # Ссылка или описание
