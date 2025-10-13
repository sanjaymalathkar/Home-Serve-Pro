"""
View routes for HomeServe Pro.
Serves HTML templates for the frontend.
"""

from flask import Blueprint, render_template, redirect, url_for

views_bp = Blueprint('views', __name__)


@views_bp.route('/')
def index():
    """Render the landing page."""
    return render_template('index.html')


@views_bp.route('/login')
def login():
    """Render the login page."""
    return render_template('login.html')


@views_bp.route('/register')
def register():
    """Render the registration page."""
    return render_template('register.html')


@views_bp.route('/services')
def services():
    """Render the services page."""
    return render_template('services.html')


@views_bp.route('/dashboard')
def dashboard():
    """Render the dashboard page."""
    return render_template('dashboard.html')


@views_bp.route('/customer/dashboard')
def customer_dashboard():
    """Render customer dashboard."""
    return render_template('customer_dashboard.html')


@views_bp.route('/vendor/dashboard')
def vendor_dashboard():
    """Render vendor dashboard."""
    return render_template('vendor_dashboard.html')


@views_bp.route('/admin/dashboard')
def admin_dashboard():
    """Render admin dashboard."""
    return render_template('admin_dashboard.html')

