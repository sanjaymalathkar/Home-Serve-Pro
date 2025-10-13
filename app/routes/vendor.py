"""
Vendor routes for HomeServe Pro.
Handles vendor-specific operations like managing bookings, uploading photos, and requesting signatures.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.models.user import User
from app.models.booking import Booking
from app.models.vendor import Vendor
from app.models.signature import Signature
from app.models.payment import Payment
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.utils.decorators import vendor_required
from app.utils.error_handlers import api_error_response, api_success_response
from app.utils.file_upload import save_image, get_file_url
from app import socketio

vendor_bp = Blueprint('vendor', __name__)


@vendor_bp.route('/profile', methods=['GET'])
@vendor_required
def get_profile(user):
    """Get vendor profile."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        
        if not vendor:
            return api_error_response('Vendor profile not found', 404)
        
        return api_success_response(Vendor.to_dict(vendor))
        
    except Exception as e:
        return api_error_response(f'Failed to get profile: {str(e)}', 500)


@vendor_bp.route('/availability', methods=['POST'])
@vendor_required
def toggle_availability(user):
    """Toggle vendor availability status."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        
        if not vendor:
            return api_error_response('Vendor profile not found', 404)
        
        Vendor.toggle_availability(str(vendor['_id']))
        updated_vendor = Vendor.find_by_id(str(vendor['_id']))
        
        # Log availability change
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='vendor',
            entity_id=str(vendor['_id']),
            user_id=str(user['_id']),
            details={'availability': updated_vendor['availability']},
            ip_address=request.remote_addr
        )
        
        return api_success_response({
            'availability': updated_vendor['availability']
        }, 'Availability updated successfully')
        
    except Exception as e:
        return api_error_response(f'Failed to update availability: {str(e)}', 500)


@vendor_bp.route('/bookings', methods=['GET'])
@vendor_required
def get_bookings(user):
    """Get all bookings for the vendor."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        
        if not vendor:
            return api_error_response('Vendor profile not found', 404)
        
        status = request.args.get('status', '')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit
        
        if status:
            bookings = Booking.find_by_status(status, skip, limit)
            bookings = [b for b in bookings if str(b['vendor_id']) == str(vendor['_id'])]
            total = len(bookings)
        else:
            bookings = Booking.find_by_vendor(str(vendor['_id']), skip, limit)
            total = Booking.count({'vendor_id': vendor['_id']})
        
        return api_success_response({
            'bookings': [Booking.to_dict(b) for b in bookings],
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get bookings: {str(e)}', 500)


@vendor_bp.route('/bookings/<booking_id>/accept', methods=['POST'])
@vendor_required
def accept_booking(user, booking_id):
    """Accept a booking request."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        booking = Booking.find_by_id(booking_id)
        
        if not booking:
            return api_error_response('Booking not found', 404)
        
        # Verify booking belongs to vendor
        if str(booking['vendor_id']) != str(vendor['_id']):
            return api_error_response('Access denied', 403)
        
        # Update booking status
        Booking.update_status(booking_id, Booking.STATUS_ACCEPTED)
        
        # Create notification for customer
        Notification.create({
            'user_id': str(booking['customer_id']),
            'type': Notification.TYPE_BOOKING_ACCEPTED,
            'title': 'Booking Accepted',
            'message': f'{vendor["name"]} has accepted your booking',
            'data': {'booking_id': booking_id}
        })
        
        # Emit real-time notification
        socketio.emit('booking_accepted', {
            'booking_id': booking_id
        }, room=str(booking['customer_id']))
        
        # Log acceptance
        AuditLog.log(
            action=AuditLog.ACTION_STATUS_CHANGE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={'status': 'accepted'},
            ip_address=request.remote_addr
        )
        
        return api_success_response(message='Booking accepted successfully')
        
    except Exception as e:
        return api_error_response(f'Failed to accept booking: {str(e)}', 500)


@vendor_bp.route('/bookings/<booking_id>/reject', methods=['POST'])
@vendor_required
def reject_booking(user, booking_id):
    """Reject a booking request."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        booking = Booking.find_by_id(booking_id)
        
        if not booking:
            return api_error_response('Booking not found', 404)
        
        # Verify booking belongs to vendor
        if str(booking['vendor_id']) != str(vendor['_id']):
            return api_error_response('Access denied', 403)
        
        # Update booking status
        Booking.update_status(booking_id, Booking.STATUS_REJECTED)
        
        # Create notification for customer
        Notification.create({
            'user_id': str(booking['customer_id']),
            'type': Notification.TYPE_BOOKING_REJECTED,
            'title': 'Booking Rejected',
            'message': 'Your booking request was rejected',
            'data': {'booking_id': booking_id}
        })
        
        # Emit real-time notification
        socketio.emit('booking_rejected', {
            'booking_id': booking_id
        }, room=str(booking['customer_id']))
        
        return api_success_response(message='Booking rejected')
        
    except Exception as e:
        return api_error_response(f'Failed to reject booking: {str(e)}', 500)


@vendor_bp.route('/bookings/<booking_id>/start', methods=['POST'])
@vendor_required
def start_booking(user, booking_id):
    """Mark booking as in progress."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        booking = Booking.find_by_id(booking_id)
        
        if not booking:
            return api_error_response('Booking not found', 404)
        
        if str(booking['vendor_id']) != str(vendor['_id']):
            return api_error_response('Access denied', 403)
        
        Booking.update_status(booking_id, Booking.STATUS_IN_PROGRESS)
        
        return api_success_response(message='Booking started')
        
    except Exception as e:
        return api_error_response(f'Failed to start booking: {str(e)}', 500)


@vendor_bp.route('/bookings/<booking_id>/complete', methods=['POST'])
@vendor_required
def complete_booking(user, booking_id):
    """Mark booking as completed."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        booking = Booking.find_by_id(booking_id)
        
        if not booking:
            return api_error_response('Booking not found', 404)
        
        if str(booking['vendor_id']) != str(vendor['_id']):
            return api_error_response('Access denied', 403)
        
        # Verify photos are uploaded
        if not booking.get('after_photos'):
            return api_error_response('Please upload after photos before completing', 400)
        
        Booking.update_status(booking_id, Booking.STATUS_COMPLETED)
        
        # Create notification for customer
        Notification.create({
            'user_id': str(booking['customer_id']),
            'type': Notification.TYPE_BOOKING_COMPLETED,
            'title': 'Service Completed',
            'message': 'Your service has been completed. Please review and sign.',
            'data': {'booking_id': booking_id}
        })
        
        return api_success_response(message='Booking completed')
        
    except Exception as e:
        return api_error_response(f'Failed to complete booking: {str(e)}', 500)


@vendor_bp.route('/bookings/<booking_id>/photos', methods=['POST'])
@vendor_required
def upload_photos(user, booking_id):
    """
    Upload before/after photos for a booking.
    
    Form Data:
        - photo: Image file
        - type: 'before' or 'after'
    """
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        booking = Booking.find_by_id(booking_id)
        
        if not booking:
            return api_error_response('Booking not found', 404)
        
        if str(booking['vendor_id']) != str(vendor['_id']):
            return api_error_response('Access denied', 403)
        
        # Get photo file
        if 'photo' not in request.files:
            return api_error_response('No photo file provided', 400)
        
        photo = request.files['photo']
        photo_type = request.form.get('type', 'before')
        
        if photo_type not in ['before', 'after']:
            return api_error_response('Photo type must be "before" or "after"', 400)
        
        # Save photo
        photo_path = save_image(photo, subfolder=f'bookings/{booking_id}')
        
        if not photo_path:
            return api_error_response('Failed to save photo', 500)
        
        # Add photo to booking
        photo_url = get_file_url(photo_path)
        Booking.add_photo(booking_id, photo_url, photo_type)
        
        return api_success_response({
            'photo_url': photo_url,
            'type': photo_type
        }, 'Photo uploaded successfully')
        
    except Exception as e:
        return api_error_response(f'Failed to upload photo: {str(e)}', 500)


@vendor_bp.route('/bookings/<booking_id>/request-signature', methods=['POST'])
@vendor_required
def request_signature(user, booking_id):
    """Request customer signature for completed booking."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        booking = Booking.find_by_id(booking_id)
        
        if not booking:
            return api_error_response('Booking not found', 404)
        
        if str(booking['vendor_id']) != str(vendor['_id']):
            return api_error_response('Access denied', 403)
        
        if booking['status'] != Booking.STATUS_COMPLETED:
            return api_error_response('Booking must be completed first', 400)
        
        # Create notification for customer
        Notification.create({
            'user_id': str(booking['customer_id']),
            'type': Notification.TYPE_SIGNATURE_REQUEST,
            'title': 'Signature Required',
            'message': f'{vendor["name"]} is requesting your satisfaction signature',
            'data': {'booking_id': booking_id}
        })
        
        # Emit real-time notification
        socketio.emit('signature_request', {
            'booking_id': booking_id
        }, room=str(booking['customer_id']))
        
        return api_success_response(message='Signature request sent to customer')
        
    except Exception as e:
        return api_error_response(f'Failed to request signature: {str(e)}', 500)


@vendor_bp.route('/earnings', methods=['GET'])
@vendor_required
def get_earnings(user):
    """Get vendor earnings summary."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        
        if not vendor:
            return api_error_response('Vendor profile not found', 404)
        
        total_earnings = Payment.get_vendor_earnings(str(vendor['_id']))
        
        return api_success_response({
            'total_earnings': total_earnings,
            'completed_jobs': vendor.get('completed_jobs', 0),
            'rating': vendor.get('ratings', 0.0),
            'total_ratings': vendor.get('total_ratings', 0)
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get earnings: {str(e)}', 500)


@vendor_bp.route('/payments', methods=['GET'])
@vendor_required
def get_payments(user):
    """Get vendor payment history."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        
        if not vendor:
            return api_error_response('Vendor profile not found', 404)
        
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit
        
        payments = Payment.find_by_vendor(str(vendor['_id']), skip, limit)
        total = Payment.count({'vendor_id': vendor['_id']})
        
        return api_success_response({
            'payments': [Payment.to_dict(p) for p in payments],
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get payments: {str(e)}', 500)

