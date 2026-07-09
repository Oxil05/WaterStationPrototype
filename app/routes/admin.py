from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timezone
from app import db
from app.models.order import Order
from app.models.customer import Customer
from app.models.delivery import Delivery
from app.models.product import Product

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

    # Fetch products and customers
    products = Product.query.all()
    customers = Customer.query.filter_by(is_active=True).all()

    return render_template('admin/dashboard.html',
        today_revenue=today_revenue,
        total_orders=total_orders,
        active_customers=active_customers,
        pending_deliveries=pending_deliveries,
        recent_orders=recent_orders,
        products=products,
        customers=customers
    )


@admin_bp.route('/update-customer-prices/<int:customer_id>', methods=['POST'])
@login_required
@admin_required
def update_customer_prices(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    try:
        round_str = request.form.get('custom_price_round', '').strip()
        slim_str = request.form.get('custom_price_slim', '').strip()
        
        # If empty, reset to None (uses global default price)
        new_round = float(round_str) if round_str else None
        new_slim = float(slim_str) if slim_str else None
        
        # Validation checks between 20 and 30 pesos bounds
        if new_round is not None and not (20.0 <= new_round <= 30.0):
            flash('Error: Round refill price must be between ₱20.00 and ₱30.00.', 'danger')
            return redirect(url_for('admin.dashboard'))
        if new_slim is not None and not (20.0 <= new_slim <= 30.0):
            flash('Error: Slim refill price must be between ₱20.00 and ₱30.00.', 'danger')
            return redirect(url_for('admin.dashboard'))
            
        customer.custom_price_round = new_round
        customer.custom_price_slim = new_slim
        db.session.commit()
        flash(f'Custom container rates updated for {customer.full_name}.', 'success')
    except (TypeError, ValueError):
        flash('Error: Invalid price inputs. Enter valid numbers.', 'danger')
        
    return redirect(url_for('admin.dashboard'))
