"""
Quick script to create admin user
"""
from app import create_app
from app.models.user import User
from config import get_config
import os

# Create app
env = os.getenv('FLASK_ENV', 'development')
app = create_app(get_config(env))

with app.app_context():
    # Check if admin exists
    existing = User.find_by_email('admin@homeservepro.com')
    if existing:
        print('✓ Admin user already exists: admin@homeservepro.com')
    else:
        # Create admin
        admin_data = {
            'email': 'admin@homeservepro.com',
            'password': 'password123',
            'name': 'Super Admin',
            'phone': '0000000000',
            'role': User.ROLE_SUPER_ADMIN,
            'verified': True,
            'active': True
        }
        user_id = User.create(admin_data)
        print(f'✅ Super admin created successfully!')
        print(f'Email: admin@homeservepro.com')
        print(f'Password: password123')
        print(f'Role: {User.ROLE_SUPER_ADMIN}')

