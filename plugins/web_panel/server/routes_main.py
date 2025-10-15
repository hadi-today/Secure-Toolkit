# plugins/web_panel/server/routes_main.py

from flask import Blueprint, render_template

main_pages_bp = Blueprint('main_pages', __name__)

@main_pages_bp.route('/')
def root_page():

    return render_template('login.html')

@main_pages_bp.route('/dashboard')
def dashboard_page():

    return render_template('dashboard.html')