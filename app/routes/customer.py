from flask import Blueprint, render_template
from flask_login import login_required, current_user

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/dashboard')
@login_required
def dashboard():
    return ('<h1 style="color:white;font-family:Inter,sans-serif;padding:2rem;">'
            'Customer Dashboard</h1>'
            '<p style="color:#aaa;font-family:Inter,sans-serif;padding:0 2rem;">'
            'Coming soon in Phase 8!</p>'
            '<a href="/logout" style="color:#42a5f5;font-family:Inter,sans-serif;'
            'padding:0 2rem;display:inline-block;margin-top:1rem;">Logout</a>')
