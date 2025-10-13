"""
CLI commands for HomeServe Pro.
Database initialization, admin creation, and data seeding.
"""

import click
from flask.cli import with_appcontext
from app.models.user import User
from app.models.vendor import Vendor
from app.models.service import Service
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.signature import Signature
from app.models.audit_log import AuditLog
from app.models.notification import Notification


@click.command('init-db')
@with_appcontext
def init_db():
    """Initialize database with indexes."""
    try:
        click.echo('Creating database indexes...')
        
        User.create_indexes()
        click.echo('✓ User indexes created')
        
        Vendor.create_indexes()
        click.echo('✓ Vendor indexes created')
        
        Service.create_indexes()
        click.echo('✓ Service indexes created')
        
        Booking.create_indexes()
        click.echo('✓ Booking indexes created')
        
        Payment.create_indexes()
        click.echo('✓ Payment indexes created')
        
        Signature.create_indexes()
        click.echo('✓ Signature indexes created')
        
        AuditLog.create_indexes()
        click.echo('✓ AuditLog indexes created')
        
        Notification.create_indexes()
        click.echo('✓ Notification indexes created')
        
        click.echo('\n✅ Database initialized successfully!')
        
    except Exception as e:
        click.echo(f'\n❌ Error initializing database: {str(e)}', err=True)


@click.command('monitor-signatures')
@with_appcontext
def monitor_signatures():
    """Monitor signature timeouts and send reminders."""
    try:
        from app.tasks.signature_monitor import run_signature_monitor

        click.echo('Starting signature monitoring...')
        result = run_signature_monitor()

        click.echo('\n📊 Signature Monitoring Results:')
        click.echo(f'   • Escalated timeouts: {result["escalated"]}')
        click.echo(f'   • Reminders sent: {result["reminders_sent"]}')

        stats = result["statistics"]
        click.echo(f'\n📈 Current Statistics:')
        click.echo(f'   • Pending signatures: {stats["total_pending"]}')
        click.echo(f'   • Expired signatures: {stats["total_expired"]}')
        click.echo(f'   • Completed signatures: {stats["total_signed"]}')
        click.echo(f'   • Expiring soon (24h): {stats["expiring_soon"]}')

        click.echo('\n✅ Signature monitoring completed successfully!')

    except Exception as e:
        click.echo(f'❌ Error during signature monitoring: {str(e)}')
        raise


@click.command('create-admin')
@click.option('--email', prompt='Admin email', help='Admin email address')
@click.option('--password', prompt='Admin password', hide_input=True, confirmation_prompt=True, help='Admin password')
@click.option('--name', prompt='Admin name', help='Admin full name')
@with_appcontext
def create_admin(email, password, name):
    """Create a super admin user."""
    try:
        # Check if admin already exists
        existing_user = User.find_by_email(email)
        if existing_user:
            click.echo(f'❌ User with email {email} already exists!', err=True)
            return
        
        # Create admin user
        admin_data = {
            'email': email.lower(),
            'password': password,
            'name': name,
            'phone': '0000000000',
            'role': User.ROLE_SUPER_ADMIN,
            'verified': True,
            'active': True
        }
        
        user_id = User.create(admin_data)
        
        click.echo(f'\n✅ Super admin created successfully!')
        click.echo(f'User ID: {user_id}')
        click.echo(f'Email: {email}')
        click.echo(f'Role: {User.ROLE_SUPER_ADMIN}')
        
    except Exception as e:
        click.echo(f'\n❌ Error creating admin: {str(e)}', err=True)


@click.command('seed-data')
@with_appcontext
def seed_data():
    """Seed database with sample data."""
    try:
        click.echo('Seeding database with sample data...\n')
        
        # Create sample services
        services_data = [
            {
                'name': 'Plumbing - Leak Repair',
                'description': 'Fix leaking pipes, faucets, and drains',
                'category': Service.CATEGORY_PLUMBING,
                'base_price': 50.0,
                'duration_minutes': 60
            },
            {
                'name': 'Electrical - Wiring',
                'description': 'Electrical wiring and circuit installation',
                'category': Service.CATEGORY_ELECTRICAL,
                'base_price': 75.0,
                'duration_minutes': 90
            },
            {
                'name': 'House Painting',
                'description': 'Interior and exterior house painting',
                'category': Service.CATEGORY_PAINTING,
                'base_price': 200.0,
                'duration_minutes': 480
            },
            {
                'name': 'Deep Cleaning',
                'description': 'Complete house deep cleaning service',
                'category': Service.CATEGORY_CLEANING,
                'base_price': 100.0,
                'duration_minutes': 180
            },
            {
                'name': 'Furniture Assembly',
                'description': 'Assemble and install furniture',
                'category': Service.CATEGORY_CARPENTRY,
                'base_price': 40.0,
                'duration_minutes': 60
            },
            {
                'name': 'AC Repair',
                'description': 'Air conditioner repair and maintenance',
                'category': Service.CATEGORY_APPLIANCE_REPAIR,
                'base_price': 80.0,
                'duration_minutes': 90
            }
        ]
        
        for service_data in services_data:
            # Check if service already exists
            if not Service.find_by_name(service_data['name']):
                Service.create(service_data)
                click.echo(f'✓ Created service: {service_data["name"]}')
        
        click.echo(f'\n✅ Sample services created!')
        
        # Create sample users
        click.echo('\nCreating sample users...')
        
        # Sample customer
        if not User.find_by_email('customer@test.com'):
            customer_data = {
                'email': 'customer@test.com',
                'password': 'password123',
                'name': 'John Customer',
                'phone': '1234567890',
                'role': User.ROLE_CUSTOMER,
                'pincode': '12345',
                'address': '123 Main St',
                'verified': True
            }
            User.create(customer_data)
            click.echo('✓ Created customer: customer@test.com')
        
        # Sample vendor
        if not User.find_by_email('vendor@test.com'):
            vendor_user_data = {
                'email': 'vendor@test.com',
                'password': 'password123',
                'name': 'Mike Vendor',
                'phone': '9876543210',
                'role': User.ROLE_VENDOR,
                'pincode': '12345',
                'address': '456 Service Ave',
                'verified': True
            }
            vendor_user_id = User.create(vendor_user_data)
            
            # Create vendor profile
            vendor_profile_data = {
                'user_id': vendor_user_id,
                'name': 'Mike Vendor',
                'services': ['Plumbing - Leak Repair', 'Electrical - Wiring'],
                'pincodes': ['12345', '12346', '12347'],
                'onboarding_status': Vendor.STATUS_APPROVED,
                'availability': True
            }
            Vendor.create(vendor_profile_data)
            click.echo('✓ Created vendor: vendor@test.com')
        
        # Sample onboard manager
        if not User.find_by_email('onboard@test.com'):
            onboard_data = {
                'email': 'onboard@test.com',
                'password': 'password123',
                'name': 'Sarah Onboard',
                'phone': '5551234567',
                'role': User.ROLE_ONBOARD_MANAGER,
                'verified': True
            }
            User.create(onboard_data)
            click.echo('✓ Created onboard manager: onboard@test.com')
        
        # Sample ops manager
        if not User.find_by_email('ops@test.com'):
            ops_data = {
                'email': 'ops@test.com',
                'password': 'password123',
                'name': 'Tom Operations',
                'phone': '5559876543',
                'role': User.ROLE_OPS_MANAGER,
                'verified': True
            }
            User.create(ops_data)
            click.echo('✓ Created ops manager: ops@test.com')
        
        click.echo('\n✅ Database seeded successfully!')
        click.echo('\nSample Credentials:')
        click.echo('  Customer: customer@test.com / password123')
        click.echo('  Vendor: vendor@test.com / password123')
        click.echo('  Onboard Manager: onboard@test.com / password123')
        click.echo('  Ops Manager: ops@test.com / password123')
        
    except Exception as e:
        click.echo(f'\n❌ Error seeding database: {str(e)}', err=True)

