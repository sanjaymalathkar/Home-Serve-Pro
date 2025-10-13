"""
Ops Manager routes for HomeServe Pro.
Handles live job monitoring, payment approvals, and operational oversight.
"""

from flask import Blueprint, request
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.vendor import Vendor
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.utils.decorators import ops_manager_required
from app.utils.error_handlers import api_error_response, api_success_response
from datetime import datetime, timedelta

ops_manager_bp = Blueprint('ops_manager', __name__)


@ops_manager_bp.route('/bookings/live', methods=['GET'])
@ops_manager_required
def get_live_bookings(user):
    """Get all active/in-progress bookings."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        skip = (page - 1) * limit
        
        # Get bookings that are not completed or cancelled
        active_statuses = [
            Booking.STATUS_PENDING,
            Booking.STATUS_ACCEPTED,
            Booking.STATUS_IN_PROGRESS
        ]
        
        bookings = Booking.find_all(
            {'status': {'$in': active_statuses}},
            skip,
            limit
        )
        total = Booking.count({'status': {'$in': active_statuses}})
        
        return api_success_response({
            'bookings': [Booking.to_dict(b) for b in bookings],
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get live bookings: {str(e)}', 500)


@ops_manager_bp.route('/bookings/pending-signatures', methods=['GET'])
@ops_manager_required
def get_pending_signatures(user):
    """Get bookings with pending signatures."""
    try:
        days = int(request.args.get('days', 2))
        bookings = Booking.get_pending_signatures(days)
        
        return api_success_response({
            'bookings': [Booking.to_dict(b) for b in bookings],
            'count': len(bookings)
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get pending signatures: {str(e)}', 500)


@ops_manager_bp.route('/payments/pending', methods=['GET'])
@ops_manager_required
def get_pending_payments(user):
    """Get all pending payment approvals."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit
        
        payments = Payment.find_all(
            {'status': Payment.STATUS_PENDING},
            skip,
            limit
        )
        total = Payment.count({'status': Payment.STATUS_PENDING})
        
        return api_success_response({
            'payments': [Payment.to_dict(p) for p in payments],
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get pending payments: {str(e)}', 500)


@ops_manager_bp.route('/payments/<payment_id>/approve', methods=['POST'])
@ops_manager_required
def approve_payment(user, payment_id):
    """
    Manually approve a payment.
    
    Request Body:
        - notes: Optional approval notes
    """
    try:
        payment = Payment.find_by_id(payment_id)
        
        if not payment:
            return api_error_response('Payment not found', 404)
        
        if payment['status'] != Payment.STATUS_PENDING:
            return api_error_response('Payment is not pending approval', 400)
        
        data = request.get_json() or {}
        
        # Update payment status
        Payment.update(payment_id, {
            'status': Payment.STATUS_COMPLETED,
            'approved_by': str(user['_id']),
            'approval_notes': data.get('notes', ''),
            'completed_at': datetime.utcnow()
        })
        
        # If it's a payout, update vendor earnings
        if payment['payment_type'] == Payment.TYPE_PAYOUT:
            Vendor.add_earnings(str(payment['vendor_id']), payment['amount'])
            
            # Notify vendor
            Notification.create({
                'user_id': str(payment['vendor_id']),
                'type': Notification.TYPE_PAYMENT_RELEASED,
                'title': 'Payment Released',
                'message': f'Payment of ${payment["amount"]} has been released',
                'data': {'payment_id': payment_id, 'amount': payment['amount']}
            })
        
        # Log approval
        AuditLog.log(
            action=AuditLog.ACTION_PAYMENT,
            entity_type='payment',
            entity_id=payment_id,
            user_id=str(user['_id']),
            details={'action': 'approved', 'amount': payment['amount']},
            ip_address=request.remote_addr
        )
        
        return api_success_response(message='Payment approved successfully')
        
    except Exception as e:
        return api_error_response(f'Failed to approve payment: {str(e)}', 500)


@ops_manager_bp.route('/dashboard/stats', methods=['GET'])
@ops_manager_required
def get_dashboard_stats(user):
    """Get operational dashboard statistics."""
    try:
        # Booking stats
        total_bookings = Booking.count({})
        pending_bookings = Booking.count({'status': Booking.STATUS_PENDING})
        in_progress_bookings = Booking.count({'status': Booking.STATUS_IN_PROGRESS})
        completed_today = Booking.count({
            'status': Booking.STATUS_VERIFIED,
            'updated_at': {'$gte': datetime.utcnow().replace(hour=0, minute=0, second=0)}
        })
        
        # Signature stats
        pending_signatures = len(Booking.get_pending_signatures(2))
        
        # Payment stats
        pending_payments = Payment.count({'status': Payment.STATUS_PENDING})
        
        # Vendor stats
        active_vendors = Vendor.count({
            'onboarding_status': Vendor.STATUS_APPROVED,
            'availability': True
        })
        
        return api_success_response({
            'bookings': {
                'total': total_bookings,
                'pending': pending_bookings,
                'in_progress': in_progress_bookings,
                'completed_today': completed_today
            },
            'signatures': {
                'pending': pending_signatures
            },
            'payments': {
                'pending': pending_payments
            },
            'vendors': {
                'active': active_vendors
            }
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get stats: {str(e)}', 500)


@ops_manager_bp.route('/bookings/<booking_id>', methods=['GET'])
@ops_manager_required
def get_booking_details(user, booking_id):
    """Get detailed booking information."""
    try:
        booking = Booking.find_by_id(booking_id)
        
        if not booking:
            return api_error_response('Booking not found', 404)
        
        # Enrich with customer and vendor data
        booking_dict = Booking.to_dict(booking)
        
        customer = User.find_by_id(str(booking['customer_id']))
        if customer:
            booking_dict['customer'] = User.to_dict(customer)
        
        vendor = Vendor.find_by_id(str(booking['vendor_id']))
        if vendor:
            booking_dict['vendor'] = Vendor.to_dict(vendor)
            vendor_user = User.find_by_id(str(vendor['user_id']))
            if vendor_user:
                booking_dict['vendor']['user'] = User.to_dict(vendor_user)
        
        return api_success_response(booking_dict)
        
    except Exception as e:
        return api_error_response(f'Failed to get booking details: {str(e)}', 500)


@ops_manager_bp.route('/alerts', methods=['GET'])
@ops_manager_required
def get_alerts(user):
    """Get operational alerts (pending signatures, delayed bookings, etc.)."""
    try:
        alerts = []
        
        # Pending signatures alert
        pending_sigs = Booking.get_pending_signatures(2)
        if pending_sigs:
            alerts.append({
                'type': 'pending_signatures',
                'severity': 'warning',
                'count': len(pending_sigs),
                'message': f'{len(pending_sigs)} bookings have pending signatures for 48+ hours'
            })
        
        # Pending payments alert
        pending_payments_count = Payment.count({'status': Payment.STATUS_PENDING})
        if pending_payments_count > 0:
            alerts.append({
                'type': 'pending_payments',
                'severity': 'info',
                'count': pending_payments_count,
                'message': f'{pending_payments_count} payments pending approval'
            })
        
        # Pending bookings alert
        pending_bookings_count = Booking.count({'status': Booking.STATUS_PENDING})
        if pending_bookings_count > 10:
            alerts.append({
                'type': 'high_pending_bookings',
                'severity': 'warning',
                'count': pending_bookings_count,
                'message': f'{pending_bookings_count} bookings awaiting vendor acceptance'
            })
        
        return api_success_response({'alerts': alerts})
        
    except Exception as e:
        return api_error_response(f'Failed to get alerts: {str(e)}', 500)


@ops_manager_bp.route('/audit-logs', methods=['GET'])
@ops_manager_required
def get_audit_logs(user):
    """Get audit logs with filters."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))
        skip = (page - 1) * limit
        
        filters = {}
        
        # Optional filters
        if request.args.get('action'):
            filters['action'] = request.args.get('action')
        if request.args.get('entity_type'):
            filters['entity_type'] = request.args.get('entity_type')
        if request.args.get('user_id'):
            filters['user_id'] = request.args.get('user_id')
        
        logs = AuditLog.find_all(filters, skip, limit)
        total = AuditLog.count(filters)
        
        return api_success_response({
            'logs': [AuditLog.to_dict(log) for log in logs],
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get audit logs: {str(e)}', 500)

