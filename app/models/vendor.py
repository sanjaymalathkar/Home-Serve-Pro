"""
Vendor model for HomeServe Pro.
Manages vendor-specific data and operations.
"""

from datetime import datetime
from bson import ObjectId
from app import mongo


class Vendor:
    """Vendor model for service providers."""
    
    COLLECTION = 'vendors'
    
    # Onboarding status constants
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_SUSPENDED = 'suspended'
    STATUS_INCOMPLETE = 'incomplete'
    STATUS_PENDING_VERIFICATION = 'pending_verification'
    STATUS_ACTIVE = 'active'

    VALID_STATUSES = [STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_SUSPENDED, STATUS_INCOMPLETE, STATUS_PENDING_VERIFICATION, STATUS_ACTIVE]

    # Document types for KYC
    DOC_TYPE_ID_PROOF = 'id_proof'
    DOC_TYPE_ADDRESS_PROOF = 'address_proof'
    DOC_TYPE_BUSINESS_LICENSE = 'business_license'
    DOC_TYPE_CERTIFICATION = 'certification'
    DOC_TYPE_SKILL_PROOF = 'skill_proof'
    DOC_TYPE_BANK_DETAILS = 'bank_details'

    VALID_DOC_TYPES = [DOC_TYPE_ID_PROOF, DOC_TYPE_ADDRESS_PROOF, DOC_TYPE_BUSINESS_LICENSE,
                       DOC_TYPE_CERTIFICATION, DOC_TYPE_SKILL_PROOF, DOC_TYPE_BANK_DETAILS]

    # Business types
    BUSINESS_TYPE_INDIVIDUAL = 'individual'
    BUSINESS_TYPE_PARTNERSHIP = 'partnership'
    BUSINESS_TYPE_COMPANY = 'company'
    BUSINESS_TYPE_FREELANCER = 'freelancer'

    VALID_BUSINESS_TYPES = [BUSINESS_TYPE_INDIVIDUAL, BUSINESS_TYPE_PARTNERSHIP,
                           BUSINESS_TYPE_COMPANY, BUSINESS_TYPE_FREELANCER]
    
    @staticmethod
    def create(data):
        """
        Create a new vendor profile.
        
        Args:
            data (dict): Vendor data
            
        Returns:
            str: Inserted vendor ID
        """
        # Convert user_id to ObjectId if string
        if 'user_id' in data and isinstance(data['user_id'], str):
            data['user_id'] = ObjectId(data['user_id'])
        
        # Set defaults for basic vendor data
        data.setdefault('onboarding_status', Vendor.STATUS_INCOMPLETE)
        data.setdefault('availability', False)
        data.setdefault('services', [])
        data.setdefault('kyc_docs', [])
        data.setdefault('ratings', 0.0)
        data.setdefault('total_ratings', 0)
        data.setdefault('earnings', 0.0)
        data.setdefault('completed_jobs', 0)
        data.setdefault('created_at', datetime.utcnow())
        data.setdefault('updated_at', datetime.utcnow())

        # New fields for enhanced onboarding
        data.setdefault('is_approved', False)
        data.setdefault('documents_verified', False)
        data.setdefault('payouts_enabled', False)
        data.setdefault('verification_docs', [])

        # Set defaults for registration data
        data.setdefault('business_type', Vendor.BUSINESS_TYPE_INDIVIDUAL)
        data.setdefault('business_name', '')
        data.setdefault('business_address', '')
        data.setdefault('business_registration_number', '')
        data.setdefault('tax_id', '')
        data.setdefault('pincodes', [])
        data.setdefault('service_areas', [])
        data.setdefault('experience_years', 0)
        data.setdefault('specializations', [])
        data.setdefault('languages', [])
        data.setdefault('working_hours', {})
        data.setdefault('emergency_contact', {})
        data.setdefault('bank_details', {})
        data.setdefault('profile_image', '')
        data.setdefault('portfolio_images', [])
        data.setdefault('registration_step', 1)  # Track registration progress
        data.setdefault('verification_notes', '')
        data.setdefault('rejection_reason', '')
        
        result = mongo.db[Vendor.COLLECTION].insert_one(data)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_id(vendor_id):
        """Find vendor by ID."""
        try:
            return mongo.db[Vendor.COLLECTION].find_one({'_id': ObjectId(vendor_id)})
        except:
            return None
    
    @staticmethod
    def find_by_user_id(user_id):
        """Find vendor by user ID."""
        try:
            user_oid = ObjectId(user_id)
            return mongo.db[Vendor.COLLECTION].find_one({'user_id': user_oid})
        except:
            return None
    
    @staticmethod
    def find_available_by_service(service_name, pincode=None):
        """
        Find available vendors for a specific service.
        
        Args:
            service_name (str): Service name
            pincode (str): Optional pincode filter
            
        Returns:
            list: List of available vendors
        """
        query = {
            'onboarding_status': Vendor.STATUS_APPROVED,
            'availability': True,
            'services': service_name
        }
        
        if pincode:
            query['pincodes'] = pincode
        
        return list(mongo.db[Vendor.COLLECTION].find(query))
    
    @staticmethod
    def update(vendor_id, data):
        """
        Update vendor data.
        
        Args:
            vendor_id (str): Vendor ID
            data (dict): Data to update
            
        Returns:
            bool: True if updated successfully
        """
        data['updated_at'] = datetime.utcnow()
        
        result = mongo.db[Vendor.COLLECTION].update_one(
            {'_id': ObjectId(vendor_id)},
            {'$set': data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def toggle_availability(vendor_id):
        """Toggle vendor availability status."""
        vendor = Vendor.find_by_id(vendor_id)
        if not vendor:
            return False
        
        new_status = not vendor.get('availability', False)
        return Vendor.update(vendor_id, {'availability': new_status})
    
    @staticmethod
    def update_rating(vendor_id, new_rating):
        """
        Update vendor rating with new rating.
        
        Args:
            vendor_id (str): Vendor ID
            new_rating (float): New rating (1-5)
        """
        vendor = Vendor.find_by_id(vendor_id)
        if not vendor:
            return False
        
        total_ratings = vendor.get('total_ratings', 0)
        current_rating = vendor.get('ratings', 0.0)
        
        # Calculate new average rating
        new_total = total_ratings + 1
        new_avg = ((current_rating * total_ratings) + new_rating) / new_total
        
        return Vendor.update(vendor_id, {
            'ratings': round(new_avg, 2),
            'total_ratings': new_total
        })
    
    @staticmethod
    def add_earnings(vendor_id, amount):
        """Add earnings to vendor account."""
        result = mongo.db[Vendor.COLLECTION].update_one(
            {'_id': ObjectId(vendor_id)},
            {
                '$inc': {'earnings': amount, 'completed_jobs': 1},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    @staticmethod
    def add_kyc_document(vendor_id, doc_url, doc_type):
        """Add KYC document to vendor profile."""
        doc = {
            'url': doc_url,
            'type': doc_type,
            'uploaded_at': datetime.utcnow()
        }
        
        result = mongo.db[Vendor.COLLECTION].update_one(
            {'_id': ObjectId(vendor_id)},
            {
                '$push': {'kyc_docs': doc},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    @staticmethod
    def find_all(filters=None, skip=0, limit=20):
        """Find all vendors with optional filters."""
        filters = filters or {}
        return list(
            mongo.db[Vendor.COLLECTION]
            .find(filters)
            .sort('created_at', -1)
            .skip(skip)
            .limit(limit)
        )
    
    @staticmethod
    def count(filters=None):
        """Count vendors matching filters."""
        filters = filters or {}
        return mongo.db[Vendor.COLLECTION].count_documents(filters)
    
    @staticmethod
    def find_pending_onboarding():
        """Find vendors pending onboarding approval."""
        return list(
            mongo.db[Vendor.COLLECTION].find({
                'onboarding_status': Vendor.STATUS_PENDING
            })
        )
    
    @staticmethod
    def create_indexes():
        """Create database indexes for optimal performance."""
        mongo.db[Vendor.COLLECTION].create_index('user_id', unique=True)
        mongo.db[Vendor.COLLECTION].create_index('onboarding_status')
        mongo.db[Vendor.COLLECTION].create_index('availability')
        mongo.db[Vendor.COLLECTION].create_index('services')
        mongo.db[Vendor.COLLECTION].create_index('pincodes')
        mongo.db[Vendor.COLLECTION].create_index([('availability', 1), ('ratings', -1)])
    
    @staticmethod
    def to_dict(vendor):
        """Convert vendor document to dictionary."""
        if not vendor:
            return None
        
        return {
            'id': str(vendor['_id']),
            'user_id': str(vendor.get('user_id')),
            'name': vendor.get('name'),
            'services': vendor.get('services', []),
            'pincodes': vendor.get('pincodes', []),
            'availability': vendor.get('availability', False),
            'onboarding_status': vendor.get('onboarding_status'),
            'kyc_docs': vendor.get('kyc_docs', []),
            'ratings': vendor.get('ratings', 0.0),
            'total_ratings': vendor.get('total_ratings', 0),
            'earnings': vendor.get('earnings', 0.0),
            'completed_jobs': vendor.get('completed_jobs', 0),
            'created_at': vendor.get('created_at'),
            'profile_image': vendor.get('profile_image'),
            'is_approved': vendor.get('is_approved', False),
            'documents_verified': vendor.get('documents_verified', False),
            'payouts_enabled': vendor.get('payouts_enabled', False),
            'verification_docs': vendor.get('verification_docs', []),
            'rejection_reason': vendor.get('rejection_reason', ''),
            'phone': vendor.get('phone', ''),
            'email': vendor.get('email', ''),
            'address': vendor.get('address', ''),
            'bank_details': vendor.get('bank_details', {})
        }

    @staticmethod
    def update_registration_step(vendor_id, step, data=None):
        """
        Update vendor registration step and associated data.

        Args:
            vendor_id (str): Vendor ID
            step (int): Registration step (1-5)
            data (dict): Optional additional data to update

        Returns:
            bool: True if updated successfully
        """
        update_data = {
            'registration_step': step,
            'updated_at': datetime.utcnow()
        }

        if data:
            update_data.update(data)

        result = mongo.db[Vendor.COLLECTION].update_one(
            {'_id': ObjectId(vendor_id)},
            {'$set': update_data}
        )
        return result.modified_count > 0

    @staticmethod
    def complete_registration(vendor_id):
        """
        Mark vendor registration as complete and set status to pending approval.

        Args:
            vendor_id (str): Vendor ID

        Returns:
            bool: True if updated successfully
        """
        result = mongo.db[Vendor.COLLECTION].update_one(
            {'_id': ObjectId(vendor_id)},
            {
                '$set': {
                    'onboarding_status': Vendor.STATUS_PENDING,
                    'registration_step': 6,  # Registration complete
                    'updated_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0

    @staticmethod
    def get_registration_progress(vendor_id):
        """
        Get vendor registration progress and completion status.

        Args:
            vendor_id (str): Vendor ID

        Returns:
            dict: Registration progress information
        """
        vendor = Vendor.find_by_id(vendor_id)
        if not vendor:
            return None

        steps = {
            1: {'name': 'Personal Information', 'completed': bool(vendor.get('name'))},
            2: {'name': 'Business Details', 'completed': bool(vendor.get('business_type'))},
            3: {'name': 'Service Information', 'completed': len(vendor.get('services', [])) > 0},
            4: {'name': 'Document Upload', 'completed': len(vendor.get('kyc_docs', [])) >= 2},
            5: {'name': 'Bank Details', 'completed': bool(vendor.get('bank_details', {}).get('account_number'))}
        }

        current_step = vendor.get('registration_step', 1)
        completed_steps = sum(1 for step in steps.values() if step['completed'])
        progress_percentage = (completed_steps / len(steps)) * 100

        return {
            'current_step': current_step,
            'steps': steps,
            'completed_steps': completed_steps,
            'total_steps': len(steps),
            'progress_percentage': progress_percentage,
            'is_complete': completed_steps == len(steps),
            'status': vendor.get('onboarding_status')
        }

