import json, os, uuid, threading
from flask import (render_template, request, jsonify, session, redirect, url_for, current_app)
from app import db
from app.admin import admin_bp
from app.models import Developer, ResidentialComplex, Contact, Document, Regulation, Draft
from app.ai_agent.agent import process_agency_agreement

# Главная страница
@admin_bp.route('/')
def index():
    developers = Developer.query.order_by(Developer.created_at.desc()).all()
    return render_template('admin/index.html', developers=developers)

# Добавление нового застройщика (GET/POST)
@admin_bp.route('/add', methods=['GET', 'POST'])
def add_developer():
    if 'draft_token' not in session:
        session['draft_token'] = str(uuid.uuid4())
    draft = Draft.query.filter_by(session_token=session['draft_token']).first()
    draft_data = draft.data if draft else {}
    return render_template('admin/add_developer.html', draft=draft_data)

# Черновики
@admin_bp.route('/api/draft', methods=['POST', 'GET'])
def draft_api():
    if 'draft_token' not in session:
        session['draft_token'] = str(uuid.uuid4())
    token = session['draft_token']
    if request.method == 'POST':
        data = request.get_json(force=True)
        draft = Draft.query.filter_by(session_token=token).first()
        if draft:
            draft.data = data
        else:
            draft = Draft(id=str(uuid.uuid4()), data=data, session_token=token)
            db.session.add(draft)
        db.session.commit()
        return jsonify({'status': 'ok'})
    else:
        draft = Draft.query.filter_by(session_token=token).first()
        return jsonify(draft.data if draft else {})

# Загрузка файла (с возвратом оригинального имени)
@admin_bp.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No filename'}), 400

    original_filename = file.filename
    file_extension = original_filename.rsplit('.', 1)[-1] if '.' in original_filename else ''
    unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())

    try:
        file_bytes = file.read()
        current_app.supabase.storage.from_('developer-docs').upload(
            unique_filename,
            file_bytes,
            {"content-type": file.content_type}
        )
        public_url = current_app.supabase.storage.from_('developer-docs').get_public_url(unique_filename)

        return jsonify({
            'id': unique_filename,
            'filename': original_filename,
            'path': public_url
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Завершение создания застройщика
@admin_bp.route('/submit', methods=['POST'])
def submit_developer():
    data = request.form.to_dict(flat=True)
    Draft.query.filter_by(session_token=session.get('draft_token')).delete()
    db.session.commit()

    dev = Developer(
        name=data.get('name'),
        channels=data.get('channels'),
        chessboard_link=data.get('chessboard_link'),
        feed=data.get('feed')
    )
    db.session.add(dev)
    db.session.flush()

    # ЖК
    complexes_json = data.get('complexes', '[]')
    try:
        complexes = json.loads(complexes_json)
        for comp in complexes:
            rc = ResidentialComplex(
                name=comp.get('name'),
                commission=comp.get('commission'),
                contact_person=comp.get('contact_person'),
                developer_id=dev.id
            )
            db.session.add(rc)
    except:
        pass

    # Контакты
    contacts_json = data.get('contacts', '[]')
    try:
        contacts = json.loads(contacts_json)
        for cont in contacts:
            c = Contact(
                contact_type=cont.get('type'),
                name=cont.get('name'),
                phone=cont.get('phone'),
                email=cont.get('email'),
                developer_id=dev.id
            )
            db.session.add(c)
    except:
        pass

    # Документы (теперь с оригинальными именами)
    doc_ids = request.form.getlist('doc_ids[]')
    doc_names = request.form.getlist('doc_names[]')
    for i, doc_id in enumerate(doc_ids):
        public_url = current_app.supabase.storage.from_('developer-docs').get_public_url(doc_id)
        original_name = doc_names[i] if i < len(doc_names) else doc_id
        doc = Document(
            filename=doc_id,
            original_filename=original_name,
            filepath=public_url,
            doc_type='agency_contract',
            developer_id=dev.id
        )
        db.session.add(doc)
    db.session.commit()

    # Запуск ИИ, если нет регламента и есть документ
    existing_regulation = Regulation.query.filter_by(developer_id=dev.id).first()
    agency_doc = Document.query.filter_by(developer_id=dev.id, doc_type='agency_contract').first()
    if agency_doc and not existing_regulation:
        app = current_app._get_current_object()
        def run_ai():
            with app.app_context():
                try:
                    regulation_fields = process_agency_agreement(agency_doc.filepath)
                    reg = Regulation(
                        data=regulation_fields,
                        raw_text='',
                        developer_id=dev.id
                    )
                    db.session.add(reg)
                    db.session.commit()
                except Exception as e:
                    app.logger.error(f"AI Agent background error: {e}")
        thread = threading.Thread(target=run_ai)
        thread.daemon = True
        thread.start()

    return redirect(url_for('admin.client_card', dev_id=dev.id))

# Просмотр карточки
@admin_bp.route('/client/<int:dev_id>')
def client_card(dev_id):
    dev = Developer.query.get_or_404(dev_id)
    regulation = Regulation.query.filter_by(developer_id=dev_id).first()
    return render_template('admin/client_card.html', developer=dev, regulation=regulation)

# Ручное сохранение регламента
@admin_bp.route('/client/<int:dev_id>/regulation', methods=['POST'])
def save_regulation(dev_id):
    dev = Developer.query.get_or_404(dev_id)
    form_data = request.form
    regulation_data = {}
    for key, value in form_data.items():
        if key.startswith('internal_regulation.') or key.startswith('booking_regulation.'):
            parts = key.split('.')
            section = parts[0]
            field = parts[1]
            if section not in regulation_data:
                regulation_data[section] = {}
            regulation_data[section][field] = value.strip()

    reg = Regulation.query.filter_by(developer_id=dev_id).first()
    if reg:
        reg.data = regulation_data
    else:
        reg = Regulation(data=regulation_data, raw_text='', developer_id=dev_id)
        db.session.add(reg)
    db.session.commit()
    return redirect(url_for('admin.client_card', dev_id=dev_id))

# Редактирование застройщика (GET – форма, POST – сохранение)
@admin_bp.route('/client/<int:dev_id>/edit', methods=['GET', 'POST'])
def edit_developer(dev_id):
    dev = Developer.query.get_or_404(dev_id)
    if request.method == 'POST':
        dev.name = request.form.get('name')
        dev.channels = request.form.get('channels')
        dev.chessboard_link = request.form.get('chessboard_link')
        dev.feed = request.form.get('feed')
        db.session.commit()
        return redirect(url_for('admin.client_card', dev_id=dev.id))
    return render_template('admin/edit_developer.html', developer=dev)

# Удаление застройщика
@admin_bp.route('/client/<int:dev_id>/delete', methods=['POST'])
def delete_developer(dev_id):
    dev = Developer.query.get_or_404(dev_id)
    db.session.delete(dev)
    db.session.commit()
    return redirect(url_for('admin.index'))

# Загрузка документа в существующую карточку и запуск ИИ
@admin_bp.route('/client/<int:dev_id>/upload', methods=['POST'])
def upload_for_developer(dev_id):
    dev = Developer.query.get_or_404(dev_id)
    if 'file' not in request.files:
        return redirect(url_for('admin.client_card', dev_id=dev_id))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('admin.client_card', dev_id=dev_id))

    original_filename = file.filename
    file_extension = original_filename.rsplit('.', 1)[-1] if '.' in original_filename else ''
    unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())

    try:
        file_bytes = file.read()
        current_app.supabase.storage.from_('developer-docs').upload(
            unique_filename,
            file_bytes,
            {"content-type": file.content_type}
        )
        public_url = current_app.supabase.storage.from_('developer-docs').get_public_url(unique_filename)
        doc = Document(
            filename=unique_filename,
            original_filename=original_filename,
            filepath=public_url,
            doc_type='agency_contract',
            developer_id=dev.id
        )
        db.session.add(doc)
        db.session.commit()

        # Запускаем ИИ, если ещё нет регламента
        existing_reg = Regulation.query.filter_by(developer_id=dev.id).first()
        if not existing_reg:
            app = current_app._get_current_object()
            def run_ai():
                with app.app_context():
                    try:
                        regulation_fields = process_agency_agreement(public_url)
                        reg = Regulation(data=regulation_fields, raw_text='', developer_id=dev.id)
                        db.session.add(reg)
                        db.session.commit()
                    except Exception as e:
                        app.logger.error(f"AI Agent background error: {e}")
            thread = threading.Thread(target=run_ai)
            thread.daemon = True
            thread.start()
    except Exception as e:
        current_app.logger.error(f"Upload error: {e}")

    return redirect(url_for('admin.client_card', dev_id=dev_id))
