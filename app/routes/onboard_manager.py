"""
Onboard Manager routes for HomeServe Pro.
Handles vendor onboarding, KYC verification, and approval workflows.
"""

from flask import Blueprint, request
from app.models.vendor import Vendor
from app.models.user import User
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.utils.decorators import onboard_manager_required
from app.utils.error_handlers import api_error_response, api_success_response
from app import socketio

onboard_manager_bp = Blueprint('onboard_manager', __name__)


@onboard_manager_bp.route('/vendors/pending', methods=['GET'])
@onboard_manager_required
def get_pending_vendors(user):
    """Get all vendors pending onboarding approval."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit
        
        vendors = Vendor.find_all(
            {'onboarding_status': Vendor.STATUS_PENDING},
            skip,
            limit
        )
        total = Vendor.count({'onboarding_status': Vendor.STATUS_PENDING})
        
        # Enrich with user data
        enriched_vendors = []
        for vendor in vendors:
            vendor_dict = Vendor.to_dict(vendor)
            vendor_user = User.find_by_id(str(vendor['user_id']))
            if vendor_user:
                vendor_dict['user'] = User.to_dict(vendor_user)
            enriched_vendors.append(vendor_dict)
        
        return api_success_response({
            'vendors': enriched_vendors,
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get pending vendors: {str(e)}', 500)


@onboard_manager_bp.route('/vendors/<vendor_id>', methods=['GET'])
@onboard_manager_required
def get_vendor_details(user, vendor_id):
    """Get detailed vendor information for review."""
    try:
        vendor = Vendor.find_by_id(vendor_id)
        
        if not vendor:
            return api_error_response('Vendor not found', 404)
        
        # Get user data
        vendor_user = User.find_by_id(str(vendor['user_id']))
        
        vendor_dict = Vendor.to_dict(vendor)
        if vendor_user:
            vendor_dict['user'] = User.to_dict(vendor_user)
        
        return api_success_response(vendor_dict)
        
    except Exception as e:
        return api_error_response(f'Failed to get vendor details: {str(e)}', 500)


@onboard_manager_bp.route('/vendors/<vendor_id>/approve', methods=['POST'])
@onboard_manager_required
def approve_vendor(user, vendor_id):
    """
    Approve vendor onboarding.
    
    Request Body:
        - notes: Optional approval notes
    """
    try:
        vendor = Vendor.find_by_id(vendor_id)
        
        if not vendor:
            return api_error_response('Vendor not found', 404)
        
        if vendor['onboarding_status'] != Vendor.STATUS_PENDING:
            return api_error_response('Vendor is not pending approval', 400)
        
        data = request.get_json() or {}
        
        # Update vendor status
        Vendor.update(vendor_id, {
            'onboarding_status': Vendor.STATUS_APPROVED,
            'approved_by': str(user['_id']),
            'approval_notes': data.get('notes', '')
        })
        
        # Create notification for vendor
        Notification.create({
            'user_id': str(vendor['user_id']),
            'type': Notification.TYPE_VENDOR_APPROVED,
            'title': 'Onboarding Approved',
            'message': 'Your vendor account has been approved. You can now start accepting bookings.',
            'data': {}
        })
        
        # Emit real-time notification
        socketio.emit('vendor_approved', {
            'vendor_id': vendor_id
        }, room=str(vendor['user_id']))
        
        # Log approval
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='vendor',
            entity_id=vendor_id,
            user_id=str(user['_id']),
            details={'action': 'approved', 'notes': data.get('notes', '')},
            ip_address=request.remote_addr
        )
        
        return api_success_response(message='Vendor approved successfully')
        
    except Exception as e:
        return api_error_response(f'Failed to approve vendor: {str(e)}', 500)


@onboard_manager_bp.route('/vendors/<vendor_id>/reject', methods=['POST'])
@onboard_manager_required
def reject_vendor(user, vendor_id):
    """
    Reject vendor onboarding.
    
    Request Body:
        - reason: Rejection reason (required)
    """
    try:
        vendor = Vendor.find_by_id(vendor_id)
        
        if not vendor:
            return api_error_response('Vendor not found', 404)
        
        if vendor['onboarding_status'] != Vendor.STATUS_PENDING:
            return api_error_response('Vendor is not pending approval', 400)
        
        data = request.get_json()
        
        if not data or not data.get('reason'):
            return api_error_response('Rejection reason is required', 400)
        
        # Update vendor status
        Vendor.update(vendor_id, {
            'onboarding_status': Vendor.STATUS_REJECTED,
            'rejected_by': str(user['_id']),
            'rejection_reason': data['reason']
        })
        
        # Create notification for vendor
        Notification.create({
            'user_id': str(vendor['user_id']),
            'type': Notification.TYPE_VENDOR_REJECTED,
            'title': 'Onboarding Rejected',
            'message': f'Your vendor application was rejected. Reason: {data["reason"]}',
            'data': {'reason': data['reason']}
        })
        
        # Emit real-time notification
        socketio.emit('vendor_rejected', {
            'vendor_id': vendor_id,
            'reason': data['reason']
        }, room=str(vendor['user_id']))
        
        # Log rejection
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='vendor',
            entity_id=vendor_id,
            user_id=str(user['_id']),
            details={'action': 'rejected', 'reason': data['reason']},
            ip_address=request.remote_addr
        )
        
        return api_success_response(message='Vendor rejected')
        
    except Exception as e:
        return api_error_response(f'Failed to reject vendor: {str(e)}', 500)


@onboard_manager_bp.route('/vendors/stats', methods=['GET'])
@onboard_manager_required
def get_vendor_stats(user):
    """Get vendor onboarding statistics."""
    try:
        pending_count = Vendor.count({'onboarding_status': Vendor.STATUS_PENDING})
        approved_count = Vendor.count({'onboarding_status': Vendor.STATUS_APPROVED})
        rejected_count = Vendor.count({'onboarding_status': Vendor.STATUS_REJECTED})
        
        return api_success_response({
            'pending': pending_count,
            'approved': approved_count,
            'rejected': rejected_count,
            'total': pending_count + approved_count + rejected_count
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get stats: {str(e)}', 500)


@onboard_manager_bp.route('/vendors/search', methods=['GET'])
@onboard_manager_required
def search_vendors(user):
    """Search vendors by name, email, or phone."""
    try:
        query = request.args.get('q', '')
        
        if not query:
            return api_error_response('Search query is required', 400)
        
        # Search in users collection
        users = User.find_all({
            'role': User.ROLE_VENDOR,
            '$or': [
                {'name': {'$regex': query, '$options': 'i'}},
                {'email': {'$regex': query, '$options': 'i'}},
                {'phone': {'$regex': query, '$options': 'i'}}
            ]
        })
        
        # Get corresponding vendor profiles
        vendors = []
        for user_doc in users:
            vendor = Vendor.find_by_user_id(str(user_doc['_id']))
            if vendor:
                vendor_dict = Vendor.to_dict(vendor)
                vendor_dict['user'] = User.to_dict(user_doc)
                vendors.append(vendor_dict)
        
        return api_success_response({'vendors': vendors})
        
    except Exception as e:
        return api_error_response(f'Failed to search vendors: {str(e)}', 500)

