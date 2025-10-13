"""
Customer routes for HomeServe Pro.
Handles customer-specific operations like booking services, viewing history, and signing.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.booking import Booking
from app.models.service import Service
from app.models.vendor import Vendor
from app.models.signature import Signature
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.utils.decorators import customer_required
from app.utils.error_handlers import api_error_response, api_success_response
from app import socketio
from datetime import datetime

customer_bp = Blueprint('customer', __name__)


@customer_bp.route('/services', methods=['GET'])
@jwt_required()
def get_services():
    """Get all available services with optional search."""
    try:
        query = request.args.get('q', '')
        pincode = request.args.get('pincode', '')
        
        if query:
            services = Service.search(query, pincode)
        else:
            services = Service.find_all_active()
        
        return api_success_response([Service.to_dict(s) for s in services])
        
    except Exception as e:
        return api_error_response(f'Failed to get services: {str(e)}', 500)


@customer_bp.route('/bookings', methods=['POST'])
@customer_required
def create_booking(user):
    """
    Create a new service booking.
    
    Request Body:
        - service_id: Service ID
        - service_date: Date of service
        - service_time: Time of service
        - address: Service address
        - pincode: Service pincode
        - description: Optional description
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['service_id', 'service_date', 'service_time', 'address', 'pincode']
        for field in required_fields:
            if field not in data:
                return api_error_response(f'Missing required field: {field}', 400)
        
        # Verify service exists
        service = Service.find_by_id(data['service_id'])
        if not service:
            return api_error_response('Service not found', 404)

        # Find available vendor (optional - booking can be created without vendor)
        vendors = Vendor.find_available_by_service(service['name'], data['pincode'])

        vendor_id = None
        vendor_assigned = False

        if vendors:
            # Select best vendor (highest rating)
            best_vendor = max(vendors, key=lambda v: v.get('ratings', 0))
            vendor_id = str(best_vendor['_id'])
            vendor_assigned = True

        # Create booking (with or without vendor)
        booking_data = {
            'customer_id': str(user['_id']),
            'vendor_id': vendor_id,
            'service_id': data['service_id'],
            'service_name': service.get('name', 'Service'),
            'service_date': data['service_date'],
            'service_time': data['service_time'],
            'address': data['address'],
            'pincode': data['pincode'],
            'description': data.get('description', ''),
            'amount': service.get('base_price', 0),
            'status': Booking.STATUS_PENDING
        }

        booking_id = Booking.create(booking_data)

        # Create notification for vendor if assigned
        if vendor_assigned and vendor_id:
            try:
                Notification.create({
                    'user_id': str(best_vendor['user_id']),
                    'type': Notification.TYPE_BOOKING_CREATED,
                    'title': 'New Booking Request',
                    'message': f'New booking for {service["name"]}',
                    'data': {'booking_id': booking_id}
                })

                # Emit real-time notification
                socketio.emit('new_booking', {
                    'booking_id': booking_id,
                    'vendor_id': str(best_vendor['user_id'])
                }, room=str(best_vendor['user_id']))
            except Exception as e:
                print(f"Failed to notify vendor: {e}")
        
        # Log booking creation
        AuditLog.log(
            action=AuditLog.ACTION_CREATE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={'service': service['name']},
            ip_address=request.remote_addr
        )
        
        return api_success_response({
            'booking_id': booking_id,
            'vendor_name': best_vendor.get('name')
        }, 'Booking created successfully', 201)
        
    except Exception as e:
        return api_error_response(f'Failed to create booking: {str(e)}', 500)


@customer_bp.route('/bookings', methods=['GET'])
@customer_required
def get_bookings(user):
    """Get all bookings for the customer."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit
        
        bookings = Booking.find_by_customer(str(user['_id']), skip, limit)
        total = Booking.count({'customer_id': user['_id']})
        
        return api_success_response({
            'bookings': [Booking.to_dict(b) for b in bookings],
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get bookings: {str(e)}', 500)


@customer_bp.route('/bookings/<booking_id>', methods=['GET'])
@customer_required
def get_booking(user, booking_id):
    """Get specific booking details."""
    try:
        booking = Booking.find_by_id(booking_id)
        
        if not booking:
            return api_error_response('Booking not found', 404)
        
        # Verify booking belongs to customer
        if str(booking['customer_id']) != str(user['_id']):
            return api_error_response('Access denied', 403)
        
        return api_success_response(Booking.to_dict(booking))
        
    except Exception as e:
        return api_error_response(f'Failed to get booking: {str(e)}', 500)


@customer_bp.route('/bookings/<booking_id>/sign', methods=['POST'])
@customer_required
def sign_booking(user, booking_id):
    """
    Sign satisfaction for completed booking.
    
    Request Body:
        - signature_data: Base64 encoded signature image
        - satisfied: Boolean indicating satisfaction
    """
    try:
        booking = Booking.find_by_id(booking_id)
        
        if not booking:
            return api_error_response('Booking not found', 404)
        
        # Verify booking belongs to customer
        if str(booking['customer_id']) != str(user['_id']):
            return api_error_response('Access denied', 403)
        
        # Verify booking is completed
        if booking['status'] != Booking.STATUS_COMPLETED:
            return api_error_response('Booking must be completed before signing', 400)
        
        # Check if already signed
        if booking.get('signature_status') == 'signed':
            return api_error_response('Booking already signed', 400)
        
        data = request.get_json()
        
        # Create signature
        signature_data = {
            'booking_id': booking_id,
            'customer_id': str(user['_id']),
            'vendor_id': str(booking['vendor_id']),
            'signature_data': data.get('signature_data', ''),
            'satisfied': data.get('satisfied', True)
        }
        
        signature_id = Signature.create(signature_data)
        signature = Signature.find_by_id(signature_id)
        
        # Update booking
        Booking.update(booking_id, {
            'signature_status': 'signed',
            'signature_hash': signature['signature_hash'],
            'status': Booking.STATUS_VERIFIED
        })
        
        # Create notification for vendor
        Notification.create({
            'user_id': str(booking['vendor_id']),
            'type': Notification.TYPE_SIGNATURE_COMPLETED,
            'title': 'Customer Signed Satisfaction',
            'message': 'Customer has signed the satisfaction document',
            'data': {'booking_id': booking_id}
        })
        
        # Emit real-time notification
        socketio.emit('signature_completed', {
            'booking_id': booking_id
        }, room=str(booking['vendor_id']))
        
        # Log signature
        AuditLog.log(
            action=AuditLog.ACTION_SIGNATURE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={'signature_hash': signature['signature_hash']},
            ip_address=request.remote_addr
        )
        
        return api_success_response({
            'signature_id': signature_id,
            'signature_hash': signature['signature_hash']
        }, 'Signature recorded successfully')
        
    except Exception as e:
        return api_error_response(f'Failed to sign booking: {str(e)}', 500)


@customer_bp.route('/bookings/<booking_id>/rate', methods=['POST'])
@customer_required
def rate_booking(user, booking_id):
    """
    Rate and review a completed booking.
    
    Request Body:
        - rating: Rating (1-5)
        - review: Optional review text
    """
    try:
        booking = Booking.find_by_id(booking_id)
        
        if not booking:
            return api_error_response('Booking not found', 404)
        
        # Verify booking belongs to customer
        if str(booking['customer_id']) != str(user['_id']):
            return api_error_response('Access denied', 403)
        
        # Verify booking is verified
        if booking['status'] != Booking.STATUS_VERIFIED:
            return api_error_response('Booking must be verified before rating', 400)
        
        data = request.get_json()
        rating = data.get('rating')
        
        if not rating or rating < 1 or rating > 5:
            return api_error_response('Rating must be between 1 and 5', 400)
        
        # Update booking with rating
        Booking.update(booking_id, {
            'rating': rating,
            'review': data.get('review', '')
        })
        
        # Update vendor rating
        Vendor.update_rating(str(booking['vendor_id']), rating)
        
        return api_success_response(message='Rating submitted successfully')
        
    except Exception as e:
        return api_error_response(f'Failed to rate booking: {str(e)}', 500)


@customer_bp.route('/notifications', methods=['GET'])
@customer_required
def get_notifications(user):
    """Get customer notifications."""
    try:
        unread_only = request.args.get('unread', 'false').lower() == 'true'
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit
        
        notifications = Notification.find_by_user(str(user['_id']), unread_only, skip, limit)
        unread_count = Notification.count_unread(str(user['_id']))
        
        return api_success_response({
            'notifications': [Notification.to_dict(n) for n in notifications],
            'unread_count': unread_count
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get notifications: {str(e)}', 500)


@customer_bp.route('/notifications/<notification_id>/read', methods=['POST'])
@customer_required
def mark_notification_read(user, notification_id):
    """Mark notification as read."""
    try:
        Notification.mark_as_read(notification_id)
        return api_success_response(message='Notification marked as read')
        
    except Exception as e:
        return api_error_response(f'Failed to mark notification: {str(e)}', 500)

