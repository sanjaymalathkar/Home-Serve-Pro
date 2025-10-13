"""
Super Admin routes for HomeServe Pro.
Handles system-wide administration, analytics, and user management.
"""

from flask import Blueprint, request
from app.models.user import User
from app.models.vendor import Vendor
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.service import Service
from app.models.audit_log import AuditLog
from app.utils.decorators import super_admin_required
from app.utils.error_handlers import api_error_response, api_success_response
from datetime import datetime, timedelta
from bson import ObjectId

super_admin_bp = Blueprint('super_admin', __name__)


@super_admin_bp.route('/dashboard/analytics', methods=['GET'])
@super_admin_required
def get_analytics(user):
    """Get comprehensive analytics for super admin dashboard."""
    try:
        # Date range
        days = int(request.args.get('days', 30))
        start_date = datetime.utcnow() - timedelta(days=days)

        # User growth
        total_users = User.count({})
        new_users = User.count({'created_at': {'$gte': start_date}})
        customers = User.count({'role': User.ROLE_CUSTOMER})
        vendors = User.count({'role': User.ROLE_VENDOR})

        # Booking stats
        total_bookings = Booking.count({})
        completed_bookings = Booking.count({'status': Booking.STATUS_VERIFIED})
        pending_bookings = Booking.count({'status': Booking.STATUS_PENDING})

        # Revenue calculation (simplified)
        from app import mongo
        revenue_pipeline = [
            {
                '$match': {
                    'status': Payment.STATUS_COMPLETED,
                    'payment_type': Payment.TYPE_BOOKING,
                    'created_at': {'$gte': start_date}
                }
            },
            {
                '$group': {
                    '_id': None,
                    'total_revenue': {'$sum': '$amount'}
                }
            }
        ]
        revenue_result = list(mongo.db['payments'].aggregate(revenue_pipeline))
        total_revenue = revenue_result[0]['total_revenue'] if revenue_result else 0

        # Vendor stats
        active_vendors = Vendor.count({
            'onboarding_status': Vendor.STATUS_APPROVED,
            'availability': True
        })
        pending_vendors = Vendor.count({'onboarding_status': Vendor.STATUS_PENDING})

        # Signature completion rate
        completed_with_signature = Booking.count({
            'status': Booking.STATUS_VERIFIED,
            'signature_status': 'signed'
        })
        signature_rate = (completed_with_signature / completed_bookings * 100) if completed_bookings > 0 else 0

        return api_success_response({
            'users': {
                'total': total_users,
                'new': new_users,
                'customers': customers,
                'vendors': vendors
            },
            'bookings': {
                'total': total_bookings,
                'completed': completed_bookings,
                'pending': pending_bookings
            },
            'revenue': {
                'total': total_revenue,
                'period_days': days
            },
            'vendors': {
                'active': active_vendors,
                'pending': pending_vendors
            },
            'signatures': {
                'completion_rate': round(signature_rate, 2)
            }
        })

    except Exception as e:
        return api_error_response(f'Failed to get analytics: {str(e)}', 500)


@super_admin_bp.route('/users', methods=['GET'])
@super_admin_required
def get_all_users(user):
    """Get all users with filters."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit

        filters = {}

        # Optional filters
        if request.args.get('role'):
            filters['role'] = request.args.get('role')
        if request.args.get('active'):
            filters['active'] = request.args.get('active').lower() == 'true'

        users = User.find_all(filters, skip, limit)
        total = User.count(filters)

        return api_success_response({
            'users': [User.to_dict(u) for u in users],
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })

    except Exception as e:
        return api_error_response(f'Failed to get users: {str(e)}', 500)


@super_admin_bp.route('/users/<user_id>', methods=['GET'])
@super_admin_required
def get_user_details(user, user_id):
    """Get detailed user information."""
    try:
        target_user = User.find_by_id(user_id)

        if not target_user:
            return api_error_response('User not found', 404)

        user_dict = User.to_dict(target_user)

        # If vendor, include vendor profile
        if target_user['role'] == User.ROLE_VENDOR:
            vendor = Vendor.find_by_user_id(user_id)
            if vendor:
                user_dict['vendor_profile'] = Vendor.to_dict(vendor)

        # Include activity stats
        if target_user['role'] == User.ROLE_CUSTOMER:
            user_dict['booking_count'] = Booking.count({'customer_id': ObjectId(user_id)})
        elif target_user['role'] == User.ROLE_VENDOR:
            vendor = Vendor.find_by_user_id(user_id)
            if vendor:
                user_dict['booking_count'] = Booking.count({'vendor_id': vendor['_id']})

        return api_success_response(user_dict)

    except Exception as e:
        return api_error_response(f'Failed to get user details: {str(e)}', 500)


@super_admin_bp.route('/users/<user_id>/toggle-active', methods=['POST'])
@super_admin_required
def toggle_user_active(user, user_id):
    """Activate or deactivate a user account."""
    try:
        target_user = User.find_by_id(user_id)

        if not target_user:
            return api_error_response('User not found', 404)

        # Prevent deactivating self
        if str(user['_id']) == user_id:
            return api_error_response('Cannot deactivate your own account', 400)

        new_status = not target_user.get('active', True)
        User.update(user_id, {'active': new_status})

        # Log action
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='user',
            entity_id=user_id,
            user_id=str(user['_id']),
            details={'action': 'toggle_active', 'new_status': new_status},
            ip_address=request.remote_addr
        )

        return api_success_response({
            'active': new_status
        }, f'User {"activated" if new_status else "deactivated"} successfully')

    except Exception as e:
        return api_error_response(f'Failed to toggle user status: {str(e)}', 500)


@super_admin_bp.route('/services', methods=['GET'])
@super_admin_required
def get_all_services(user):
    """Get all services."""
    try:
        services = Service.find_all_active()
        return api_success_response([Service.to_dict(s) for s in services])

    except Exception as e:
        return api_error_response(f'Failed to get services: {str(e)}', 500)


@super_admin_bp.route('/services', methods=['POST'])
@super_admin_required
def create_service(user):
    """
    Create a new service.

    Request Body:
        - name: Service name
        - description: Service description
        - category: Service category
        - base_price: Base price
        - duration_minutes: Estimated duration
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'description', 'category', 'base_price']
        for field in required_fields:
            if field not in data:
                return api_error_response(f'Missing required field: {field}', 400)

        # Check if service already exists
        if Service.find_by_name(data['name']):
            return api_error_response('Service with this name already exists', 400)

        service_id = Service.create(data)

        # Log creation
        AuditLog.log(
            action=AuditLog.ACTION_CREATE,
            entity_type='service',
            entity_id=service_id,
            user_id=str(user['_id']),
            details={'name': data['name']},
            ip_address=request.remote_addr
        )

        return api_success_response({
            'service_id': service_id
        }, 'Service created successfully', 201)

    except Exception as e:
        return api_error_response(f'Failed to create service: {str(e)}', 500)


@super_admin_bp.route('/services/<service_id>', methods=['GET'])
@super_admin_required
def get_service_details(user, service_id):
    """Get a single service with sub-services and commission."""
    try:
        service = Service.find_by_id(service_id)
        if not service:
            return api_error_response('Service not found', 404)
        return api_success_response(Service.to_dict(service))
    except Exception as e:
        return api_error_response(f'Failed to get service: {str(e)}', 500)


@super_admin_bp.route('/services/<service_id>/sub-services', methods=['POST'])
@super_admin_required
def add_sub_service(user, service_id):
    """Add a sub-service variant under a service."""
    try:
        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        if not name:
            return api_error_response('Sub-service name is required', 400)
        sub = {
            'name': name,
            'base_price': data.get('base_price')
        }
        sub_id = Service.add_sub_service(service_id, sub)
        if not sub_id:
            return api_error_response('Failed to add sub-service', 500)
        AuditLog.log(
            action=AuditLog.ACTION_CREATE,
            entity_type='service_sub',
            entity_id=sub_id,
            user_id=str(user['_id']),
            details={'service_id': service_id, 'name': name},
            ip_address=request.remote_addr
        )
        return api_success_response({'sub_service_id': sub_id}, 'Sub-service added', 201)
    except Exception as e:
        return api_error_response(f'Failed to add sub-service: {str(e)}', 500)


@super_admin_bp.route('/services/<service_id>/sub-services/<sub_id>', methods=['DELETE'])
@super_admin_required
def delete_sub_service(user, service_id, sub_id):
    try:
        ok = Service.remove_sub_service(service_id, sub_id)
        if not ok:
            return api_error_response('Failed to remove sub-service', 500)
        AuditLog.log(
            action=AuditLog.ACTION_DELETE,
            entity_type='service_sub',
            entity_id=sub_id,
            user_id=str(user['_id']),
            details={'service_id': service_id},
            ip_address=request.remote_addr
        )
        return api_success_response(message='Sub-service removed')
    except Exception as e:
        return api_error_response(f'Failed to remove sub-service: {str(e)}', 500)


@super_admin_bp.route('/services/<service_id>/commission', methods=['PUT'])
@super_admin_required
def set_service_commission(user, service_id):
    """Configure commission and cancellation fees for a service."""
    try:
        data = request.get_json() or {}
        ok = Service.set_commission(service_id, data)
        if not ok:
            return api_error_response('Failed to set commission', 500)
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='service',
            entity_id=service_id,
            user_id=str(user['_id']),
            details={'commission_updated': True},
            ip_address=request.remote_addr
        )
        return api_success_response(message='Commission updated')
    except Exception as e:
        return api_error_response(f'Failed to set commission: {str(e)}', 500)


@super_admin_bp.route('/bookings/<booking_id>/confirm', methods=['POST'])
@super_admin_required
def admin_confirm_booking(user, booking_id):
    """Confirm a booking (move from pending to accepted)."""
    try:
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)
        if booking.get('status') != Booking.STATUS_PENDING:
            return api_error_response('Only pending bookings can be confirmed', 400)
        ok = Booking.update_status(booking_id, Booking.STATUS_ACCEPTED)
        if not ok:
            return api_error_response('Failed to confirm booking', 500)
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={'status': Booking.STATUS_ACCEPTED},
            ip_address=request.remote_addr
        )
        return api_success_response(message='Booking confirmed')
    except Exception as e:
        return api_error_response(f'Failed to confirm booking: {str(e)}', 500)


@super_admin_bp.route('/bookings/<booking_id>/refund', methods=['POST'])
@super_admin_required
def admin_refund_booking(user, booking_id):
    """Refund a booking payment and optionally cancel the booking."""
    try:
        data = request.get_json() or {}
        cancel = bool(data.get('cancel', True))
        amount = data.get('amount')
        reason = data.get('reason')

        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)

        # Update payment record
        payment = Payment.find_by_booking(booking_id)
        if payment:
            Payment.update(payment['_id'], {
                'status': Payment.STATUS_REFUNDED,
                'refund_reason': reason,
                'refund_amount': amount,
            })
        # Update booking fields
        update_data = {'payment_status': 'refunded'}
        if cancel and booking.get('status') not in [Booking.STATUS_CANCELLED, Booking.STATUS_VERIFIED]:
            update_data['status'] = Booking.STATUS_CANCELLED
        ok = Booking.update(booking_id, update_data)
        if not ok:
            return api_error_response('Failed to update booking', 500)

        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={'refund': True, 'amount': amount, 'reason': reason, 'cancelled': update_data.get('status') == Booking.STATUS_CANCELLED},
            ip_address=request.remote_addr
        )
        return api_success_response(message='Refund processed')
    except Exception as e:
        return api_error_response(f'Failed to refund booking: {str(e)}', 500)


@super_admin_bp.route('/services/<service_id>', methods=['PUT'])
@super_admin_required
def update_service(user, service_id):
    """Update service details."""
    try:
        service = Service.find_by_id(service_id)

        if not service:
            return api_error_response('Service not found', 404)

        data = request.get_json()
        Service.update(service_id, data)

        # Log update
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='service',
            entity_id=service_id,
            user_id=str(user['_id']),
            details=data,
            ip_address=request.remote_addr
        )

        return api_success_response(message='Service updated successfully')

    except Exception as e:
        return api_error_response(f'Failed to update service: {str(e)}', 500)


@super_admin_bp.route('/payouts/pending', methods=['GET'])
@super_admin_required
def get_pending_payouts(user):
    """Get all pending payout requests."""
    try:
        payouts = Payment.find_pending_payouts()

        # Enrich with vendor data
        enriched_payouts = []
        for payout in payouts:
            payout_dict = Payment.to_dict(payout)
            vendor = Vendor.find_by_id(str(payout['vendor_id']))
            if vendor:
                payout_dict['vendor'] = Vendor.to_dict(vendor)
            enriched_payouts.append(payout_dict)

        return api_success_response({'payouts': enriched_payouts})

    except Exception as e:
        return api_error_response(f'Failed to get pending payouts: {str(e)}', 500)


@super_admin_bp.route('/payouts/<payment_id>/approve', methods=['POST'])
@super_admin_required
def approve_payout(user, payment_id):
    """Approve vendor payout."""
    try:
        payment = Payment.find_by_id(payment_id)

        if not payment:
            return api_error_response('Payment not found', 404)

        if payment['payment_type'] != Payment.TYPE_PAYOUT:
            return api_error_response('This is not a payout request', 400)

        # Update payment status
        Payment.update_status(payment_id, Payment.STATUS_COMPLETED)

        # Update vendor earnings
        Vendor.add_earnings(str(payment['vendor_id']), payment['amount'])

        # Log approval
        AuditLog.log(
            action=AuditLog.ACTION_PAYMENT,
            entity_type='payment',
            entity_id=payment_id,
            user_id=str(user['_id']),
            details={'action': 'payout_approved', 'amount': payment['amount']},
            ip_address=request.remote_addr
        )

        return api_success_response(message='Payout approved successfully')

    except Exception as e:
        return api_error_response(f'Failed to approve payout: {str(e)}', 500)


@super_admin_bp.route('/audit-logs', methods=['GET'])
@super_admin_required
def get_all_audit_logs(user):
    """Get all audit logs with comprehensive filters."""
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
        if request.args.get('entity_id'):
            filters['entity_id'] = request.args.get('entity_id')

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



@super_admin_bp.route('/vendors', methods=['GET'])
@super_admin_required
def admin_get_vendors(user):
    """List vendors with optional filters (onboarding_status, availability)."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit
        filters = {}
        status = request.args.get('onboarding_status')
        if status:
            filters['onboarding_status'] = status
        if request.args.get('availability'):
            val = request.args.get('availability').lower() == 'true'
            filters['availability'] = val
        vendors = Vendor.find_all(filters, skip, limit)
        total = Vendor.count(filters)
        return api_success_response({
            'vendors': [Vendor.to_dict(v) for v in vendors],
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })
    except Exception as e:
        return api_error_response(f'Failed to get vendors: {str(e)}', 500)


@super_admin_bp.route('/vendors/<vendor_id>/set-status', methods=['POST'])
@super_admin_required
def admin_set_vendor_status(user, vendor_id):
    """Approve/Reject/Suspend vendor by setting onboarding_status."""
    try:
        data = request.get_json() or {}
        new_status = data.get('onboarding_status')
        if new_status not in Vendor.VALID_STATUSES:
            return api_error_response('Invalid status', 400)
        ok = Vendor.update(vendor_id, {'onboarding_status': new_status})
        if not ok:
            return api_error_response('Failed to update vendor', 500)
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='vendor',
            entity_id=vendor_id,
            user_id=str(user['_id']),
            details={'onboarding_status': new_status},
            ip_address=request.remote_addr
        )
        return api_success_response(message='Vendor status updated')
    except Exception as e:
        return api_error_response(f'Failed to set vendor status: {str(e)}', 500)


@super_admin_bp.route('/bookings', methods=['GET'])
@super_admin_required
def admin_get_bookings(user):
    """List bookings with optional status filter."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit
        filters = {}
        status = request.args.get('status')
        if status:
            filters['status'] = status
        bookings = Booking.find_all(filters, skip, limit)
        total = Booking.count(filters)
        return api_success_response({
            'bookings': [Booking.to_dict(b) for b in bookings],
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })
    except Exception as e:
        return api_error_response(f'Failed to get bookings: {str(e)}', 500)



@super_admin_bp.route('/bookings/live', methods=['GET'])
@super_admin_required
def admin_get_live_bookings(user):
    """List live jobs (accepted and in_progress)."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit
        filters = {'status': {'$in': [Booking.STATUS_ACCEPTED, Booking.STATUS_IN_PROGRESS]}}
        bookings = Booking.find_all(filters, skip, limit)
        total = Booking.count(filters)
        return api_success_response({
            'bookings': [Booking.to_dict(b) for b in bookings],
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })
    except Exception as e:
        return api_error_response(f'Failed to get live bookings: {str(e)}', 500)


@super_admin_bp.route('/bookings/<booking_id>/start', methods=['POST'])
@super_admin_required
def admin_start_booking(user, booking_id):
    """Start a booking (set status to in_progress)."""
    try:
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)
        ok = Booking.update_status(booking_id, Booking.STATUS_IN_PROGRESS)
        if not ok:
            return api_error_response('Failed to start booking', 500)
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={'status': Booking.STATUS_IN_PROGRESS},
            ip_address=request.remote_addr
        )
        updated = Booking.find_by_id(booking_id)
        return api_success_response(Booking.to_dict(updated), 'Booking started')
    except Exception as e:
        return api_error_response(f'Failed to start booking: {str(e)}', 500)


@super_admin_bp.route('/bookings/<booking_id>/complete', methods=['POST'])
@super_admin_required
def admin_complete_booking(user, booking_id):
    """Complete a booking (set status to completed)."""
    try:
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)
        ok = Booking.update_status(booking_id, Booking.STATUS_COMPLETED)
        if not ok:
            return api_error_response('Failed to complete booking', 500)
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={'status': Booking.STATUS_COMPLETED},
            ip_address=request.remote_addr
        )
        updated = Booking.find_by_id(booking_id)
        return api_success_response(Booking.to_dict(updated), 'Booking completed')
    except Exception as e:
        return api_error_response(f'Failed to complete booking: {str(e)}', 500)


@super_admin_bp.route('/bookings/<booking_id>/cancel', methods=['POST'])
@super_admin_required
def admin_cancel_booking(user, booking_id):
    """Cancel a booking (set status to cancelled). Refund is managed separately."""
    try:
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)
        ok = Booking.update_status(booking_id, Booking.STATUS_CANCELLED)
        if not ok:
            return api_error_response('Failed to cancel booking', 500)
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={'status': Booking.STATUS_CANCELLED},
            ip_address=request.remote_addr
        )
        updated = Booking.find_by_id(booking_id)
        return api_success_response(Booking.to_dict(updated), 'Booking cancelled')
    except Exception as e:
        return api_error_response(f'Failed to cancel booking: {str(e)}', 500)


@super_admin_bp.route('/bookings/<booking_id>/available-vendors', methods=['GET'])
@super_admin_required
def admin_available_vendors_for_booking(user, booking_id):
    """Get available approved vendors for the booking's service and pincode."""
    try:
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)
        service = Service.find_by_id(str(booking.get('service_id')))
        service_name = service.get('name') if service else None
        if not service_name:
            return api_error_response('Service not found for booking', 400)
        pincode = booking.get('pincode') or request.args.get('pincode')
        vendors = Vendor.find_available_by_service(service_name, pincode)
        return api_success_response({'vendors': [Vendor.to_dict(v) for v in vendors]})
    except Exception as e:
        return api_error_response(f'Failed to get available vendors: {str(e)}', 500)


@super_admin_bp.route('/bookings/<booking_id>/reassign', methods=['POST'])
@super_admin_required
def admin_reassign_booking(user, booking_id):
    """Reassign booking to a different vendor."""
    try:
        data = request.get_json() or {}
        vendor_id = data.get('vendor_id')
        if not vendor_id:
            return api_error_response('vendor_id required', 400)
        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)
        vendor = Vendor.find_by_id(vendor_id)
        if not vendor:
            return api_error_response('Vendor not found', 404)
        ok = Booking.update(booking_id, {'vendor_id': ObjectId(vendor_id)})
        if not ok:
            return api_error_response('Failed to reassign booking', 500)
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={'reassigned_to': vendor_id},
            ip_address=request.remote_addr
        )
        updated = Booking.find_by_id(booking_id)
        return api_success_response(Booking.to_dict(updated), 'Booking reassigned')
    except Exception as e:
        return api_error_response(f'Failed to reassign booking: {str(e)}', 500)


@super_admin_bp.route('/vendors/available', methods=['GET'])
@super_admin_required
def admin_available_vendors(user):
    """List available approved vendors by service (service_id or service_name) and optional pincode."""
    try:
        service_id = request.args.get('service_id')
        pincode = request.args.get('pincode')
        service_name = request.args.get('service_name')
        if not service_name and service_id:
            service = Service.find_by_id(service_id)
            service_name = service.get('name') if service else None
        if not service_name:
            return api_error_response('service_id or service_name required', 400)
        vendors = Vendor.find_available_by_service(service_name, pincode)
        return api_success_response({'vendors': [Vendor.to_dict(v) for v in vendors]})
    except Exception as e:
        return api_error_response(f'Failed to get available vendors: {str(e)}', 500)


@super_admin_bp.route('/finance/summary', methods=['GET'])
@super_admin_required
def get_finance_summary(user):
    """Revenue and payout summary for Financial Management dashboard."""
    try:
        from app import mongo
        # Total revenue: completed booking payments
        rev_pipeline = [
            {'$match': {'payment_type': Payment.TYPE_BOOKING, 'status': Payment.STATUS_COMPLETED}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ]
        rev = list(mongo.db[Payment.COLLECTION].aggregate(rev_pipeline))
        total_revenue = rev[0]['total'] if rev else 0

        # Refunded total
        refund_pipeline = [
            {'$match': {'payment_type': Payment.TYPE_BOOKING, 'status': Payment.STATUS_REFUNDED}},
            {'$group': {'_id': None, 'total': {'$sum': {'$ifNull': ['$refund_amount', '$amount']}}}}
        ]
        ref = list(mongo.db[Payment.COLLECTION].aggregate(refund_pipeline))
        refunded_total = ref[0]['total'] if ref else 0

        # Payouts
        pending_payouts_total = mongo.db[Payment.COLLECTION].aggregate([
            {'$match': {'payment_type': Payment.TYPE_PAYOUT, 'status': Payment.STATUS_PENDING}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ])
        pending_payouts_total = list(pending_payouts_total)
        pending_payouts_total = pending_payouts_total[0]['total'] if pending_payouts_total else 0

        completed_payouts_total = mongo.db[Payment.COLLECTION].aggregate([
            {'$match': {'payment_type': Payment.TYPE_PAYOUT, 'status': Payment.STATUS_COMPLETED}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ])
        completed_payouts_total = list(completed_payouts_total)
        completed_payouts_total = completed_payouts_total[0]['total'] if completed_payouts_total else 0

        return api_success_response({
            'total_revenue': total_revenue,
            'refunded_total': refunded_total,
            'pending_payouts_total': pending_payouts_total,
            'completed_payouts_total': completed_payouts_total
        })
    except Exception as e:
        return api_error_response(f'Failed to get finance summary: {str(e)}', 500)


@super_admin_bp.route('/payments', methods=['GET'])
@super_admin_required
def get_payments(user):
    """List payments with optional filters: status, payment_type."""
    try:
        from app import mongo
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit
        filters = {}
        status = request.args.get('status')
        ptype = request.args.get('payment_type')
        if status:
            filters['status'] = status
        if ptype:
            filters['payment_type'] = ptype
        items = list(mongo.db[Payment.COLLECTION].find(filters).sort('created_at', -1).skip(skip).limit(limit))
        total = mongo.db[Payment.COLLECTION].count_documents(filters)
        return api_success_response({
            'payments': [Payment.to_dict(p) for p in items],
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })
    except Exception as e:
        return api_error_response(f'Failed to get payments: {str(e)}', 500)


@super_admin_bp.route('/payments/<payment_id>/invoice', methods=['POST'])
@super_admin_required
def generate_invoice(user, payment_id):
    """Generate and attach a simple invoice number to the payment (stub)."""
    try:
        payment = Payment.find_by_id(payment_id)
        if not payment:
            return api_error_response('Payment not found', 404)
        if payment.get('payment_type') != Payment.TYPE_BOOKING:
            return api_error_response('Invoice applicable only for booking payments', 400)
        # Generate invoice number
        today = datetime.utcnow().strftime('%Y%m%d')
        suffix = str(payment['_id'])[-6:].upper()
        invoice_no = f'INV-{today}-{suffix}'
        ok = Payment.update(payment_id, {
            'invoice_number': invoice_no,
            'invoice_date': datetime.utcnow()
        })
        if not ok:
            return api_error_response('Failed to tag invoice', 500)
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='payment',
            entity_id=payment_id,
            user_id=str(user['_id']),
            details={'invoice_number': invoice_no},
            ip_address=request.remote_addr
        )
        updated = Payment.find_by_id(payment_id)
        return api_success_response(Payment.to_dict(updated), 'Invoice generated')
    except Exception as e:
        return api_error_response(f'Failed to generate invoice: {str(e)}', 500)
