from datetime import datetime, timezone
from app import db


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, unique=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    orders = db.relationship('Order', backref='customer', lazy=True)

    @property
    def total_spent(self):
        return sum(order.total_amount for order in self.orders if order.status == 'completed')

    @property
    def order_count(self):
        return len(self.orders)

    def __repr__(self):
        return f'<Customer {self.full_name}>'
