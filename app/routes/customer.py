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
import math

customer_bp = Blueprint('customer', __name__)


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula."""
    R = 6371  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


@customer_bp.route('/search_by_pincode', methods=['GET'])
@customer_required
def search_by_pincode(user):
    """
    Search services by pincode with vendor filtering and dynamic pricing.

    Query Parameters:
        - pincode: Customer's pincode (required)
        - service_category: Filter by service category (optional)
        - radius: Search radius in km (default: 10)
        - q: Search query for service name (optional)
    """
    try:
        pincode = request.args.get('pincode')
        if not pincode:
            return api_error_response('Pincode is required', 400)

        service_category = request.args.get('service_category')
        radius = float(request.args.get('radius', 10))  # Default 10km radius
        search_query = request.args.get('q', '')

        # Build service filters
        service_filters = {'active': True}
        if service_category:
            service_filters['category'] = service_category
        if search_query:
            service_filters['name'] = {'$regex': search_query, '$options': 'i'}

        # Get all active services
        services = list(Service.find_all(service_filters))

        # Get vendors in the area
        vendor_filters = {
            'onboarding_status': 'approved',
            'availability': True
        }

        # If pincode filtering is available, add it
        if pincode:
            vendor_filters['service_areas'] = {'$in': [pincode]}

        vendors = list(Vendor.find_all(vendor_filters))

        # Calculate demand metrics for dynamic pricing
        recent_bookings = list(Booking.find_all({
            'pincode': pincode,
            'created_at': {'$gte': datetime.utcnow().replace(day=1)}  # This month
        }))

        demand_multiplier = 1.0
        if len(recent_bookings) > 20:  # High demand area
            demand_multiplier = 1.2
        elif len(recent_bookings) > 50:  # Very high demand
            demand_multiplier = 1.5

        # Enhance services with vendor availability and pricing
        enhanced_services = []
        for service in services:
            service_dict = Service.to_dict(service)

            # Find available vendors for this service
            available_vendors = [
                v for v in vendors
                if str(service['_id']) in [str(s) for s in v.get('services', [])]
            ]

            if available_vendors:
                # Apply dynamic pricing
                base_price = service.get('base_price', 0)
                dynamic_price = base_price * demand_multiplier

                service_dict.update({
                    'available_vendors': len(available_vendors),
                    'base_price': base_price,
                    'dynamic_price': round(dynamic_price, 2),
                    'demand_level': 'high' if demand_multiplier > 1.2 else 'normal',
                    'nearest_vendors': [
                        {
                            'id': str(v['_id']),
                            'name': v.get('name', 'Unknown'),
                            'rating': v.get('ratings', 0),
                            'completed_jobs': v.get('completed_jobs', 0)
                        }
                        for v in available_vendors[:3]  # Top 3 vendors
                    ]
                })
                enhanced_services.append(service_dict)

        # Sort by availability and rating
        enhanced_services.sort(
            key=lambda x: (x['available_vendors'], x.get('dynamic_price', 0)),
            reverse=True
        )

        return api_success_response({
            'services': enhanced_services,
            'pincode': pincode,
            'radius': radius,
            'demand_multiplier': demand_multiplier,
            'total_vendors_in_area': len(vendors)
        })

    except Exception as e:
        return api_error_response(f'Failed to search services: {str(e)}', 500)


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
        - service_id: Service ID (required)
        - vendor_id: Specific vendor ID (optional - system will auto-assign if not provided)
        - service_date: Date of service (required)
        - service_time: Time of service (required)
        - address: Service address (required)
        - pincode: Service pincode (required)
        - description: Optional description
    """
    try:
        data = request.get_json()

        if not data:
            return api_error_response('Request body is required', 400)

        # Validate required fields
        required_fields = ['service_id', 'service_date', 'service_time', 'address', 'pincode']
        missing_fields = [field for field in required_fields if field not in data or not str(data[field]).strip()]

        if missing_fields:
            return api_error_response(f'Missing or empty required fields: {", ".join(missing_fields)}', 400)

        # Validate pincode format
        pincode = str(data['pincode']).strip()
        if not pincode.isdigit() or len(pincode) != 6:
            return api_error_response('Pincode must be a 6-digit number', 400)

        # Verify service exists and is active
        service = Service.find_by_id(data['service_id'])
        if not service:
            return api_error_response('Service not found', 404)

        if not service.get('active', True):
            return api_error_response('Service is currently unavailable', 400)

        # Handle vendor selection
        vendor_id = data.get('vendor_id', '').strip()
        vendor_assigned = False
        selected_vendor = None

        if vendor_id:
            # Customer selected a specific vendor - validate it exists and is available
            selected_vendor = Vendor.find_by_id(vendor_id)
            if not selected_vendor:
                return api_error_response('Selected vendor not found', 404)

            if selected_vendor.get('onboarding_status') != Vendor.STATUS_APPROVED:
                return api_error_response('Selected vendor is not approved for bookings', 400)

            if not selected_vendor.get('availability', False):
                return api_error_response('Selected vendor is currently unavailable', 400)

            # Check if vendor serves the requested pincode
            vendor_pincodes = selected_vendor.get('pincodes', [])
            if vendor_pincodes and pincode not in vendor_pincodes:
                return api_error_response('Selected vendor does not serve this pincode', 400)

            # Check if vendor provides the requested service
            vendor_services = selected_vendor.get('services', [])
            if service['name'] not in vendor_services:
                return api_error_response('Selected vendor does not provide this service', 400)

            vendor_assigned = True

        else:
            # Auto-assign best available vendor
            try:
                available_vendors = Vendor.find_available_by_service(service['name'], pincode)

                if available_vendors:
                    # Select best vendor based on rating, completed jobs, and availability
                    selected_vendor = max(available_vendors, key=lambda v: (
                        v.get('ratings', 0),
                        v.get('completed_jobs', 0),
                        1 if v.get('availability') else 0
                    ))
                    vendor_id = str(selected_vendor['_id'])
                    vendor_assigned = True
                else:
                    # No vendors available - booking will be created in pending state
                    print(f"No vendors available for service '{service['name']}' in pincode '{pincode}'")

            except Exception as vendor_error:
                print(f"Error finding available vendors: {vendor_error}")
                # Continue without vendor assignment

        # Create booking data
        booking_data = {
            'customer_id': str(user['_id']),
            'vendor_id': vendor_id if vendor_assigned else None,
            'service_id': data['service_id'],
            'service_name': service.get('name', 'Service'),
            'service_date': data['service_date'],
            'service_time': data['service_time'],
            'address': data['address'],
            'pincode': pincode,
            'description': data.get('description', '').strip(),
            'amount': service.get('base_price', 0),
            'status': Booking.STATUS_PENDING
        }

        # Create the booking
        booking_id = Booking.create(booking_data)

        if not booking_id:
            return api_error_response('Failed to create booking. Please try again.', 500)

        # Send notifications if vendor was assigned
        if vendor_assigned and selected_vendor:
            try:
                # Create notification for vendor
                Notification.create({
                    'user_id': str(selected_vendor['user_id']),
                    'type': Notification.TYPE_BOOKING_CREATED,
                    'title': 'New Booking Request',
                    'message': f'New booking request for {service["name"]} on {data["service_date"]} at {data["service_time"]}',
                    'data': {
                        'booking_id': booking_id,
                        'service_name': service['name'],
                        'customer_name': user.get('name', 'Customer'),
                        'pincode': pincode
                    }
                })

                # Emit real-time notification to vendor
                socketio.emit('new_booking', {
                    'booking_id': booking_id,
                    'service_name': service['name'],
                    'customer_name': user.get('name', 'Customer'),
                    'service_date': data['service_date'],
                    'service_time': data['service_time'],
                    'pincode': pincode
                }, room=str(selected_vendor['user_id']))

            except Exception as notification_error:
                print(f"Failed to notify vendor: {notification_error}")
                # Don't fail the booking creation due to notification errors

        # Log booking creation for audit
        AuditLog.log(
            action=AuditLog.ACTION_CREATE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={
                'service': service['name'],
                'vendor_assigned': vendor_assigned,
                'vendor_id': vendor_id if vendor_assigned else None,
                'pincode': pincode,
                'amount': booking_data['amount']
            },
            ip_address=request.remote_addr
        )

        # Build success response
        response_data = {
            'booking_id': booking_id,
            'service_name': service['name'],
            'vendor_assigned': vendor_assigned,
            'status': 'pending'
        }

        if vendor_assigned and selected_vendor:
            response_data['vendor_name'] = selected_vendor.get('name', 'Assigned Vendor')
            response_data['vendor_id'] = vendor_id
            success_message = f'Booking created successfully! Vendor "{selected_vendor.get("name", "Assigned Vendor")}" has been notified.'
        else:
            success_message = 'Booking created successfully! We will assign a vendor and notify you soon.'

        return api_success_response(response_data, success_message, 201)
        
    except Exception as e:
        return api_error_response(f'Failed to create booking: {str(e)}', 500)


@customer_bp.route('/bookings/with-vendor', methods=['POST'])
@customer_required
def create_booking_with_vendor(user):
    """
    Create a booking with a specific vendor selected by the customer.

    Request Body:
        - vendor_id: Specific vendor ID (required)
        - service_id: Service ID (required)
        - service_date: Date of service (required)
        - service_time: Time of service (required)
        - address: Service address (required)
        - pincode: Service pincode (required)
        - description: Optional description
    """
    try:
        data = request.get_json()

        if not data:
            return api_error_response('Request body is required', 400)

        # Validate required fields
        required_fields = ['vendor_id', 'service_id', 'service_date', 'service_time', 'address', 'pincode']
        missing_fields = [field for field in required_fields if field not in data or not str(data[field]).strip()]

        if missing_fields:
            return api_error_response(f'Missing or empty required fields: {", ".join(missing_fields)}', 400)

        vendor_id = str(data['vendor_id']).strip()
        service_id = str(data['service_id']).strip()
        pincode = str(data['pincode']).strip()

        # Validate pincode format
        if not pincode.isdigit() or len(pincode) != 6:
            return api_error_response('Pincode must be a 6-digit number', 400)

        # Verify vendor exists and is available
        vendor = Vendor.find_by_id(vendor_id)
        if not vendor:
            return api_error_response('Vendor not found', 404)

        if vendor.get('onboarding_status') != Vendor.STATUS_APPROVED:
            return api_error_response('Vendor is not approved for bookings', 400)

        if not vendor.get('availability', False):
            return api_error_response('Vendor is currently unavailable', 400)

        # Verify service exists and is active
        service = Service.find_by_id(service_id)
        if not service:
            return api_error_response('Service not found', 404)

        if not service.get('active', True):
            return api_error_response('Service is currently unavailable', 400)

        # Check if vendor serves the requested pincode
        vendor_pincodes = vendor.get('pincodes', [])
        if vendor_pincodes and pincode not in vendor_pincodes:
            return api_error_response('Vendor does not serve this pincode', 400)

        # Check if vendor provides the requested service
        vendor_services = vendor.get('services', [])
        if service['name'] not in vendor_services:
            return api_error_response('Vendor does not provide this service', 400)

        # Create booking data
        booking_data = {
            'customer_id': str(user['_id']),
            'vendor_id': vendor_id,
            'service_id': service_id,
            'service_name': service.get('name', 'Service'),
            'service_date': data['service_date'],
            'service_time': data['service_time'],
            'address': data['address'],
            'pincode': pincode,
            'description': data.get('description', '').strip(),
            'amount': service.get('base_price', 0),
            'status': Booking.STATUS_PENDING
        }

        # Create the booking
        booking_id = Booking.create(booking_data)

        if not booking_id:
            return api_error_response('Failed to create booking. Please try again.', 500)

        # Send notification to vendor
        try:
            Notification.create({
                'user_id': str(vendor['user_id']),
                'type': Notification.TYPE_BOOKING_CREATED,
                'title': 'New Direct Booking Request',
                'message': f'Customer {user.get("name", "Customer")} has directly booked you for {service["name"]}',
                'data': {
                    'booking_id': booking_id,
                    'service_name': service['name'],
                    'customer_name': user.get('name', 'Customer'),
                    'pincode': pincode,
                    'direct_booking': True
                }
            })

            # Emit real-time notification to vendor
            socketio.emit('new_direct_booking', {
                'booking_id': booking_id,
                'service_name': service['name'],
                'customer_name': user.get('name', 'Customer'),
                'service_date': data['service_date'],
                'service_time': data['service_time'],
                'pincode': pincode,
                'message': 'You have been directly selected for a booking!'
            }, room=str(vendor['user_id']))

        except Exception as notification_error:
            print(f"Failed to notify vendor: {notification_error}")

        # Log booking creation
        AuditLog.log(
            action=AuditLog.ACTION_CREATE,
            entity_type='booking',
            entity_id=booking_id,
            user_id=str(user['_id']),
            details={
                'service': service['name'],
                'vendor_id': vendor_id,
                'vendor_name': vendor.get('name', 'Unknown'),
                'pincode': pincode,
                'amount': booking_data['amount'],
                'direct_booking': True
            },
            ip_address=request.remote_addr
        )

        return api_success_response({
            'booking_id': booking_id,
            'service_name': service['name'],
            'vendor_name': vendor.get('name', 'Selected Vendor'),
            'vendor_id': vendor_id,
            'status': 'pending',
            'direct_booking': True
        }, f'Booking created successfully with {vendor.get("name", "selected vendor")}! They have been notified.', 201)

    except Exception as e:
        print(f"Error creating booking with vendor: {str(e)}")
        return api_error_response(f'Failed to create booking: {str(e)}', 500)


@customer_bp.route('/dashboard', methods=['GET'])
@customer_required
def get_dashboard(user):
    """Get comprehensive customer dashboard data."""
    try:
        customer_id = str(user['_id'])

        # Get all bookings for the customer
        all_bookings = list(Booking.find_all({'customer_id': customer_id}))

        # Separate upcoming and past bookings
        current_time = datetime.utcnow()
        upcoming_bookings = []
        past_bookings = []

        for booking in all_bookings:
            booking_dict = Booking.to_dict(booking)

            # Enhance with vendor and service details
            if booking.get('vendor_id'):
                vendor = Vendor.find_by_id(booking['vendor_id'])
                if vendor:
                    booking_dict['vendor_info'] = {
                        'name': vendor.get('name', 'Unknown'),
                        'phone': vendor.get('phone', ''),
                        'rating': vendor.get('ratings', 0),
                        'completed_jobs': vendor.get('completed_jobs', 0)
                    }

            if booking.get('service_id'):
                service = Service.find_by_id(booking['service_id'])
                if service:
                    booking_dict['service_info'] = {
                        'name': service.get('name', 'Unknown'),
                        'category': service.get('category', ''),
                        'base_price': service.get('base_price', 0)
                    }

            # Add signature requirement status
            booking_dict['requires_signature'] = (
                booking['status'] == Booking.STATUS_COMPLETED and
                booking.get('signature_status', 'unsigned') in ['unsigned', 'requested']
            )

            # Categorize by date
            service_date = booking.get('service_date')
            if service_date and isinstance(service_date, str):
                try:
                    service_date = datetime.fromisoformat(service_date.replace('Z', '+00:00'))
                except:
                    service_date = current_time
            elif not service_date:
                service_date = booking.get('created_at', current_time)

            if service_date >= current_time or booking['status'] in [Booking.STATUS_PENDING, Booking.STATUS_ACCEPTED, Booking.STATUS_IN_PROGRESS]:
                upcoming_bookings.append(booking_dict)
            else:
                past_bookings.append(booking_dict)

        # Sort bookings
        upcoming_bookings.sort(key=lambda x: x.get('service_date', ''), reverse=False)
        past_bookings.sort(key=lambda x: x.get('service_date', ''), reverse=True)

        # Calculate statistics
        total_bookings = len(all_bookings)
        completed_bookings = len([b for b in all_bookings if b['status'] in [Booking.STATUS_COMPLETED, Booking.STATUS_VERIFIED]])
        pending_bookings = len([b for b in all_bookings if b['status'] == Booking.STATUS_PENDING])
        pending_signatures = len([b for b in all_bookings if b.get('signature_status') in ['unsigned', 'requested'] and b['status'] == Booking.STATUS_COMPLETED])

        # Get user profile info
        user_profile = {
            'name': user.get('name', ''),
            'email': user.get('email', ''),
            'phone': user.get('phone', ''),
            'address': user.get('address', ''),
            'pincode': user.get('pincode', ''),
            'created_at': user.get('created_at', '').isoformat() if user.get('created_at') else ''
        }

        return api_success_response({
            'profile': user_profile,
            'statistics': {
                'total_bookings': total_bookings,
                'completed_bookings': completed_bookings,
                'pending_bookings': pending_bookings,
                'pending_signatures': pending_signatures
            },
            'upcoming_bookings': upcoming_bookings[:10],  # Latest 10
            'past_bookings': past_bookings[:20],  # Latest 20
            'signature_required_bookings': [
                Booking.to_dict(b) for b in all_bookings
                if b['status'] == Booking.STATUS_COMPLETED and
                b.get('signature_status', 'unsigned') in ['unsigned', 'requested']
            ]
        })

    except Exception as e:
        return api_error_response(f'Failed to get dashboard data: {str(e)}', 500)


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

