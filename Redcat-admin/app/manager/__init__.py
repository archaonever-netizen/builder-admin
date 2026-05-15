from flask import Blueprint
manager_bp = Blueprint('manager', __name__, template_folder='../templates/manager', static_folder='../static')
