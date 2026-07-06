from app import create_app, db
from app.models.user import User
from app.models.customer import Customer
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.delivery import Delivery
from datetime import datetime, timedelta, timezone
import random


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        print('Seeding database...')

        # Create admin user
        admin = User(username='admin', email='admin@waterstation.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)

        # Create products
        round_container = Product(
            name='5-Gallon Round Blue Container (Refill)',
            description='Standard 5-gallon round blue water container refill with purified mineral water.',
            price=25.00,
            stock_quantity=500,
            unit='gallon'
        )
        slim_container = Product(
            name='5-Gallon Slim Blue Container (Refill)',
            description='Slim-type 5-gallon blue water container refill with purified mineral water.',
            price=30.00,
            stock_quantity=300,
            unit='gallon'
        )
        db.session.add_all([round_container, slim_container])
        db.session.flush()

        # Create customer users and profiles
        customers = []
        customer_data = [
            ('juan', 'juan@email.com', 'Juan Dela Cruz', '09171234567', '123 Main St, Manila'),
            ('maria', 'maria@email.com', 'Maria Santos', '09181234567', '456 Rizal Ave, Quezon City'),
            ('pedro', 'pedro@email.com', 'Pedro Reyes', '09191234567', '789 Bonifacio St, Makati'),
        ]

        for username, email, full_name, phone, address in customer_data:
            user = User(username=username, email=email, role='customer')
            user.set_password('password123')
            db.session.add(user)
            db.session.flush()

            customer = Customer(
                user_id=user.id,
                full_name=full_name,
                phone=phone,
                address=address
            )
            db.session.add(customer)
            db.session.flush()
            customers.append(customer)

        # Create sample orders over the past 30 days
        products = [round_container, slim_container]
        statuses = ['completed', 'completed', 'completed', 'pending', 'confirmed']
        now = datetime.now(timezone.utc)

        for i in range(20):
            days_ago = random.randint(0, 30)
            order_date = now - timedelta(days=days_ago, hours=random.randint(0, 12))
            customer = random.choice(customers)
            status = random.choice(statuses)

            order = Order(
                customer_id=customer.id,
                status=status,
                order_date=order_date,
                created_at=order_date
            )
            db.session.add(order)
            db.session.flush()

            # Add 1-2 items per order
            num_items = random.randint(1, 2)
            total = 0.0
            for _ in range(num_items):
                product = random.choice(products)
                quantity = random.randint(1, 5)
                subtotal = product.price * quantity
                total += subtotal

                item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=product.price,
                    subtotal=subtotal
                )
                db.session.add(item)

            order.total_amount = total

            # Add delivery for completed orders
            if status == 'completed':
                delivery = Delivery(
                    order_id=order.id,
                    delivery_date=order_date + timedelta(hours=random.randint(1, 6)),
                    status='delivered',
                    driver_name=random.choice(['Carlos', 'Miguel', 'Ramon']),
                    created_at=order_date
                )
                db.session.add(delivery)

        db.session.commit()
        print('Database seeded successfully!')
        print('  - 1 admin user (admin / admin123)')
        print('  - 3 customer users (juan, maria, pedro / password123)')
        print('  - 2 products')
        print('  - 20 sample orders')


if __name__ == '__main__':
    seed()
