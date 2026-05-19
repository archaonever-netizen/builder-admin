import json, os, uuid, threading
from datetime import datetime
from flask import (render_template, request, jsonify, session, redirect, url_for, current_app)
from app import db
from app.admin import admin_bp
from app.models import Developer, ResidentialComplex, Contact, Document, Regulation, Draft
from app.ai_agent.agent import process_agency_agreement

CONTACT_TYPES_RU = {
    'curator': 'Куратор',
    'rop': 'РОП',
    'partner_head': 'Руководитель партнёрского отдела',
    'doc_flow': 'Документооборот'
}

@admin_bp.route('/')
def index():
    developers = Developer.query.order_by(Developer.created_at.desc()).all()
    return render_template('admin/index.html', developers=developers)

@admin_bp.route('/add', methods=['GET', 'POST'])
def add_developer():
    if 'draft_token' not in session:
        session['draft_token'] = str(uuid.uuid4())
    draft = Draft.query.filter_by(session_token=session['draft_token']).first()
    draft_data = draft.data if draft else {}
    return render_template('admin/add_developer.html', draft=draft_data)

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

    complexes_json = data.get('complexes', '[]')
    try:
        complexes = json.loads(complexes_json)
        for comp in complexes:
            rc = ResidentialComplex(
                name=comp.get('name'),
                city=comp.get('city', ''),
                region=comp.get('region', ''),
                property_type=comp.get('property_type', ''),
                commission=comp.get('commission'),
                contact_person=comp.get('contact_person'),
                developer_id=dev.id
            )
            db.session.add(rc)
    except:
        pass

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

    return redirect(url_for('admin.client_card', dev_id=dev.id))

@admin_bp.route('/client/<int:dev_id>')
def client_card(dev_id):
    dev = Developer.query.get_or_404(dev_id)
    regulation = Regulation.query.filter_by(developer_id=dev_id).first()
    return render_template('admin/client_card.html', developer=dev, regulation=regulation, contact_types_ru=CONTACT_TYPES_RU)

# CRUD для ЖК
@admin_bp.route('/client/<int:dev_id>/complex/add', methods=['POST'])
def add_complex(dev_id):
    dev = Developer.query.get_or_404(dev_id)
    rc = ResidentialComplex(
        name=request.form.get('name'),
        city=request.form.get('city', ''),
        region=request.form.get('region', ''),
        property_type=request.form.get('property_type', ''),
        commission=request.form.get('commission'),
        contact_person=request.form.get('contact_person'),
        developer_id=dev.id
    )
    db.session.add(rc)
    db.session.commit()
    return redirect(url_for('admin.client_card', dev_id=dev_id))

@admin_bp.route('/complex/<int:complex_id>/edit', methods=['POST'])
def edit_complex(complex_id):
    rc = ResidentialComplex.query.get_or_404(complex_id)
    rc.name = request.form.get('name')
    rc.city = request.form.get('city', '')
    rc.region = request.form.get('region', '')
    rc.property_type = request.form.get('property_type', '')
    rc.commission = request.form.get('commission')
    rc.contact_person = request.form.get('contact_person')
    db.session.commit()
    return redirect(url_for('admin.client_card', dev_id=rc.developer_id))

@admin_bp.route('/complex/<int:complex_id>/delete', methods=['POST'])
def delete_complex(complex_id):
    rc = ResidentialComplex.query.get_or_404(complex_id)
    dev_id = rc.developer_id
    db.session.delete(rc)
    db.session.commit()
    return redirect(url_for('admin.client_card', dev_id=dev_id))

# CRUD для Контактов
@admin_bp.route('/client/<int:dev_id>/contact/add', methods=['POST'])
def add_contact(dev_id):
    dev = Developer.query.get_or_404(dev_id)
    c = Contact(
        contact_type=request.form.get('contact_type'),
        name=request.form.get('name'),
        phone=request.form.get('phone'),
        email=request.form.get('email'),
        developer_id=dev.id
    )
    db.session.add(c)
    db.session.commit()
    return redirect(url_for('admin.client_card', dev_id=dev_id))

@admin_bp.route('/contact/<int:contact_id>/edit', methods=['POST'])
def edit_contact(contact_id):
    c = Contact.query.get_or_404(contact_id)
    c.contact_type = request.form.get('contact_type')
    c.name = request.form.get('name')
    c.phone = request.form.get('phone')
    c.email = request.form.get('email')
    db.session.commit()
    return redirect(url_for('admin.client_card', dev_id=c.developer_id))

@admin_bp.route('/contact/<int:contact_id>/delete', methods=['POST'])
def delete_contact(contact_id):
    c = Contact.query.get_or_404(contact_id)
    dev_id = c.developer_id
    db.session.delete(c)
    db.session.commit()
    return redirect(url_for('admin.client_card', dev_id=dev_id))

# Документы
@admin_bp.route('/client/<int:dev_id>/document/<int:doc_id>/delete', methods=['POST'])
def delete_document(dev_id, doc_id):
    doc = Document.query.get_or_404(doc_id)
    try:
        current_app.supabase.storage.from_('developer-docs').remove([doc.filename])
    except Exception as e:
        current_app.logger.error(f"Ошибка удаления файла {doc.filename}: {e}")
    db.session.delete(doc)
    db.session.commit()
    return redirect(url_for('admin.client_card', dev_id=dev_id))

@admin_bp.route('/client/<int:dev_id>/upload', methods=['POST'])
def upload_for_developer(dev_id):
    dev = Developer.query.get_or_404(dev_id)
    files = request.files.getlist('files')
    for file in files:
        if file.filename == '':
            continue
        original_filename = file.filename
        file_extension = original_filename.rsplit('.', 1)[-1] if '.' in original_filename else ''
        unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
        try:
            file_bytes = file.read()
            current_app.supabase.storage.from_('developer-docs').upload(
                unique_filename, file_bytes, {"content-type": file.content_type}
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
        except Exception as e:
            current_app.logger.error(f"Upload error: {e}")
    db.session.commit()
    return redirect(url_for('admin.client_card', dev_id=dev_id))

# Регламент
@admin_bp.route('/client/<int:dev_id>/regulation', methods=['POST'])
def save_regulation(dev_id):
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
        reg.status = ''
    else:
        reg = Regulation(data=regulation_data, status='', developer_id=dev_id)
        db.session.add(reg)
    db.session.commit()
    return redirect(url_for('admin.client_card', dev_id=dev_id))

@admin_bp.route('/client/<int:dev_id>/regulation/start', methods=['POST'])
def start_regulation(dev_id):
    docs = Document.query.filter_by(developer_id=dev_id, doc_type='agency_contract').all()
    if not docs:
        return jsonify({'error': 'Нет файлов для анализа'}), 400

    reg = Regulation.query.filter_by(developer_id=dev_id).first()
    if not reg:
        reg = Regulation(developer_id=dev_id, data={}, status='')
        db.session.add(reg)
    reg.status = "Анализирую"
    db.session.commit()

    app = current_app._get_current_object()
    urls = [doc.filepath for doc in docs]

    def run_auto():
        with app.app_context():
            reg_local = Regulation.query.filter_by(developer_id=dev_id).first()
            if not reg_local:
                return
            try:
                reg_local.status = "Систематизация"
                db.session.commit()
                result = process_agency_agreement(urls)
                reg_local.status = "Заполнение"
                db.session.commit()
                reg_local.data = result
                reg_local.status = "Выполнено"
            except Exception as e:
                reg_local.status = f"Ошибка: {e}"
            db.session.commit()

    thread = threading.Thread(target=run_auto)
    thread.daemon = True
    thread.start()
    return jsonify({'status': 'started'})

@admin_bp.route('/client/<int:dev_id>/regulation/status')
def regulation_status(dev_id):
    reg = Regulation.query.filter_by(developer_id=dev_id).first()
    return jsonify({'status': reg.status if reg else ''})

@admin_bp.route('/client/<int:dev_id>/regulation/field', methods=['POST'])
def update_regulation_field(dev_id):
    reg = Regulation.query.filter_by(developer_id=dev_id).first()
    if not reg or not reg.data:
        return jsonify({'error': 'Регламент не найден'}), 404
    data = request.get_json()
    key = data.get('key')
    value = data.get('value', '')
    if not key:
        return jsonify({'error': 'Не указан ключ'}), 400
    # Поддержка вложенных ключей вида internal_regulation.company
    parts = key.split('.', 1)
    if len(parts) == 2 and parts[0] in reg.data and isinstance(reg.data[parts[0]], dict):
        reg.data[parts[0]][parts[1]] = value
        reg.status = ''  # сброс статуса, чтобы отображалось как ручное
    else:
        return jsonify({'error': 'Неверный ключ'}), 400
    db.session.commit()
    return jsonify({'status': 'ok'})

# Редактирование/удаление застройщика
@admin_bp.route('/client/<int:dev_id>/edit', methods=['GET', 'POST'])
def edit_developer(dev_id):
    dev = Developer.query.get_or_404(dev_id)
    if request.method == 'POST':
        dev.name = request.form.get('name')
        dev.channels = request.form.get('channels')
        new_chessboard = request.form.get('chessboard_link')
        if new_chessboard != dev.chessboard_link:
            dev.chessboard_updated = datetime.utcnow()
        dev.chessboard_link = new_chessboard
        new_feed = request.form.get('feed')
        if new_feed != dev.feed:
            dev.feed_updated = datetime.utcnow()
        dev.feed = new_feed
        db.session.commit()
        return redirect(url_for('admin.client_card', dev_id=dev.id))
    return render_template('admin/edit_developer.html', developer=dev)

@admin_bp.route('/client/<int:dev_id>/delete', methods=['POST'])
def delete_developer(dev_id):
    dev = Developer.query.get_or_404(dev_id)
    for doc in dev.documents:
        try:
            current_app.supabase.storage.from_('developer-docs').remove([doc.filename])
        except Exception as e:
            current_app.logger.error(f"Не удалось удалить файл {doc.filename}: {e}")
    db.session.delete(dev)
    db.session.commit()
    return redirect(url_for('admin.index'))

# ========== ИМПОРТ ИЗ ТАБЛИЦЫ ==========
@admin_bp.route('/import')
def import_developers():
    return render_template('admin/import_developers.html')

@admin_bp.route('/import/execute', methods=['POST'])
def import_execute():
    data = request.get_json()
    if not data or 'rows' not in data or 'mapping' not in data:
        return jsonify({'error': 'Неверные данные запроса'}), 400

    rows = data['rows']          # list of lists (строки таблицы)
    mapping = data['mapping']    # dict: поле -> индекс колонки или None

    # Обязательные поля
    dev_name_col = mapping.get('developer_name')
    complex_name_col = mapping.get('complex_name')
    if dev_name_col is None or complex_name_col is None:
        return jsonify({'error': 'Сопоставьте обязательные поля: Название застройщика и Название ЖК'}), 400

    # Группируем строки по имени застройщика
    developer_groups = {}
    for row in rows:
        if len(row) <= max(dev_name_col, complex_name_col):
            continue
        dev_name = str(row[dev_name_col]).strip()
        complex_name = str(row[complex_name_col]).strip()
        if not dev_name or not complex_name:
            continue
        if dev_name not in developer_groups:
            developer_groups[dev_name] = []
        developer_groups[dev_name].append(row)

    created_devs = 0
    created_complexes = 0
    try:
        for dev_name, row_list in developer_groups.items():
            # Создаём застройщика
            dev = Developer(name=dev_name)
            db.session.add(dev)
            db.session.flush()  # получаем dev.id
            created_devs += 1

            for row in row_list:
                # Извлекаем данные по маппингу
                def get_cell(col_idx):
                    if col_idx is not None and col_idx < len(row):
                        val = str(row[col_idx]).strip()
                        return val if val else ''
                    return ''

                complex_name = get_cell(complex_name_col)
                city = get_cell(mapping.get('city'))
                region = get_cell(mapping.get('region'))
                property_type = get_cell(mapping.get('property_type'))
                commission = get_cell(mapping.get('commission'))
                contact_person = get_cell(mapping.get('contact_person'))

                rc = ResidentialComplex(
                    name=complex_name,
                    city=city,
                    region=region,
                    property_type=property_type,
                    commission=commission,
                    contact_person=contact_person,
                    developer_id=dev.id
                )
                db.session.add(rc)
                created_complexes += 1

                # Контакт (если есть имя или телефон)
                contact_name = get_cell(mapping.get('contact_name'))
                contact_phone = get_cell(mapping.get('contact_phone'))
                contact_email = get_cell(mapping.get('contact_email'))

                if contact_name or contact_phone:
                    c = Contact(
                        contact_type='curator',  # по умолчанию – куратор
                        name=contact_name,
                        phone=contact_phone,
                        email=contact_email,
                        developer_id=dev.id
                    )
                    db.session.add(c)

        db.session.commit()
        return jsonify({
            'status': 'success',
            'developers_created': created_devs,
            'complexes_created': created_complexes
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Ошибка при сохранении: {str(e)}'}), 500
