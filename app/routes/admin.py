from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timezone
from app import db
from app.models.order import Order
from app.models.customer import Customer
from app.models.delivery import Delivery

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Today's revenue
    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    today_orders = Order.query.filter(
        Order.order_date >= today_start,
        Order.status.in_(['completed', 'confirmed'])
    ).all()
    today_revenue = sum(order.total_amount for order in today_orders)

    # Total orders
    total_orders = Order.query.count()

    # Active customers
    active_customers = Customer.query.filter_by(is_active=True).count()

    # Pending deliveries
    pending_deliveries = Delivery.query.filter_by(status='pending').count()

    # Recent orders
    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
        today_revenue=today_revenue,
        total_orders=total_orders,
        active_customers=active_customers,
        pending_deliveries=pending_deliveries,
        recent_orders=recent_orders
    )
