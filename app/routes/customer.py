from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.customer import Customer
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.delivery import Delivery
from datetime import datetime, timezone

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/dashboard')
@login_required
def dashboard():
    customer = current_user.customer_profile
    if not customer:
        flash('Customer profile not found. Please contact support.', 'error')
        return redirect(url_for('auth.logout'))
    
    # Sort orders by date descending
    orders = sorted(customer.orders, key=lambda o: o.order_date, reverse=True)
    
    # Find active order (uncompleted/undelivered)
    active_order = None
    for o in orders:
        if o.status in ('pending', 'confirmed') or (o.delivery and o.delivery.status in ('pending', 'in_transit')):
            active_order = o
            break
    
    return render_template('customer/dashboard.html', customer=customer, orders=orders, active_order=active_order)


@customer_bp.route('/order', methods=['GET', 'POST'])
@login_required
def place_order():
    customer = current_user.customer_profile
    if not customer:
        flash('Customer profile not found.', 'error')
        return redirect(url_for('auth.logout'))
        
    products = Product.query.filter_by(is_available=True).all()
    
    if request.method == 'POST':
        # Collect item quantities
        items_ordered = []
        for p in products:
            qty = int(request.form.get(f'qty_{p.id}', 0))
            if qty > 0:
                items_ordered.append((p, qty))
                
        notes = request.form.get('notes', '').strip()
        
        if not items_ordered:
            flash('Please select at least one water container to order.', 'warning')
            return render_template('customer/order.html', products=products, customer=customer)
            
        # Create order
        new_order = Order(
            customer_id=customer.id,
            status='pending',
            order_date=datetime.now(timezone.utc),
            notes=notes
        )
        db.session.add(new_order)
        db.session.flush() # get new_order.id
        
        total_amount = 0.0
        for product, qty in items_ordered:
            price = product.price
            if 'Round' in product.name and customer.custom_price_round is not None:
                price = customer.custom_price_round
            elif 'Slim' in product.name and customer.custom_price_slim is not None:
                price = customer.custom_price_slim
                
            subtotal = price * qty
            total_amount += subtotal
            
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=qty,
                unit_price=price,
                subtotal=subtotal
            )
            db.session.add(order_item)
            
        new_order.total_amount = total_amount
        
        # Create delivery profile automatically
        new_delivery = Delivery(
            order_id=new_order.id,
            status='pending',
            notes=f"Delivery to: {customer.address}"
        )
        db.session.add(new_delivery)
        
        db.session.commit()
        flash('Your order refill has been placed successfully!', 'success')
        return redirect(url_for('customer.dashboard'))
        
    return render_template('customer/order.html', products=products, customer=customer)


@customer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    customer = current_user.customer_profile
    if not customer:
        flash('Customer profile not found.', 'error')
        return redirect(url_for('auth.logout'))
        
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        
        if not full_name:
            flash('Full name is required.', 'error')
            return render_template('customer/profile.html', customer=customer)
            
        customer.full_name = full_name
        customer.phone = phone
        customer.address = address
        customer.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('customer.dashboard'))
        
    return render_template('customer/profile.html', customer=customer)
