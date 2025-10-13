"""
Vendor routes for HomeServe Pro.
Handles vendor-specific operations like managing bookings, uploading photos, and requesting signatures.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.booking import Booking
from app.models.vendor import Vendor
from app.models.signature import Signature
from app.models.payment import Payment
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.models.service import Service
from app.utils.decorators import vendor_required
from app.utils.error_handlers import api_error_response, api_success_response
from app.utils.file_upload import save_image, save_upload_file, get_file_url
from app import socketio
import os
import re
from datetime import datetime

vendor_bp = Blueprint('vendor', __name__)


# ============================================================================
# VENDOR REGISTRATION SYSTEM
# ============================================================================

@vendor_bp.route('/register/start', methods=['POST'])
@vendor_required
def start_registration(user):
    """Start vendor registration process - Step 1: Personal Information."""
    try:
        data = request.get_json()

        # Check if vendor profile already exists
        existing_vendor = Vendor.find_by_user_id(str(user['_id']))
        if existing_vendor:
            return api_error_response('Vendor profile already exists', 400)

        # Validate required fields for step 1
        required_fields = ['name', 'phone', 'address', 'pincode']
        for field in required_fields:
            if not data.get(field):
                return api_error_response(f'Missing required field: {field}', 400)

        # Validate pincode format
        if not re.match(r'^\d{6}$', data['pincode']):
            return api_error_response('Invalid pincode format', 400)

        # Create vendor profile with step 1 data
        vendor_data = {
            'user_id': str(user['_id']),
            'name': data['name'],
            'phone': data['phone'],
            'address': data['address'],
            'pincode': data['pincode'],
            'registration_step': 1
        }

        vendor_id = Vendor.create(vendor_data)

        # Log registration start
        AuditLog.log(
            action=AuditLog.ACTION_CREATE,
            entity_type='vendor_registration',
            entity_id=vendor_id,
            user_id=str(user['_id']),
            details={'step': 1, 'name': data['name']},
            ip_address=request.remote_addr
        )

        return api_success_response({
            'vendor_id': vendor_id,
            'registration_step': 1,
            'message': 'Registration started successfully'
        })

    except Exception as e:
        return api_error_response(f'Failed to start registration: {str(e)}', 500)


@vendor_bp.route('/register/business', methods=['POST'])
@vendor_required
def register_business_details(user):
    """Step 2: Business Details Registration."""
    try:
        data = request.get_json()
        vendor = Vendor.find_by_user_id(str(user['_id']))

        if not vendor:
            return api_error_response('Vendor profile not found. Please start registration first.', 404)

        # Validate business type
        if data.get('business_type') not in Vendor.VALID_BUSINESS_TYPES:
            return api_error_response('Invalid business type', 400)

        # Prepare business data
        business_data = {
            'business_type': data.get('business_type', Vendor.BUSINESS_TYPE_INDIVIDUAL),
            'business_name': data.get('business_name', ''),
            'business_address': data.get('business_address', ''),
            'business_registration_number': data.get('business_registration_number', ''),
            'tax_id': data.get('tax_id', ''),
            'experience_years': int(data.get('experience_years', 0)),
            'languages': data.get('languages', []),
            'emergency_contact': {
                'name': data.get('emergency_contact_name', ''),
                'phone': data.get('emergency_contact_phone', ''),
                'relationship': data.get('emergency_contact_relationship', '')
            }
        }

        # Update vendor with business details
        success = Vendor.update_registration_step(str(vendor['_id']), 2, business_data)

        if success:
            return api_success_response({
                'registration_step': 2,
                'message': 'Business details saved successfully'
            })
        else:
            return api_error_response('Failed to save business details', 500)

    except Exception as e:
        return api_error_response(f'Failed to save business details: {str(e)}', 500)


@vendor_bp.route('/register/services', methods=['POST'])
@vendor_required
def register_services(user):
    """Step 3: Service Information Registration."""
    try:
        data = request.get_json()
        vendor = Vendor.find_by_user_id(str(user['_id']))

        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        services = data.get('services', [])
        service_areas = data.get('service_areas', [])
        specializations = data.get('specializations', [])

        if not services:
            return api_error_response('At least one service must be selected', 400)

        # Validate services exist in database
        valid_services = []
        for service_name in services:
            service = Service.find_by_name(service_name)
            if service:
                valid_services.append(service_name)

        if not valid_services:
            return api_error_response('No valid services selected', 400)

        # Prepare service data
        service_data = {
            'services': valid_services,
            'service_areas': service_areas,
            'pincodes': service_areas,  # For backward compatibility
            'specializations': specializations,
            'working_hours': {
                'monday': data.get('working_hours', {}).get('monday', '9:00-18:00'),
                'tuesday': data.get('working_hours', {}).get('tuesday', '9:00-18:00'),
                'wednesday': data.get('working_hours', {}).get('wednesday', '9:00-18:00'),
                'thursday': data.get('working_hours', {}).get('thursday', '9:00-18:00'),
                'friday': data.get('working_hours', {}).get('friday', '9:00-18:00'),
                'saturday': data.get('working_hours', {}).get('saturday', '9:00-17:00'),
                'sunday': data.get('working_hours', {}).get('sunday', 'Closed')
            }
        }

        # Update vendor with service details
        success = Vendor.update_registration_step(str(vendor['_id']), 3, service_data)

        if success:
            return api_success_response({
                'registration_step': 3,
                'services_added': len(valid_services),
                'message': 'Service information saved successfully'
            })
        else:
            return api_error_response('Failed to save service information', 500)

    except Exception as e:
        return api_error_response(f'Failed to save service information: {str(e)}', 500)


@vendor_bp.route('/register/progress', methods=['GET'])
@vendor_required
def get_registration_progress(user):
    """Get vendor registration progress."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))

        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        progress = Vendor.get_registration_progress(str(vendor['_id']))

        return api_success_response(progress)

    except Exception as e:
        return api_error_response(f'Failed to get registration progress: {str(e)}', 500)


# ============================================================================
# PROFILE VERIFICATION & KYC SYSTEM
# ============================================================================

@vendor_bp.route('/register/documents', methods=['POST'])
@vendor_required
def upload_documents(user):
    """Step 4: Document Upload for KYC Verification."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))

        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        # Check if files were uploaded
        if 'documents' not in request.files:
            return api_error_response('No documents uploaded', 400)

        files = request.files.getlist('documents')
        doc_types = request.form.getlist('doc_types')

        if len(files) != len(doc_types):
            return api_error_response('Document types must match number of files', 400)

        uploaded_docs = []

        for file, doc_type in zip(files, doc_types):
            if doc_type not in Vendor.VALID_DOC_TYPES:
                return api_error_response(f'Invalid document type: {doc_type}', 400)

            # Save document
            doc_url = save_image(file, 'vendor_documents')
            if doc_url:
                # Add document to vendor profile
                Vendor.add_kyc_document(str(vendor['_id']), doc_url, doc_type)
                uploaded_docs.append({
                    'type': doc_type,
                    'url': doc_url,
                    'filename': file.filename
                })

        # Update registration step
        Vendor.update_registration_step(str(vendor['_id']), 4)

        # Log document upload
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='vendor_documents',
            entity_id=str(vendor['_id']),
            user_id=str(user['_id']),
            details={'documents_uploaded': len(uploaded_docs), 'types': doc_types},
            ip_address=request.remote_addr
        )

        return api_success_response({
            'registration_step': 4,
            'documents_uploaded': len(uploaded_docs),
            'documents': uploaded_docs,
            'message': 'Documents uploaded successfully'
        })

    except Exception as e:
        return api_error_response(f'Failed to upload documents: {str(e)}', 500)

@vendor_bp.route('/verification/upload', methods=['POST'])
@vendor_required
def upload_verification_document(user):
    """Upload a single verification document (image or PDF) and store reference in MongoDB.
    Accepts multipart/form-data with fields:
      - document: file
      - doc_type: one of ['id_proof','business_license','service_certification']
    Returns a public URL that can be used in verification submission.
    """
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        if 'document' not in request.files:
            return api_error_response('No document file provided', 400)

        file = request.files['document']
        doc_type = request.form.get('doc_type')
        if doc_type not in ['id_proof', 'business_license', 'service_certification']:
            return api_error_response('Invalid or missing document type', 400)

        # Save file (supports images and pdf via allowed extensions)
        rel_path = save_upload_file(file, subfolder='vendor_documents')
        if not rel_path:
            return api_error_response('Invalid file type or failed to save file', 400)

        # Build URL and persist minimal reference on vendor (kyc_docs)
        file_url = get_file_url(rel_path)
        Vendor.add_kyc_document(str(vendor['_id']), file_url, doc_type)

        return api_success_response({
            'document': {
                'type': doc_type,
                'url': file_url
            }
        }, 'Document uploaded successfully')
    except Exception as e:
        return api_error_response(f'Failed to upload document: {str(e)}', 500)



@vendor_bp.route('/register/bank-details', methods=['POST'])
@vendor_required
def register_bank_details(user):
    """Step 5: Bank Details Registration."""
    try:
        data = request.get_json()
        vendor = Vendor.find_by_user_id(str(user['_id']))

        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        # Validate required bank details
        required_fields = ['account_holder_name', 'account_number', 'ifsc_code', 'bank_name']
        for field in required_fields:
            if not data.get(field):
                return api_error_response(f'Missing required field: {field}', 400)

        # Validate IFSC code format
        if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', data['ifsc_code']):
            return api_error_response('Invalid IFSC code format', 400)

        # Prepare bank details
        bank_data = {
            'bank_details': {
                'account_holder_name': data['account_holder_name'],
                'account_number': data['account_number'],
                'ifsc_code': data['ifsc_code'],
                'bank_name': data['bank_name'],
                'branch_name': data.get('branch_name', ''),
                'account_type': data.get('account_type', 'savings'),
                'upi_id': data.get('upi_id', '')
            }
        }

        # Update vendor with bank details and complete registration
        success = Vendor.update_registration_step(str(vendor['_id']), 5, bank_data)

        if success:
            # Mark registration as complete
            Vendor.complete_registration(str(vendor['_id']))

            # Create notification for admin review
            Notification.create({
                'user_id': 'admin',  # Will be handled by admin notification system
                'type': Notification.TYPE_VENDOR_REGISTRATION,
                'title': 'New Vendor Registration',
                'message': f'Vendor {vendor.get("name")} has completed registration and is pending approval',
                'data': {'vendor_id': str(vendor['_id']), 'vendor_name': vendor.get('name')}
            })

            return api_success_response({
                'registration_step': 6,
                'status': 'pending_approval',
                'message': 'Registration completed successfully! Your profile is now under review.'
            })
        else:
            return api_error_response('Failed to save bank details', 500)

    except Exception as e:
        return api_error_response(f'Failed to save bank details: {str(e)}', 500)


@vendor_bp.route('/documents', methods=['GET'])
@vendor_required
def get_documents(user):
    """Get vendor uploaded documents."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))

        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        documents = vendor.get('kyc_docs', [])

        # Add full URLs for documents
        for doc in documents:
            doc['full_url'] = get_file_url(doc['url'])

        return api_success_response({
            'documents': documents,
            'total_documents': len(documents)
        })

    except Exception as e:
        return api_error_response(f'Failed to get documents: {str(e)}', 500)


@vendor_bp.route('/documents/verify', methods=['POST'])
@vendor_required
def verify_document(user):
    """Verify uploaded document using OCR."""
    try:
        from app.services.ocr_service import OCRService

        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        data = request.get_json()
        doc_url = data.get('document_url')
        doc_type = data.get('document_type')

        if not doc_url or not doc_type:
            return api_error_response('Document URL and type are required', 400)

        # Convert URL to local file path (assuming files are stored locally)
        # In production, you might need to download from cloud storage
        file_path = doc_url.replace('/static/', 'static/')

        # Process document with OCR
        ocr_result = OCRService.process_document(file_path, doc_type)

        if not ocr_result['success']:
            return api_error_response(f'OCR processing failed: {ocr_result.get("error")}', 500)

        # Update document with verification results
        vendor_docs = vendor.get('kyc_docs', [])
        for doc in vendor_docs:
            if doc['url'] == doc_url:
                doc['ocr_result'] = ocr_result
                doc['verified'] = ocr_result['validation']['is_valid']
                doc['verification_confidence'] = ocr_result['validation']['confidence']
                break

        # Update vendor with verified documents
        Vendor.update(str(vendor['_id']), {'kyc_docs': vendor_docs})

        return api_success_response({
            'verification_result': ocr_result,
            'document_verified': ocr_result['validation']['is_valid'],
            'confidence': ocr_result['validation']['confidence'],
            'extracted_data': ocr_result['validation']['extracted_data']
        })

    except Exception as e:
        return api_error_response(f'Failed to verify document: {str(e)}', 500)


@vendor_bp.route('/verification/status', methods=['GET'])
@vendor_required
def get_verification_status(user):
    """Get vendor verification status."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        documents = vendor.get('kyc_docs', [])
        total_docs = len(documents)
        verified_docs = sum(1 for doc in documents if doc.get('verified', False))

        # Calculate overall verification score
        total_confidence = sum(doc.get('verification_confidence', 0) for doc in documents)
        avg_confidence = total_confidence / total_docs if total_docs > 0 else 0

        # Determine verification status
        if verified_docs == total_docs and total_docs >= 2:
            verification_status = 'verified'
        elif verified_docs > 0:
            verification_status = 'partially_verified'
        else:
            verification_status = 'unverified'

        return api_success_response({
            'verification_status': verification_status,
            'total_documents': total_docs,
            'verified_documents': verified_docs,
            'average_confidence': round(avg_confidence, 2),
            'onboarding_status': vendor.get('onboarding_status'),
            'documents': [
                {
                    'type': doc.get('type'),
                    'verified': doc.get('verified', False),
                    'confidence': doc.get('verification_confidence', 0),
                    'uploaded_at': doc.get('uploaded_at')
                }
                for doc in documents
            ]
        })

    except Exception as e:
        return api_error_response(f'Failed to get verification status: {str(e)}', 500)


# ============================================================================
# SERVICE MANAGEMENT PANEL
# ============================================================================

@vendor_bp.route('/services', methods=['GET'])
@vendor_required
def get_vendor_services(user):
    """Get vendor's services with pricing and availability."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        services = vendor.get('services', [])
        service_details = []

        for service_name in services:
            service = Service.find_by_name(service_name)
            if service:
                service_details.append({
                    'id': str(service['_id']),
                    'name': service['name'],
                    'category': service.get('category'),
                    'description': service.get('description'),
                    'base_price': service.get('base_price', 0),
                    'vendor_price': vendor.get('custom_pricing', {}).get(service_name, service.get('base_price', 0)),
                    'duration_minutes': service.get('duration_minutes', 60),
                    'active': service.get('active', True)
                })

        return api_success_response({
            'services': service_details,
            'total_services': len(service_details),
            'availability': vendor.get('availability', False),
            'working_hours': vendor.get('working_hours', {})
        })

    except Exception as e:
        return api_error_response(f'Failed to get services: {str(e)}', 500)


@vendor_bp.route('/services/add', methods=['POST'])
@vendor_required
def add_vendor_service(user):
    """Add new service to vendor's offerings."""
    try:
        data = request.get_json()
        vendor = Vendor.find_by_user_id(str(user['_id']))

        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        service_names = data.get('services', [])
        if not service_names:
            return api_error_response('No services specified', 400)

        # Validate services exist
        valid_services = []
        for service_name in service_names:
            service = Service.find_by_name(service_name)
            if service:
                valid_services.append(service_name)

        if not valid_services:
            return api_error_response('No valid services found', 400)

        # Get current services and add new ones
        current_services = vendor.get('services', [])
        updated_services = list(set(current_services + valid_services))

        # Update custom pricing if provided
        custom_pricing = vendor.get('custom_pricing', {})
        pricing_updates = data.get('pricing', {})
        custom_pricing.update(pricing_updates)

        # Update vendor
        update_data = {
            'services': updated_services,
            'custom_pricing': custom_pricing
        }

        success = Vendor.update(str(vendor['_id']), update_data)

        if success:
            return api_success_response({
                'services_added': len(valid_services),
                'total_services': len(updated_services),
                'new_services': valid_services
            })
        else:
            return api_error_response('Failed to add services', 500)

    except Exception as e:
        return api_error_response(f'Failed to add services: {str(e)}', 500)


@vendor_bp.route('/services/remove', methods=['POST'])
@vendor_required
def remove_vendor_service(user):
    """Remove service from vendor's offerings."""
    try:
        data = request.get_json()
        vendor = Vendor.find_by_user_id(str(user['_id']))

        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        services_to_remove = data.get('services', [])
        if not services_to_remove:
            return api_error_response('No services specified', 400)

        # Remove services
        current_services = vendor.get('services', [])
        updated_services = [s for s in current_services if s not in services_to_remove]

        # Remove custom pricing for removed services
        custom_pricing = vendor.get('custom_pricing', {})
        for service in services_to_remove:
            custom_pricing.pop(service, None)

        # Update vendor
        update_data = {
            'services': updated_services,
            'custom_pricing': custom_pricing
        }

        success = Vendor.update(str(vendor['_id']), update_data)

        if success:
            return api_success_response({
                'services_removed': len(services_to_remove),
                'remaining_services': len(updated_services),
                'removed_services': services_to_remove
            })
        else:
            return api_error_response('Failed to remove services', 500)

    except Exception as e:
        return api_error_response(f'Failed to remove services: {str(e)}', 500)


@vendor_bp.route('/services/pricing', methods=['POST'])
@vendor_required
def update_service_pricing(user):
    """Update custom pricing for vendor services."""
    try:
        data = request.get_json()
        vendor = Vendor.find_by_user_id(str(user['_id']))

        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        pricing_updates = data.get('pricing', {})
        if not pricing_updates:
            return api_error_response('No pricing updates provided', 400)

        # Validate that vendor offers these services
        vendor_services = vendor.get('services', [])
        invalid_services = [s for s in pricing_updates.keys() if s not in vendor_services]

        if invalid_services:
            return api_error_response(f'Vendor does not offer these services: {invalid_services}', 400)

        # Update custom pricing
        custom_pricing = vendor.get('custom_pricing', {})
        custom_pricing.update(pricing_updates)

        success = Vendor.update(str(vendor['_id']), {'custom_pricing': custom_pricing})

        if success:
            return api_success_response({
                'pricing_updated': len(pricing_updates),
                'updated_services': list(pricing_updates.keys()),
                'custom_pricing': custom_pricing
            })
        else:
            return api_error_response('Failed to update pricing', 500)

    except Exception as e:
        return api_error_response(f'Failed to update pricing: {str(e)}', 500)


@vendor_bp.route('/services/create', methods=['POST'])
@vendor_required
def create_custom_service(user):
    """
    Create a custom service offering for the vendor.
    Allows vendors to define their own services with custom pricing and details.
    """
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))

        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        # Check if vendor is approved
        if not vendor.get('is_approved', False):
            return api_error_response('Only approved vendors can create services', 403)

        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'category', 'price', 'duration']
        for field in required_fields:
            if field not in data:
                return api_error_response(f'Missing required field: {field}', 400)

        # Prepare custom service data
        custom_service = {
            'name': data['name'],
            'category': data['category'],
            'price': float(data['price']),
            'duration': int(data['duration']),  # in minutes
            'description': data.get('description', ''),
            'availability': data.get('availability', True),
            'created_at': datetime.utcnow(),
            'vendor_id': str(vendor['_id'])
        }

        # Get or initialize custom_services array
        from app import mongo
        vendor_id = str(vendor['_id'])

        # Add to vendor's custom services
        result = mongo.db[Vendor.COLLECTION].update_one(
            {'_id': vendor['_id']},
            {
                '$push': {'custom_services': custom_service},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )

        if result.modified_count > 0:
            # Log service creation
            AuditLog.log(
                action=AuditLog.ACTION_CREATE,
                entity_type='vendor_service',
                entity_id=vendor_id,
                user_id=str(user['_id']),
                details={'service_name': data['name'], 'price': data['price']},
                ip_address=request.remote_addr
            )

            return api_success_response({
                'message': 'Custom service created successfully',
                'service': custom_service
            }, 'Service created successfully', 201)
        else:
            return api_error_response('Failed to create service', 500)

    except Exception as e:
        return api_error_response(f'Failed to create service: {str(e)}', 500)


# ============================================================================
# VENDOR DASHBOARD & NOTIFICATIONS
# ============================================================================

@vendor_bp.route('/dashboard', methods=['GET'])
@vendor_required
def get_dashboard(user):
    """Get comprehensive vendor dashboard data."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        vendor_id = str(vendor['_id'])

        # Get booking statistics
        total_bookings = Booking.count({'vendor_id': vendor_id})
        pending_bookings = Booking.count({'vendor_id': vendor_id, 'status': Booking.STATUS_PENDING})
        active_bookings = Booking.count({'vendor_id': vendor_id, 'status': Booking.STATUS_IN_PROGRESS})
        completed_bookings = Booking.count({'vendor_id': vendor_id, 'status': Booking.STATUS_COMPLETED})

        # Get recent bookings
        recent_bookings = list(Booking.find_all(
            {'vendor_id': vendor_id},
            sort=[('created_at', -1)],
            limit=10
        ))

        # Get earnings data
        earnings = vendor.get('earnings', 0.0)

        # Get notifications
        notifications = list(Notification.find_all(
            {'user_id': str(user['_id'])},
            sort=[('created_at', -1)],
            limit=20
        ))

        # Calculate performance metrics
        rating = vendor.get('ratings', 0.0)
        total_ratings = vendor.get('total_ratings', 0)

        # Get registration progress
        progress = Vendor.get_registration_progress(vendor_id)

        dashboard_data = {
            'vendor_info': {
                'id': vendor_id,
                'name': vendor.get('name'),
                'status': vendor.get('onboarding_status'),
                'availability': vendor.get('availability', False),
                'rating': rating,
                'total_ratings': total_ratings,
                'services_count': len(vendor.get('services', [])),
                'registration_progress': progress,
                # New status flags for dynamic dashboard
                'is_approved': vendor.get('is_approved', False),
                'documents_verified': vendor.get('documents_verified', False),
                'payouts_enabled': vendor.get('payouts_enabled', False),
                'verification_docs': vendor.get('verification_docs', []),
                'rejection_reason': vendor.get('rejection_reason', ''),
                'phone': vendor.get('phone', ''),
                'email': user.get('email', ''),
                'bank_details': vendor.get('bank_details', {})
            },
            'statistics': {
                'total_bookings': total_bookings,
                'pending_bookings': pending_bookings,
                'active_bookings': active_bookings,
                'completed_bookings': completed_bookings,
                'total_earnings': earnings,
                'average_rating': rating
            },
            'recent_bookings': [Booking.to_dict(b) for b in recent_bookings],
            'notifications': [Notification.to_dict(n) for n in notifications],
            'quick_actions': [
                {'name': 'Toggle Availability', 'endpoint': '/api/vendor/availability', 'method': 'POST'},
                {'name': 'View Bookings', 'endpoint': '/api/vendor/bookings', 'method': 'GET'},
                {'name': 'Update Services', 'endpoint': '/api/vendor/services', 'method': 'GET'},
                {'name': 'View Earnings', 'endpoint': '/api/vendor/earnings', 'method': 'GET'}
            ]
        }

        return api_success_response(dashboard_data)

    except Exception as e:
        return api_error_response(f'Failed to get dashboard data: {str(e)}', 500)


@vendor_bp.route('/notifications', methods=['GET'])
@vendor_required
def get_notifications(user):
    """Get vendor notifications with pagination."""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'

        skip = (page - 1) * limit

        filters = {'user_id': str(user['_id'])}
        if unread_only:
            filters['read'] = False

        notifications = list(Notification.find_all(
            filters,
            sort=[('created_at', -1)],
            skip=skip,
            limit=limit
        ))

        total = Notification.count(filters)
        unread_count = Notification.count({'user_id': str(user['_id']), 'read': False})

        return api_success_response({
            'notifications': [Notification.to_dict(n) for n in notifications],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            },
            'unread_count': unread_count
        })

    except Exception as e:
        return api_error_response(f'Failed to get notifications: {str(e)}', 500)


@vendor_bp.route('/notifications/<notification_id>/read', methods=['POST'])
@vendor_required
def mark_notification_read(user, notification_id):
    """Mark notification as read."""
    try:
        success = Notification.mark_as_read(notification_id)

        if success:
            return api_success_response({'message': 'Notification marked as read'})
        else:
            return api_error_response('Failed to mark notification as read', 500)

    except Exception as e:
        return api_error_response(f'Failed to mark notification as read: {str(e)}', 500)


@vendor_bp.route('/notifications/preferences', methods=['GET', 'POST'])
@vendor_required
def notification_preferences(user):
    """Get or update notification preferences."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        if request.method == 'GET':
            preferences = vendor.get('notification_preferences', {
                'email_notifications': True,
                'sms_notifications': True,
                'whatsapp_notifications': False,
                'push_notifications': True,
                'booking_alerts': True,
                'payment_alerts': True,
                'promotional_messages': False
            })

            return api_success_response({'preferences': preferences})

        else:  # POST
            data = request.get_json()
            preferences = data.get('preferences', {})

            # Update preferences
            success = Vendor.update(str(vendor['_id']), {
                'notification_preferences': preferences
            })

            if success:
                return api_success_response({
                    'message': 'Notification preferences updated',
                    'preferences': preferences
                })
            else:
                return api_error_response('Failed to update preferences', 500)

    except Exception as e:
        return api_error_response(f'Failed to handle notification preferences: {str(e)}', 500)


# ============================================================================
# BOOKING MANAGEMENT SYSTEM
# ============================================================================

@vendor_bp.route('/bookings/<booking_id>/accept', methods=['POST'])
@vendor_required
def accept_booking(user, booking_id):
    """Accept a booking request."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)

        # Verify booking belongs to this vendor
        if str(booking['vendor_id']) != str(vendor['_id']):
            return api_error_response('Access denied', 403)

        # Check if booking is in pending status
        if booking['status'] != Booking.STATUS_PENDING:
            return api_error_response('Booking is not in pending status', 400)

        # Accept the booking
        success = Booking.update_status(booking_id, Booking.STATUS_ACCEPTED)

        if success:
            # Notify customer
            customer = User.find_by_id(str(booking['customer_id']))
            if customer:
                Notification.create({
                    'user_id': str(customer['_id']),
                    'type': Notification.TYPE_BOOKING_ACCEPTED,
                    'title': 'Booking Accepted',
                    'message': f'Your booking for {booking.get("service_name")} has been accepted',
                    'data': {'booking_id': booking_id, 'vendor_name': vendor.get('name')}
                })

                # Send real-time notification
                socketio.emit('booking_accepted', {
                    'booking_id': booking_id,
                    'vendor_name': vendor.get('name'),
                    'service_name': booking.get('service_name')
                }, room=str(customer['_id']))

            # Log the action
            AuditLog.log(
                action=AuditLog.ACTION_UPDATE,
                entity_type='booking',
                entity_id=booking_id,
                user_id=str(user['_id']),
                details={'action': 'accepted', 'vendor_name': vendor.get('name')},
                ip_address=request.remote_addr
            )

            return api_success_response({
                'booking_id': booking_id,
                'status': Booking.STATUS_ACCEPTED,
                'message': 'Booking accepted successfully'
            })
        else:
            return api_error_response('Failed to accept booking', 500)

    except Exception as e:
        return api_error_response(f'Failed to accept booking: {str(e)}', 500)


@vendor_bp.route('/bookings/<booking_id>/reject', methods=['POST'])
@vendor_required
def reject_booking(user, booking_id):
    """Reject a booking request."""
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')

        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)

        # Verify booking belongs to this vendor
        if str(booking['vendor_id']) != str(vendor['_id']):
            return api_error_response('Access denied', 403)

        # Check if booking can be rejected
        if booking['status'] not in [Booking.STATUS_PENDING, Booking.STATUS_ACCEPTED]:
            return api_error_response('Booking cannot be rejected at this stage', 400)

        # Reject the booking
        success = Booking.update(booking_id, {
            'status': Booking.STATUS_REJECTED,
            'rejection_reason': reason,
            'rejected_at': datetime.utcnow(),
            'rejected_by': str(vendor['_id'])
        })

        if success:
            # Notify customer
            customer = User.find_by_id(str(booking['customer_id']))
            if customer:
                Notification.create({
                    'user_id': str(customer['_id']),
                    'type': Notification.TYPE_BOOKING_REJECTED,
                    'title': 'Booking Rejected',
                    'message': f'Your booking for {booking.get("service_name")} has been rejected. Reason: {reason}',
                    'data': {'booking_id': booking_id, 'reason': reason}
                })

                # Send real-time notification
                socketio.emit('booking_rejected', {
                    'booking_id': booking_id,
                    'reason': reason,
                    'service_name': booking.get('service_name')
                }, room=str(customer['_id']))

            # Log the action
            AuditLog.log(
                action=AuditLog.ACTION_UPDATE,
                entity_type='booking',
                entity_id=booking_id,
                user_id=str(user['_id']),
                details={'action': 'rejected', 'reason': reason},
                ip_address=request.remote_addr
            )

            return api_success_response({
                'booking_id': booking_id,
                'status': Booking.STATUS_REJECTED,
                'reason': reason,
                'message': 'Booking rejected successfully'
            })
        else:
            return api_error_response('Failed to reject booking', 500)

    except Exception as e:
        return api_error_response(f'Failed to reject booking: {str(e)}', 500)


@vendor_bp.route('/bookings/<booking_id>/start', methods=['POST'])
@vendor_required
def start_booking(user, booking_id):
    """Start a booking (mark as in progress)."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)

        # Verify booking belongs to this vendor
        if str(booking['vendor_id']) != str(vendor['_id']):
            return api_error_response('Access denied', 403)

        # Check if booking can be started
        if booking['status'] != Booking.STATUS_ACCEPTED:
            return api_error_response('Only accepted bookings can be started', 400)

        # Update booking status to in_progress
        success = Booking.update_status(booking_id, Booking.STATUS_IN_PROGRESS)

        if success:
            # Update booking with start time
            Booking.update(booking_id, {
                'started_at': datetime.utcnow()
            })

            # Notify customer
            customer = User.find_by_id(str(booking['customer_id']))
            if customer:
                Notification.create({
                    'user_id': str(customer['_id']),
                    'type': Notification.TYPE_BOOKING_STARTED,
                    'title': 'Service Started',
                    'message': f'Your service has been started by {vendor.get("name")}',
                    'data': {'booking_id': booking_id}
                })

            # Log the action
            AuditLog.log(
                user_id=str(user['_id']),
                action='booking_started',
                resource_type='booking',
                resource_id=booking_id,
                details={'vendor_id': str(vendor['_id'])}
            )

            return api_success_response({
                'message': 'Booking started successfully',
                'booking': Booking.to_dict(Booking.find_by_id(booking_id))
            })
        else:
            return api_error_response('Failed to start booking', 500)

    except Exception as e:
        return api_error_response(f'Failed to start booking: {str(e)}', 500)


@vendor_bp.route('/bookings/<booking_id>/complete', methods=['POST'])
@vendor_required
def complete_booking(user, booking_id):
    """Complete a booking."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)

        # Verify booking belongs to this vendor
        if str(booking['vendor_id']) != str(vendor['_id']):
            return api_error_response('Access denied', 403)

        # Check if booking can be completed
        if booking['status'] != Booking.STATUS_IN_PROGRESS:
            return api_error_response('Only in-progress bookings can be completed', 400)

        # Update booking status to completed
        success = Booking.update_status(booking_id, Booking.STATUS_COMPLETED)

        if success:
            # Update booking with completion time
            Booking.update(booking_id, {
                'completed_at': datetime.utcnow()
            })

            # Update vendor earnings
            amount = booking.get('amount', 0)
            current_earnings = vendor.get('earnings', 0)
            Vendor.update(str(vendor['_id']), {
                'earnings': current_earnings + amount
            })

            # Notify customer
            customer = User.find_by_id(str(booking['customer_id']))
            if customer:
                Notification.create({
                    'user_id': str(customer['_id']),
                    'type': Notification.TYPE_BOOKING_COMPLETED,
                    'title': 'Service Completed',
                    'message': f'Your service has been completed by {vendor.get("name")}. Please rate your experience!',
                    'data': {'booking_id': booking_id}
                })

            # Log the action
            AuditLog.log(
                user_id=str(user['_id']),
                action='booking_completed',
                resource_type='booking',
                resource_id=booking_id,
                details={'vendor_id': str(vendor['_id']), 'amount': amount}
            )

            return api_success_response({
                'message': 'Booking completed successfully',
                'booking': Booking.to_dict(Booking.find_by_id(booking_id))
            })
        else:
            return api_error_response('Failed to complete booking', 500)

    except Exception as e:
        return api_error_response(f'Failed to complete booking: {str(e)}', 500)


@vendor_bp.route('/bookings/<booking_id>/reschedule', methods=['POST'])
@vendor_required
def reschedule_booking(user, booking_id):
    """Reschedule a booking."""
    try:
        data = request.get_json()
        new_date = data.get('new_date')
        new_time = data.get('new_time')
        reason = data.get('reason', 'Vendor requested reschedule')

        if not new_date or not new_time:
            return api_error_response('New date and time are required', 400)

        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        booking = Booking.find_by_id(booking_id)
        if not booking:
            return api_error_response('Booking not found', 404)

        # Verify booking belongs to this vendor
        if str(booking['vendor_id']) != str(vendor['_id']):
            return api_error_response('Access denied', 403)

        # Check if booking can be rescheduled
        if booking['status'] not in [Booking.STATUS_PENDING, Booking.STATUS_ACCEPTED]:
            return api_error_response('Booking cannot be rescheduled at this stage', 400)

        # Store original schedule
        original_date = booking.get('service_date')
        original_time = booking.get('service_time')

        # Update booking with new schedule
        success = Booking.update(booking_id, {
            'service_date': new_date,
            'service_time': new_time,
            'reschedule_reason': reason,
            'rescheduled_at': datetime.utcnow(),
            'rescheduled_by': str(vendor['_id']),
            'original_date': original_date,
            'original_time': original_time
        })

        if success:
            # Notify customer
            customer = User.find_by_id(str(booking['customer_id']))
            if customer:
                Notification.create({
                    'user_id': str(customer['_id']),
                    'type': Notification.TYPE_BOOKING_RESCHEDULED,
                    'title': 'Booking Rescheduled',
                    'message': f'Your booking has been rescheduled to {new_date} at {new_time}. Reason: {reason}',
                    'data': {
                        'booking_id': booking_id,
                        'new_date': new_date,
                        'new_time': new_time,
                        'reason': reason
                    }
                })

                # Send real-time notification
                socketio.emit('booking_rescheduled', {
                    'booking_id': booking_id,
                    'new_date': new_date,
                    'new_time': new_time,
                    'reason': reason
                }, room=str(customer['_id']))

            # Log the action
            AuditLog.log(
                action=AuditLog.ACTION_UPDATE,
                entity_type='booking',
                entity_id=booking_id,
                user_id=str(user['_id']),
                details={
                    'action': 'rescheduled',
                    'original_date': original_date,
                    'original_time': original_time,
                    'new_date': new_date,
                    'new_time': new_time,
                    'reason': reason
                },
                ip_address=request.remote_addr
            )

            return api_success_response({
                'booking_id': booking_id,
                'new_date': new_date,
                'new_time': new_time,
                'message': 'Booking rescheduled successfully'
            })
        else:
            return api_error_response('Failed to reschedule booking', 500)

    except Exception as e:
        return api_error_response(f'Failed to reschedule booking: {str(e)}', 500)


# ============================================================================
# PAYOUTS & FINANCIAL MANAGEMENT
# ============================================================================

@vendor_bp.route('/earnings', methods=['GET'])
@vendor_required
def get_earnings(user):
    """Get vendor earnings and financial summary."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        vendor_id = str(vendor['_id'])

        # Get payment history
        payments = list(Payment.find_all({'vendor_id': vendor_id}))

        # Calculate earnings summary
        total_earnings = sum(p.get('amount', 0) for p in payments if p.get('status') == 'completed')
        pending_earnings = sum(p.get('amount', 0) for p in payments if p.get('status') == 'pending')
        total_payouts = sum(p.get('amount', 0) for p in payments if p.get('type') == 'payout')

        # Get recent transactions
        recent_payments = sorted(payments, key=lambda x: x.get('created_at', datetime.min), reverse=True)[:10]

        # Calculate monthly earnings
        from collections import defaultdict
        monthly_earnings = defaultdict(float)
        for payment in payments:
            if payment.get('status') == 'completed' and payment.get('created_at'):
                month_key = payment['created_at'].strftime('%Y-%m')
                monthly_earnings[month_key] += payment.get('amount', 0)

        earnings_data = {
            'summary': {
                'total_earnings': total_earnings,
                'pending_earnings': pending_earnings,
                'total_payouts': total_payouts,
                'available_balance': total_earnings - total_payouts,
                'completed_jobs': vendor.get('completed_jobs', 0),
                'average_earning_per_job': total_earnings / max(vendor.get('completed_jobs', 1), 1)
            },
            'recent_transactions': [Payment.to_dict(p) for p in recent_payments],
            'monthly_earnings': dict(monthly_earnings),
            'bank_details': vendor.get('bank_details', {}),
            'payout_preferences': vendor.get('payout_preferences', {
                'method': 'bank_transfer',
                'frequency': 'weekly',
                'minimum_amount': 500
            })
        }

        return api_success_response(earnings_data)

    except Exception as e:
        return api_error_response(f'Failed to get earnings: {str(e)}', 500)


@vendor_bp.route('/payouts/request', methods=['POST'])
@vendor_required
def request_payout(user):
    """Request payout of available earnings."""
    try:
        data = request.get_json()
        vendor = Vendor.find_by_user_id(str(user['_id']))

        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        amount = float(data.get('amount', 0))
        method = data.get('method', 'bank_transfer')  # bank_transfer, upi, wallet

        if amount <= 0:
            return api_error_response('Invalid payout amount', 400)

        # Check available balance
        vendor_id = str(vendor['_id'])
        payments = list(Payment.find_all({'vendor_id': vendor_id}))
        total_earnings = sum(p.get('amount', 0) for p in payments if p.get('status') == 'completed')
        total_payouts = sum(p.get('amount', 0) for p in payments if p.get('type') == 'payout')
        available_balance = total_earnings - total_payouts

        if amount > available_balance:
            return api_error_response(f'Insufficient balance. Available: ₹{available_balance}', 400)

        # Validate payout method and details
        if method == 'bank_transfer':
            bank_details = vendor.get('bank_details', {})
            if not bank_details.get('account_number') or not bank_details.get('ifsc_code'):
                return api_error_response('Bank details not found. Please update your profile.', 400)
        elif method == 'upi':
            bank_details = vendor.get('bank_details', {})
            if not bank_details.get('upi_id'):
                return api_error_response('UPI ID not found. Please update your profile.', 400)

        # Create payout request
        payout_data = {
            'vendor_id': vendor_id,
            'user_id': str(user['_id']),
            'type': 'payout',
            'amount': amount,
            'method': method,
            'status': 'pending',
            'requested_at': datetime.utcnow(),
            'reference_id': f'PAYOUT_{vendor_id}_{int(datetime.utcnow().timestamp())}',
            'details': {
                'vendor_name': vendor.get('name'),
                'method': method,
                'bank_details': vendor.get('bank_details', {}) if method == 'bank_transfer' else None,
                'upi_id': vendor.get('bank_details', {}).get('upi_id') if method == 'upi' else None
            }
        }

        payout_id = Payment.create(payout_data)

        # Create notification for admin
        Notification.create({
            'user_id': 'admin',
            'type': Notification.TYPE_PAYOUT_REQUESTED,
            'title': 'Payout Request',
            'message': f'Vendor {vendor.get("name")} requested payout of ₹{amount}',
            'data': {
                'payout_id': payout_id,
                'vendor_id': vendor_id,
                'amount': amount,
                'method': method
            }
        })

        # Log the payout request
        AuditLog.log(
            action=AuditLog.ACTION_CREATE,
            entity_type='payout_request',
            entity_id=payout_id,
            user_id=str(user['_id']),
            details={'amount': amount, 'method': method},
            ip_address=request.remote_addr
        )

        return api_success_response({
            'payout_id': payout_id,
            'amount': amount,
            'method': method,
            'status': 'pending',
            'reference_id': payout_data['reference_id'],
            'message': 'Payout request submitted successfully'
        })

    except Exception as e:
        return api_error_response(f'Failed to request payout: {str(e)}', 500)


@vendor_bp.route('/payouts', methods=['GET'])
@vendor_required
def get_payouts(user):
    """Get vendor payout history."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        status = request.args.get('status', '')

        skip = (page - 1) * limit

        # Build filters
        filters = {'vendor_id': str(vendor['_id']), 'type': 'payout'}
        if status:
            filters['status'] = status

        # Get payouts
        payouts = list(Payment.find_all(filters, skip=skip, limit=limit))
        total = Payment.count(filters)

        # Calculate summary
        total_requested = sum(p.get('amount', 0) for p in payouts)
        completed_payouts = [p for p in payouts if p.get('status') == 'completed']
        total_paid = sum(p.get('amount', 0) for p in completed_payouts)

        return api_success_response({
            'payouts': [Payment.to_dict(p) for p in payouts],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            },
            'summary': {
                'total_requested': total_requested,
                'total_paid': total_paid,
                'pending_amount': total_requested - total_paid
            }
        })

    except Exception as e:
        return api_error_response(f'Failed to get payouts: {str(e)}', 500)


@vendor_bp.route('/payouts/preferences', methods=['GET', 'POST'])
@vendor_required
def payout_preferences(user):
    """Get or update payout preferences."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        if request.method == 'GET':
            preferences = vendor.get('payout_preferences', {
                'method': 'bank_transfer',
                'frequency': 'weekly',
                'minimum_amount': 500,
                'auto_payout': False
            })

            return api_success_response({'preferences': preferences})

        else:  # POST
            data = request.get_json()
            preferences = data.get('preferences', {})

            # Validate preferences
            valid_methods = ['bank_transfer', 'upi', 'wallet']
            valid_frequencies = ['daily', 'weekly', 'monthly', 'manual']

            if preferences.get('method') not in valid_methods:
                return api_error_response('Invalid payout method', 400)

            if preferences.get('frequency') not in valid_frequencies:
                return api_error_response('Invalid payout frequency', 400)

            # Update preferences
            success = Vendor.update(str(vendor['_id']), {
                'payout_preferences': preferences
            })

            if success:
                return api_success_response({
                    'message': 'Payout preferences updated',
                    'preferences': preferences
                })
            else:
                return api_error_response('Failed to update preferences', 500)

    except Exception as e:
        return api_error_response(f'Failed to handle payout preferences: {str(e)}', 500)


# ============================================================================
# GROWTH & SUPPORT SYSTEM
# ============================================================================

@vendor_bp.route('/support/tickets', methods=['GET', 'POST'])
@vendor_required
def support_tickets(user):
    """Get or create support tickets."""
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))
        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        if request.method == 'GET':
            # Get support tickets
            page = int(request.args.get('page', 1))
            limit = int(request.args.get('limit', 20))
            status = request.args.get('status', '')

            skip = (page - 1) * limit

            filters = {'user_id': str(user['_id'])}
            if status:
                filters['status'] = status

            # Mock support ticket collection (in production, create SupportTicket model)
            tickets = []  # Would fetch from SupportTicket.find_all(filters, skip=skip, limit=limit)
            total = 0  # Would be SupportTicket.count(filters)

            return api_success_response({
                'tickets': tickets,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit if total > 0 else 0
                }
            })

        else:  # POST
            data = request.get_json()

            # Validate required fields
            required_fields = ['subject', 'description', 'category']
            for field in required_fields:
                if not data.get(field):
                    return api_error_response(f'Missing required field: {field}', 400)

            # Create support ticket (mock implementation)
            ticket_data = {
                'user_id': str(user['_id']),
                'vendor_id': str(vendor['_id']),
                'subject': data['subject'],
                'description': data['description'],
                'category': data['category'],  # technical, payment, account, general
                'priority': data.get('priority', 'medium'),
                'status': 'open',
                'created_at': datetime.utcnow(),
                'ticket_id': f'TICKET_{int(datetime.utcnow().timestamp())}'
            }

            # In production: ticket_id = SupportTicket.create(ticket_data)
            ticket_id = ticket_data['ticket_id']

            # Create notification for admin
            Notification.create({
                'user_id': 'admin',
                'type': Notification.TYPE_SUPPORT_TICKET,
                'title': 'New Support Ticket',
                'message': f'Vendor {vendor.get("name")} created a support ticket: {data["subject"]}',
                'data': {
                    'ticket_id': ticket_id,
                    'vendor_id': str(vendor['_id']),
                    'category': data['category']
                }
            })

            return api_success_response({
                'ticket_id': ticket_id,
                'status': 'open',
                'message': 'Support ticket created successfully'
            })

    except Exception as e:
        return api_error_response(f'Failed to handle support tickets: {str(e)}', 500)


@vendor_bp.route('/support/faq', methods=['GET'])
@vendor_required
def get_faq(user):
    """Get frequently asked questions."""
    try:
        # Mock FAQ data (in production, fetch from database)
        faq_data = {
            'categories': [
                {
                    'name': 'Getting Started',
                    'questions': [
                        {
                            'question': 'How do I complete my vendor registration?',
                            'answer': 'Complete all 5 steps: Personal Information, Business Details, Service Information, Document Upload, and Bank Details. Ensure all required documents are uploaded and verified.'
                        },
                        {
                            'question': 'How long does verification take?',
                            'answer': 'Verification typically takes 2-3 business days. You will receive notifications about the status of your application.'
                        },
                        {
                            'question': 'What documents do I need to upload?',
                            'answer': 'You need ID proof (PAN/Aadhaar), address proof, business license (if applicable), skill certifications, and bank account details.'
                        }
                    ]
                },
                {
                    'name': 'Bookings & Services',
                    'questions': [
                        {
                            'question': 'How do I accept or reject bookings?',
                            'answer': 'Go to your dashboard and click on pending bookings. You can accept, reject, or reschedule bookings with appropriate reasons.'
                        },
                        {
                            'question': 'Can I add new services to my profile?',
                            'answer': 'Yes, go to Services section in your dashboard to add new services, update pricing, and manage your service offerings.'
                        },
                        {
                            'question': 'How do I update my availability?',
                            'answer': 'Use the availability toggle in your dashboard or update your working hours in the profile section.'
                        }
                    ]
                },
                {
                    'name': 'Payments & Payouts',
                    'questions': [
                        {
                            'question': 'When do I get paid?',
                            'answer': 'Payments are processed after job completion and customer verification. You can request payouts based on your preferences (daily, weekly, or monthly).'
                        },
                        {
                            'question': 'What are the payout methods available?',
                            'answer': 'We support bank transfer, UPI, and digital wallet payouts. Update your preferences in the Payouts section.'
                        },
                        {
                            'question': 'Is there a minimum payout amount?',
                            'answer': 'Yes, the default minimum payout amount is ₹500. You can adjust this in your payout preferences.'
                        }
                    ]
                },
                {
                    'name': 'Technical Support',
                    'questions': [
                        {
                            'question': 'I am not receiving notifications. What should I do?',
                            'answer': 'Check your notification preferences in settings. Ensure your phone number and email are verified. Contact support if issues persist.'
                        },
                        {
                            'question': 'How do I update my profile information?',
                            'answer': 'Go to Profile section in your dashboard. You can update personal details, business information, and service offerings.'
                        },
                        {
                            'question': 'The app is not working properly. How do I report bugs?',
                            'answer': 'Create a support ticket with category "Technical" and provide detailed information about the issue you are experiencing.'
                        }
                    ]
                }
            ],
            'contact_info': {
                'support_email': 'support@homeservepro.com',
                'support_phone': '+91-1234567890',
                'support_hours': 'Monday to Friday, 9:00 AM to 6:00 PM',
                'emergency_contact': '+91-9876543210'
            }
        }

        return api_success_response(faq_data)

    except Exception as e:
        return api_error_response(f'Failed to get FAQ: {str(e)}', 500)


@vendor_bp.route('/support/resources', methods=['GET'])
@vendor_required
def get_resources(user):
    """Get training resources and community links."""
    try:
        resources_data = {
            'training_materials': [
                {
                    'title': 'Vendor Onboarding Guide',
                    'description': 'Complete guide to getting started as a HomeServe Pro vendor',
                    'type': 'pdf',
                    'url': '/static/resources/vendor-onboarding-guide.pdf',
                    'duration': '15 minutes'
                },
                {
                    'title': 'Service Quality Standards',
                    'description': 'Learn about our service quality expectations and best practices',
                    'type': 'video',
                    'url': '/static/resources/quality-standards-video.mp4',
                    'duration': '20 minutes'
                },
                {
                    'title': 'Customer Communication Tips',
                    'description': 'Effective communication strategies for better customer satisfaction',
                    'type': 'article',
                    'url': '/static/resources/communication-tips.html',
                    'duration': '10 minutes'
                },
                {
                    'title': 'Safety Guidelines',
                    'description': 'Important safety protocols for different types of services',
                    'type': 'pdf',
                    'url': '/static/resources/safety-guidelines.pdf',
                    'duration': '25 minutes'
                }
            ],
            'community_links': [
                {
                    'name': 'Vendor WhatsApp Group',
                    'description': 'Connect with other vendors, share experiences, and get quick help',
                    'url': 'https://chat.whatsapp.com/vendor-community',
                    'type': 'whatsapp'
                },
                {
                    'name': 'Vendor Forum',
                    'description': 'Online forum for discussions, tips, and announcements',
                    'url': 'https://forum.homeservepro.com/vendors',
                    'type': 'forum'
                },
                {
                    'name': 'Monthly Vendor Meetup',
                    'description': 'Join our monthly virtual meetups for training and networking',
                    'url': 'https://meet.homeservepro.com/vendor-meetup',
                    'type': 'meeting'
                }
            ],
            'quick_links': [
                {
                    'name': 'Download Mobile App',
                    'url': 'https://play.google.com/store/apps/homeservepro-vendor',
                    'icon': 'mobile'
                },
                {
                    'name': 'Rate Card & Pricing Guide',
                    'url': '/static/resources/pricing-guide.pdf',
                    'icon': 'document'
                },
                {
                    'name': 'Terms & Conditions',
                    'url': '/static/legal/vendor-terms.html',
                    'icon': 'legal'
                },
                {
                    'name': 'Privacy Policy',
                    'url': '/static/legal/privacy-policy.html',
                    'icon': 'privacy'
                }
            ],
            'announcements': [
                {
                    'title': 'New Service Categories Added',
                    'message': 'We have added new service categories: Pet Care and Gardening. Update your profile to offer these services.',
                    'date': '2024-01-15',
                    'type': 'info'
                },
                {
                    'title': 'Payout Schedule Update',
                    'message': 'Starting February 1st, payouts will be processed daily for amounts above ₹1000.',
                    'date': '2024-01-10',
                    'type': 'important'
                }
            ]
        }

        return api_success_response(resources_data)

    except Exception as e:
        return api_error_response(f'Failed to get resources: {str(e)}', 500)


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


@vendor_bp.route('/verify_profile', methods=['POST'])
@vendor_required
def verify_profile(user):
    """
    Submit vendor profile for verification.
    Upload verification documents (ID proof, business license, service certification).
    """
    try:
        vendor = Vendor.find_by_user_id(str(user['_id']))

        if not vendor:
            return api_error_response('Vendor profile not found', 404)

        data = request.get_json()

        # Get document URLs from request
        documents = data.get('documents', {})

        # Validate that at least one document is provided
        if not documents:
            return api_error_response('At least one verification document is required', 400)

        # Prepare verification documents array
        verification_docs = []

        if documents.get('id_proof'):
            verification_docs.append({
                'type': 'id_proof',
                'url': documents['id_proof'],
                'uploaded_at': datetime.utcnow()
            })

        if documents.get('business_license'):
            verification_docs.append({
                'type': 'business_license',
                'url': documents['business_license'],
                'uploaded_at': datetime.utcnow()
            })

        if documents.get('service_certification'):
            verification_docs.append({
                'type': 'service_certification',
                'url': documents['service_certification'],
                'uploaded_at': datetime.utcnow()
            })

        # Update vendor profile
        vendor_id = str(vendor['_id'])
        Vendor.update(vendor_id, {
            'verification_docs': verification_docs,
            'onboarding_status': Vendor.STATUS_PENDING_VERIFICATION
        })

        # Create admin notification/verification request
        from app import mongo
        mongo.db['admin_verification_requests'].insert_one({
            'vendor_id': vendor_id,
            'vendor_name': vendor.get('name'),
            'request_type': 'profile_verification',
            'status': 'pending',
            'documents': verification_docs,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })

        # Create notification for admins
        Notification.create({
            'user_id': 'admin',  # Special admin notification
            'type': 'vendor_verification_request',
            'title': 'New Vendor Verification Request',
            'message': f'Vendor {vendor.get("name")} has submitted documents for verification',
            'data': {'vendor_id': vendor_id}
        })

        # Log verification submission
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='vendor',
            entity_id=vendor_id,
            user_id=str(user['_id']),
            details={'action': 'verification_submitted', 'documents_count': len(verification_docs)},
            ip_address=request.remote_addr
        )

        return api_success_response({
            'message': 'Verification documents submitted successfully',
            'status': 'pending_verification'
        })

    except Exception as e:
        return api_error_response(f'Failed to submit verification: {str(e)}', 500)


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

