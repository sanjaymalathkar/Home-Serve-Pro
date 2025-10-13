"""
Signature workflow routes for HomeServe Pro.
Handles mandatory e-signature workflow for completed jobs.
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.booking import Booking
from app.models.vendor import Vendor
from app.models.signature import Signature
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.utils.decorators import vendor_required, customer_required
from app.utils.error_handlers import api_error_response, api_success_response
from app import socketio
from datetime import datetime, timedelta
import hashlib

signature_bp = Blueprint('signature', __name__)


@signature_bp.route('/job/complete_and_request_signature', methods=['POST'])
@vendor_required
def complete_and_request_signature(user):
    """
    Mark job as completed and automatically request customer signature.
    
    Request Body:
        - booking_id: Booking ID to complete
        - before_photos: List of before photo URLs (optional)
        - after_photos: List of after photo URLs (optional)
        - completion_notes: Notes about the completed work (optional)
    """
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        
        if not booking_id:
            return api_error_response('Booking ID is required', 400)
        
        # Get and validate booking
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)
        
        # Verify vendor owns this booking
        if str(booking['vendor_id']) != str(user['_id']):
            return api_error_response('Access denied', 403)
        
        # Verify booking can be completed
        if booking['status'] not in [Booking.STATUS_ACCEPTED, Booking.STATUS_IN_PROGRESS]:
            return api_error_response('Booking cannot be completed from current status', 400)
        
        # Update booking with completion data
        update_data = {
            'status': Booking.STATUS_COMPLETED,
            'completed_at': datetime.utcnow(),
            'completion_notes': data.get('completion_notes', '')
        }
        
        # Add photos if provided
        if data.get('before_photos'):
            update_data['before_photos'] = data['before_photos']
        if data.get('after_photos'):
            update_data['after_photos'] = data['after_photos']
        
        # Update booking
        Booking.update(booking_id, update_data)
        
        # Request signature with 48-hour timeout
        signature_requested = Booking.request_signature(booking_id, timeout_hours=48)
        
        if signature_requested:
            # Get customer info for notification
            customer = User.find_by_id(booking['customer_id'])
            if customer:
                # Create notification for customer
                Notification.create({
                    'user_id': str(customer['_id']),
                    'type': Notification.TYPE_SIGNATURE_REQUIRED,
                    'title': 'Signature Required',
                    'message': f'Please review and sign off on your completed service: {booking.get("service_name", "Service")}',
                    'data': {
                        'booking_id': booking_id,
                        'vendor_name': user.get('name', 'Vendor'),
                        'service_name': booking.get('service_name', 'Service')
                    }
                })
                
                # Send real-time notification
                socketio.emit('signature_required', {
                    'booking_id': booking_id,
                    'vendor_name': user.get('name', 'Vendor'),
                    'service_name': booking.get('service_name', 'Service'),
                    'timeout_hours': 48
                }, room=str(customer['_id']))
        
        # Log the completion and signature request
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={
                'status_changed_to': 'completed',
                'signature_requested': signature_requested,
                'completion_notes': data.get('completion_notes', '')
            },
            ip_address=request.remote_addr
        )
        
        return api_success_response({
            'message': 'Job completed and signature requested',
            'booking_id': booking_id,
            'signature_requested': signature_requested,
            'signature_timeout_hours': 48
        })
        
    except Exception as e:
        return api_error_response(f'Failed to complete job: {str(e)}', 500)


@signature_bp.route('/job/signature_submit', methods=['POST'])
@customer_required
def submit_signature(user):
    """
    Submit customer signature for completed job.
    
    Request Body:
        - booking_id: Booking ID to sign
        - signature_data: Base64 encoded signature image
        - satisfaction_rating: Rating from 1-5 (optional)
        - feedback: Customer feedback (optional)
        - confirmation_text: Required confirmation text
    """
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        signature_data = data.get('signature_data')
        confirmation_text = data.get('confirmation_text', '')
        
        if not booking_id:
            return api_error_response('Booking ID is required', 400)
        
        if not signature_data:
            return api_error_response('Signature data is required', 400)
        
        # Validate confirmation text
        required_confirmation = "I confirm the service met my expectations"
        if required_confirmation.lower() not in confirmation_text.lower():
            return api_error_response('Please confirm the service met your expectations', 400)
        
        # Get and validate booking
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)
        
        # Verify customer owns this booking
        if str(booking['customer_id']) != str(user['_id']):
            return api_error_response('Access denied', 403)
        
        # Verify booking is completed and signature is required
        if booking['status'] != Booking.STATUS_COMPLETED:
            return api_error_response('Booking must be completed before signing', 400)
        
        if booking.get('signature_status') not in ['unsigned', 'requested']:
            return api_error_response('Signature not required or already submitted', 400)
        
        # Check if signature request has expired
        if booking.get('signature_timeout_at'):
            timeout_at = booking['signature_timeout_at']
            if isinstance(timeout_at, str):
                timeout_at = datetime.fromisoformat(timeout_at.replace('Z', '+00:00'))
            
            if datetime.utcnow() > timeout_at:
                return api_error_response('Signature request has expired. Please contact support.', 400)
        
        # Create signature record
        signature_content = f"{booking_id}{user['_id']}{datetime.utcnow().isoformat()}{confirmation_text}"
        signature_hash = hashlib.sha256(signature_content.encode()).hexdigest()
        
        signature_data_record = {
            'booking_id': booking_id,
            'customer_id': str(user['_id']),
            'vendor_id': str(booking['vendor_id']),
            'signature_data': signature_data,
            'signature_hash': signature_hash,
            'satisfaction_rating': data.get('satisfaction_rating'),
            'feedback': data.get('feedback', ''),
            'confirmation_text': confirmation_text,
            'signed_at': datetime.utcnow()
        }
        
        signature_id = Signature.create(signature_data_record)
        
        # Update booking with signature
        signature_submitted = Booking.submit_signature(booking_id, signature_hash)
        
        if signature_submitted:
            # Create notification for vendor
            vendor = User.find_by_id(booking['vendor_id'])
            if vendor:
                Notification.create({
                    'user_id': str(vendor['_id']),
                    'type': Notification.TYPE_SIGNATURE_COMPLETED,
                    'title': 'Customer Signed Off',
                    'message': f'Customer has signed off on completed service: {booking.get("service_name", "Service")}',
                    'data': {
                        'booking_id': booking_id,
                        'customer_name': user.get('name', 'Customer'),
                        'signature_id': signature_id,
                        'satisfaction_rating': data.get('satisfaction_rating')
                    }
                })
                
                # Send real-time notification
                socketio.emit('signature_completed', {
                    'booking_id': booking_id,
                    'customer_name': user.get('name', 'Customer'),
                    'signature_id': signature_id,
                    'satisfaction_rating': data.get('satisfaction_rating')
                }, room=str(vendor['_id']))
        
        # Log signature submission
        AuditLog.log(
            action=AuditLog.ACTION_SIGNATURE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={
                'signature_hash': signature_hash,
                'signature_id': signature_id,
                'satisfaction_rating': data.get('satisfaction_rating'),
                'confirmation_text': confirmation_text
            },
            ip_address=request.remote_addr
        )
        
        return api_success_response({
            'message': 'Signature submitted successfully',
            'booking_id': booking_id,
            'signature_id': signature_id,
            'signature_hash': signature_hash,
            'status': 'verified'
        })
        
    except Exception as e:
        return api_error_response(f'Failed to submit signature: {str(e)}', 500)


@signature_bp.route('/job/signature_status/<booking_id>', methods=['GET'])
@jwt_required()
def get_signature_status(booking_id):
    """Get signature status for a booking."""
    try:
        current_user_id = get_jwt_identity()
        
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)
        
        # Verify user has access to this booking
        user_id_str = str(current_user_id)
        if (str(booking['customer_id']) != user_id_str and 
            str(booking.get('vendor_id', '')) != user_id_str):
            return api_error_response('Access denied', 403)
        
        signature_info = {
            'booking_id': booking_id,
            'status': booking['status'],
            'signature_status': booking.get('signature_status', 'unsigned'),
            'signature_requested_at': booking.get('signature_requested_at'),
            'signature_submitted_at': booking.get('signature_submitted_at'),
            'signature_timeout_at': booking.get('signature_timeout_at'),
            'signature_escalated': booking.get('signature_escalated', False),
            'requires_signature': (
                booking['status'] == Booking.STATUS_COMPLETED and 
                booking.get('signature_status', 'unsigned') in ['unsigned', 'requested']
            )
        }
        
        # Add time remaining if signature is requested
        if (booking.get('signature_status') == 'requested' and 
            booking.get('signature_timeout_at')):
            timeout_at = booking['signature_timeout_at']
            if isinstance(timeout_at, str):
                timeout_at = datetime.fromisoformat(timeout_at.replace('Z', '+00:00'))
            
            time_remaining = timeout_at - datetime.utcnow()
            signature_info['hours_remaining'] = max(0, time_remaining.total_seconds() / 3600)
        
        return api_success_response(signature_info)
        
    except Exception as e:
        return api_error_response(f'Failed to get signature status: {str(e)}', 500)
