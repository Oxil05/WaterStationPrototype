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
    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(8).all()

    return render_template('admin/dashboard.html',
        today_revenue=today_revenue,
        total_orders=total_orders,
        active_customers=active_customers,
        pending_deliveries=pending_deliveries,
        recent_orders=recent_orders
    )


@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    # Filter by status if specified in query params
    status_filter = request.args.get('status', 'all')
    if status_filter != 'all':
        orders_list = Order.query.filter_by(status=status_filter).order_by(Order.order_date.desc()).all()
    else:
        orders_list = Order.query.order_by(Order.order_date.desc()).all()
        
    return render_template('admin/orders.html', orders=orders_list, current_status=status_filter)


@admin_bp.route('/orders/update-status/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    if new_status in ('pending', 'confirmed', 'completed', 'cancelled'):
        order.status = new_status
        if order.delivery:
            if new_status == 'completed':
                order.delivery.status = 'delivered'
                order.delivery.delivery_date = datetime.now(timezone.utc)
            elif new_status == 'cancelled':
                order.delivery.status = 'failed'
            elif new_status == 'confirmed' and order.delivery.status == 'pending':
                pass # keep as pending
        db.session.commit()
        flash(f'Order #{order.id} status updated to {new_status}.', 'success')
    else:
        flash('Invalid status value.', 'danger')
        
    return redirect(request.referrer or url_for('admin.orders'))


@admin_bp.route('/customers')
@login_required
@admin_required
def customers():
    customers_list = Customer.query.filter_by(is_active=True).all()
    return render_template('admin/customers.html', customers=customers_list)


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
            return redirect(url_for('admin.customers'))
        if new_slim is not None and not (20.0 <= new_slim <= 30.0):
            flash('Error: Slim refill price must be between ₱20.00 and ₱30.00.', 'danger')
            return redirect(url_for('admin.customers'))
            
        customer.custom_price_round = new_round
        customer.custom_price_slim = new_slim
        db.session.commit()
        flash(f'Custom container rates updated for {customer.full_name}.', 'success')
    except (TypeError, ValueError):
        flash('Error: Invalid price inputs. Enter valid numbers.', 'danger')
        
    return redirect(url_for('admin.customers'))


@admin_bp.route('/deliveries')
@login_required
@admin_required
def deliveries():
    deliveries_list = Delivery.query.order_by(Delivery.created_at.desc()).all()
    return render_template('admin/deliveries.html', deliveries=deliveries_list)


@admin_bp.route('/deliveries/update/<int:delivery_id>', methods=['POST'])
@login_required
@admin_required
def update_delivery(delivery_id):
    delivery = Delivery.query.get_or_404(delivery_id)
    driver_name = request.form.get('driver_name', '').strip()
    status = request.form.get('status')
    
    if status in ('pending', 'in_transit', 'delivered', 'failed'):
        delivery.status = status
        if driver_name:
            delivery.driver_name = driver_name
            
        # Synchronize order status
        if status == 'delivered':
            delivery.order.status = 'completed'
            delivery.delivery_date = datetime.now(timezone.utc)
        elif status == 'in_transit':
            delivery.order.status = 'confirmed'
        elif status == 'failed':
            delivery.order.status = 'cancelled'
            
        db.session.commit()
        flash(f'Delivery details for Order #{delivery.order_id} updated.', 'success')
    else:
        flash('Invalid delivery status.', 'danger')
        
    return redirect(request.referrer or url_for('admin.deliveries'))


@admin_bp.route('/revenue')
@login_required
@admin_required
def revenue():
    completed_orders = Order.query.filter(Order.status.in_(['completed', 'confirmed'])).all()
    total_sales = sum(o.total_amount for o in completed_orders)
    
    # Calculate refill quantities
    round_qty = 0
    slim_qty = 0
    for o in completed_orders:
        for item in o.items:
            if 'Round' in item.product.name:
                round_qty += item.quantity
            elif 'Slim' in item.product.name:
                slim_qty += item.quantity
                
    return render_template('admin/revenue.html',
        total_sales=total_sales,
        orders_count=len(completed_orders),
        round_qty=round_qty,
        slim_qty=slim_qty,
        orders=completed_orders
    )
