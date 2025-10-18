from flask import Blueprint, render_template


main_pages_bp = Blueprint('main_pages', __name__)


@main_pages_bp.route('/')
def root_page():
    """Serve the login page for the web panel."""

    return render_template('login.html')


@main_pages_bp.route('/dashboard')
def dashboard_page():
    """Serve the dashboard shell that loads plugin content."""

    return render_template('dashboard.html')
