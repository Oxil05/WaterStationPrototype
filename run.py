from app import create_app, db

app = create_app()

# Auto-initialize and seed database on module loading (runs on Gunicorn/Render deployments)
with app.app_context():
    db.create_all()
    
    # Seed admin user if missing
    from app.models.user import User
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin_user = User(username='admin', email='admin@waterstation.com', role='admin')
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        
        # Seed default products
        from app.models.product import Product
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
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
