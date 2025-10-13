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
    
    VALID_STATUSES = [STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_SUSPENDED]
    
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
        
        # Set defaults
        data.setdefault('onboarding_status', Vendor.STATUS_PENDING)
        data.setdefault('availability', False)
        data.setdefault('services', [])
        data.setdefault('kyc_docs', [])
        data.setdefault('ratings', 0.0)
        data.setdefault('total_ratings', 0)
        data.setdefault('earnings', 0.0)
        data.setdefault('completed_jobs', 0)
        data.setdefault('created_at', datetime.utcnow())
        data.setdefault('updated_at', datetime.utcnow())
        
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
            'profile_image': vendor.get('profile_image')
        }

