import json
from datetime import datetime, date
from flask import render_template, request, redirect, url_for, flash
from app import db
from app.manager import manager_bp
from app.models import Agent, Employee, Presentation

@manager_bp.route('/')
def index():
    agents = Agent.query.order_by(Agent.created_at.desc()).all()
    return render_template('manager/index.html', agents=agents)

# ------------------ CRUD Агента ------------------
@manager_bp.route('/add', methods=['GET'])
def add_agent_form():
    return render_template('manager/add_agent.html')

@manager_bp.route('/submit', methods=['POST'])
def submit_agent():
    data = request.form
    agent = Agent(
        name=data.get('name'),
        director_name=data.get('director_name'),
        director_phone=data.get('director_phone'),
        contact_name=data.get('contact_name'),
        contact_phone=data.get('contact_phone'),
        messenger_linked=data.get('messenger_linked') == 'yes',
        messenger_contact=data.get('messenger_contact') if data.get('messenger_linked') != 'yes' else None,
        website=data.get('website'),
        active_agents_count=int(data.get('active_agents_count', 0))
    )
    db.session.add(agent)
    db.session.commit()
    return redirect(url_for('manager.agent_card', agent_id=agent.id))

@manager_bp.route('/agent/<int:agent_id>')
def agent_card(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    # Расчёт количества сотрудников, фиксаций, броней, сделок по компании
    total_employees = len(agent.employees)
    total_fixations = sum(e.fixations_count for e in agent.employees)
    total_bookings = sum(e.bookings_count for e in agent.employees)
    total_deals = sum(e.deals_count for e in agent.employees)

    # Презентации
    all_presentations = Presentation.query.filter_by(agent_id=agent.id).order_by(Presentation.presentation_date.desc()).all()
    today = date.today()
    current_month_presentations = [p for p in all_presentations if p.presentation_date and p.presentation_date.month == today.month and p.presentation_date.year == today.year]
    presentation_dates = [p.presentation_date.strftime('%d.%m.%Y') for p in all_presentations if p.presentation_date]
    last_presentation_date = max(p.presentation_date for p in all_presentations if p.presentation_date) if all_presentations else None

    return render_template('manager/agent_card.html',
                           agent=agent,
                           total_employees=total_employees,
                           total_fixations=total_fixations,
                           total_bookings=total_bookings,
                           total_deals=total_deals,
                           current_month_count=len(current_month_presentations),
                           all_time_count=len(all_presentations),
                           presentation_dates=presentation_dates,
                           last_presentation_date=last_presentation_date)

@manager_bp.route('/agent/<int:agent_id>/edit', methods=['GET', 'POST'])
def edit_agent(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    if request.method == 'POST':
        data = request.form
        agent.name = data.get('name')
        agent.director_name = data.get('director_name')
        agent.director_phone = data.get('director_phone')
        agent.contact_name = data.get('contact_name')
        agent.contact_phone = data.get('contact_phone')
        agent.messenger_linked = data.get('messenger_linked') == 'yes'
        agent.messenger_contact = data.get('messenger_contact') if data.get('messenger_linked') != 'yes' else None
        agent.website = data.get('website')
        agent.active_agents_count = int(data.get('active_agents_count', 0))
        db.session.commit()
        return redirect(url_for('manager.agent_card', agent_id=agent.id))
    return render_template('manager/edit_agent.html', agent=agent)

@manager_bp.route('/agent/<int:agent_id>/delete', methods=['POST'])
def delete_agent(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    db.session.delete(agent)
    db.session.commit()
    return redirect(url_for('manager.index'))

# ------------------ CRUD Сотрудников ------------------
@manager_bp.route('/agent/<int:agent_id>/employee/add', methods=['POST'])
def add_employee(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    emp = Employee(
        full_name=request.form.get('full_name'),
        phone=request.form.get('phone'),
        messenger=request.form.get('messenger'),
        fixations_count=int(request.form.get('fixations_count', 0)),
        bookings_count=int(request.form.get('bookings_count', 0)),
        deals_count=int(request.form.get('deals_count', 0)),
        agent_id=agent.id
    )
    db.session.add(emp)
    db.session.commit()
    return redirect(url_for('manager.agent_card', agent_id=agent.id))

@manager_bp.route('/employee/<int:employee_id>/edit', methods=['POST'])
def edit_employee(employee_id):
    emp = Employee.query.get_or_404(employee_id)
    emp.full_name = request.form.get('full_name')
    emp.phone = request.form.get('phone')
    emp.messenger = request.form.get('messenger')
    emp.fixations_count = int(request.form.get('fixations_count', 0))
    emp.bookings_count = int(request.form.get('bookings_count', 0))
    emp.deals_count = int(request.form.get('deals_count', 0))
    db.session.commit()
    return redirect(url_for('manager.agent_card', agent_id=emp.agent_id))

@manager_bp.route('/employee/<int:employee_id>/delete', methods=['POST'])
def delete_employee(employee_id):
    emp = Employee.query.get_or_404(employee_id)
    agent_id = emp.agent_id
    db.session.delete(emp)
    db.session.commit()
    return redirect(url_for('manager.agent_card', agent_id=agent_id))

# ------------------ Заглушка «Клиенты в работе» ------------------
@manager_bp.route('/clients')
def clients_placeholder():
    return render_template('manager/clients_placeholder.html')
