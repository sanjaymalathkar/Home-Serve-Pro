"""
Common routes for HomeServe Pro.
Shared endpoints accessible by all authenticated users.
"""

from flask import Blueprint, request, send_from_directory, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.notification import Notification
from app.models.service import Service
from app.utils.error_handlers import api_error_response, api_success_response
from app.utils.file_upload import save_image, get_file_url
import os

common_bp = Blueprint('common', __name__)


@common_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with DB ping."""
    db_ok = True
    db_error = None
    try:
        from app import mongo
        # Ping the MongoDB server; raises if unreachable
        mongo.db.command('ping')
    except Exception as e:
        db_ok = False
        db_error = str(e)
    return api_success_response({
        'status': 'healthy' if db_ok else 'degraded',
        'service': 'HomeServe Pro API',
        'database': {'ok': db_ok, 'error': db_error}
    })


@common_bp.route('/services', methods=['GET'])
def get_public_services():
    """Get all available services (public endpoint)."""
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



@common_bp.route('/vendors', methods=['GET'])
def get_public_vendors():
    """
    Get approved, registered vendors (public endpoint).

    Query Parameters:
        - service_id: Filter by service ID
        - service_type: Filter by service category/type
        - pincode: Filter by serviceable pincode
        - availability: 'true' to return only currently available vendors
        - limit: Maximum number of vendors to return (default: 50)

    Returns:
        {
            "success": true,
            "data": [
                {
                    "vendor_id": "unique_id",
                    "name": "Vendor Name",
                    "service_type": "Cleaning / Electrical / Plumbing etc.",
                    "services": ["Service 1", "Service 2"],
                    "pincode": ["12345", "12346"],
                    "availability_status": "Available / Busy",
                    "ratings": 4.5,
                    "total_ratings": 120,
                    "completed_jobs": 85,
                    "profile_image": "url_to_image"
                }
            ],
            "total": 10,
            "filters_applied": {...}
        }
    """
    try:
        from app.models.vendor import Vendor

        # Parse query parameters
        service_id = request.args.get('service_id', '').strip()
        service_type = request.args.get('service_type', '').strip()
        pincode = request.args.get('pincode', '').strip()
        availability_only = request.args.get('availability', 'false').lower() == 'true'
        limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 vendors

        # Resolve service_id to service name if provided
        service_name = None
        if service_id:
            service = Service.find_by_id(service_id)
            if service:
                service_name = service.get('name', '')
                if not service_type:
                    service_type = service.get('category', '')

        # Build vendor filters
        filters = {
            'onboarding_status': Vendor.STATUS_APPROVED  # Only approved vendors
        }

        if availability_only:
            filters['availability'] = True

        if service_name:
            filters['services'] = {'$in': [service_name]}

        if service_type:
            # Filter by service category - check if any service in vendor's services matches the category
            category_services = Service.find_by_category(service_type)
            if category_services:
                service_names = [s.get('name') for s in category_services]
                filters['services'] = {'$in': service_names}

        if pincode:
            filters['pincodes'] = {'$in': [pincode]}

        # Fetch vendors from database
        vendors = list(Vendor.find_all(filters, skip=0, limit=limit))

        # Process and validate vendors
        result = []
        for vendor in vendors:
            try:
                # Verify vendor has valid user account
                user = None
                if vendor.get('user_id'):
                    user = User.find_by_id(str(vendor['user_id']))

                if not user or user.get('role') != User.ROLE_VENDOR:
                    continue  # Skip vendors without valid user accounts

                # Convert to dict and enhance with user data
                vendor_dict = Vendor.to_dict(vendor)

                # Use vendor name, fallback to user name/email
                vendor_name = vendor_dict.get('name') or user.get('name') or user.get('email', 'Unknown Vendor')

                # Determine primary service type
                vendor_services = vendor_dict.get('services', [])
                primary_service_type = 'General'
                if vendor_services:
                    # Get the category of the first service
                    first_service = Service.find_by_name(vendor_services[0])
                    if first_service:
                        primary_service_type = first_service.get('category', 'General').title()

                # Build public vendor data
                public_vendor = {
                    'vendor_id': vendor_dict['id'],
                    'name': vendor_name,
                    'service_type': primary_service_type,
                    'services': vendor_services,
                    'pincode': vendor_dict.get('pincodes', []),
                    'availability_status': 'Available' if vendor_dict.get('availability') else 'Busy',
                    'ratings': round(vendor_dict.get('ratings', 0.0), 1),
                    'total_ratings': vendor_dict.get('total_ratings', 0),
                    'completed_jobs': vendor_dict.get('completed_jobs', 0),
                    'profile_image': vendor_dict.get('profile_image'),
                    'phone': user.get('phone', ''),  # Include contact info for booking
                    'created_at': vendor_dict.get('created_at')
                }

                result.append(public_vendor)

            except Exception as vendor_error:
                print(f"Error processing vendor {vendor.get('_id')}: {vendor_error}")
                continue

        # Sort vendors by rating and availability
        result.sort(key=lambda x: (
            1 if x['availability_status'] == 'Available' else 0,
            x['ratings'],
            x['completed_jobs']
        ), reverse=True)

        # Build response with metadata
        response_data = {
            'vendors': result,
            'total': len(result),
            'filters_applied': {
                'service_id': service_id,
                'service_type': service_type,
                'pincode': pincode,
                'availability_only': availability_only,
                'limit': limit
            }
        }

        return api_success_response(response_data)

    except ValueError as ve:
        return api_error_response(f'Invalid parameter: {str(ve)}', 400)
    except Exception as e:
        print(f"Error in get_public_vendors: {str(e)}")
        return api_error_response('Failed to fetch vendors. Please try again later.', 500)

@common_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile."""
    try:
        user_id = get_jwt_identity()
        user = User.find_by_id(user_id)

        if not user:
            return api_error_response('User not found', 404)

        return api_success_response(User.to_dict(user))

    except Exception as e:
        return api_error_response(f'Failed to get profile: {str(e)}', 500)


@common_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update user profile.

    Request Body:
        - name: User name
        - phone: Phone number
        - address: Address
        - pincode: Pincode
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # Remove fields that shouldn't be updated via this endpoint
        data.pop('email', None)
        data.pop('password', None)
        data.pop('role', None)
        data.pop('verified', None)
        data.pop('active', None)

        User.update(user_id, data)

        updated_user = User.find_by_id(user_id)
        return api_success_response(User.to_dict(updated_user), 'Profile updated successfully')

    except Exception as e:
        return api_error_response(f'Failed to update profile: {str(e)}', 500)


@common_bp.route('/profile/photo', methods=['POST'])
@jwt_required()
def upload_profile_photo():
    """Upload profile photo."""
    try:
        user_id = get_jwt_identity()

        if 'photo' not in request.files:
            return api_error_response('No photo file provided', 400)

        photo = request.files['photo']
        photo_path = save_image(photo, subfolder='profiles')

        if not photo_path:
            return api_error_response('Failed to save photo', 500)

        photo_url = get_file_url(photo_path)
        User.update(user_id, {'profile_image': photo_url})

        return api_success_response({
            'photo_url': photo_url
        }, 'Profile photo uploaded successfully')

    except Exception as e:
        return api_error_response(f'Failed to upload photo: {str(e)}', 500)


@common_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    """Get user notifications."""
    try:
        user_id = get_jwt_identity()
        unread_only = request.args.get('unread', 'false').lower() == 'true'
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit

        notifications = Notification.find_by_user(user_id, unread_only, skip, limit)
        unread_count = Notification.count_unread(user_id)

        return api_success_response({
            'notifications': [Notification.to_dict(n) for n in notifications],
            'unread_count': unread_count
        })

    except Exception as e:
        return api_error_response(f'Failed to get notifications: {str(e)}', 500)


@common_bp.route('/notifications/<notification_id>/read', methods=['POST'])
@jwt_required()
def mark_notification_read(notification_id):
    """Mark notification as read."""
    try:
        Notification.mark_as_read(notification_id)
        return api_success_response(message='Notification marked as read')

    except Exception as e:
        return api_error_response(f'Failed to mark notification: {str(e)}', 500)


@common_bp.route('/notifications/read-all', methods=['POST'])
@jwt_required()
def mark_all_notifications_read():
    """Mark all notifications as read."""
    try:
        user_id = get_jwt_identity()
        count = Notification.mark_all_as_read(user_id)

        return api_success_response({
            'marked_count': count
        }, f'{count} notifications marked as read')

    except Exception as e:
        return api_error_response(f'Failed to mark notifications: {str(e)}', 500)


@common_bp.route('/uploads/<path:filename>', methods=['GET'])
def serve_upload(filename):
    """Serve uploaded files."""
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        return api_error_response('File not found', 404)

