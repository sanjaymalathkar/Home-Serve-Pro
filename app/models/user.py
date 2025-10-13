"""
User model for HomeServe Pro.
Handles customer, vendor, and admin user data.
"""

from datetime import datetime
from bson import ObjectId
from app import mongo, bcrypt


class User:
    """User model for all user types (customer, vendor, admin roles)."""
    
    COLLECTION = 'users'
    
    # Role constants
    ROLE_CUSTOMER = 'customer'
    ROLE_VENDOR = 'vendor'
    ROLE_ONBOARD_MANAGER = 'onboard_manager'
    ROLE_OPS_MANAGER = 'ops_manager'
    ROLE_SUPER_ADMIN = 'super_admin'
    
    VALID_ROLES = [
        ROLE_CUSTOMER,
        ROLE_VENDOR,
        ROLE_ONBOARD_MANAGER,
        ROLE_OPS_MANAGER,
        ROLE_SUPER_ADMIN
    ]
    
    @staticmethod
    def create(data):
        """
        Create a new user.
        
        Args:
            data (dict): User data including email, password, role, etc.
            
        Returns:
            str: Inserted user ID
        """
        # Hash password
        if 'password' in data:
            data['password'] = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        
        # Set defaults
        data.setdefault('verified', False)
        data.setdefault('active', True)
        data.setdefault('created_at', datetime.utcnow())
        data.setdefault('updated_at', datetime.utcnow())
        
        # Validate role
        if data.get('role') not in User.VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of {User.VALID_ROLES}")
        
        result = mongo.db[User.COLLECTION].insert_one(data)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_id(user_id):
        """Find user by ID."""
        try:
            return mongo.db[User.COLLECTION].find_one({'_id': ObjectId(user_id)})
        except:
            return None
    
    @staticmethod
    def find_by_email(email):
        """Find user by email."""
        return mongo.db[User.COLLECTION].find_one({'email': email.lower()})
    
    @staticmethod
    def find_by_phone(phone):
        """Find user by phone number."""
        return mongo.db[User.COLLECTION].find_one({'phone': phone})
    
    @staticmethod
    def update(user_id, data):
        """
        Update user data.
        
        Args:
            user_id (str): User ID
            data (dict): Data to update
            
        Returns:
            bool: True if updated successfully
        """
        data['updated_at'] = datetime.utcnow()
        
        # Hash password if being updated
        if 'password' in data:
            data['password'] = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        
        result = mongo.db[User.COLLECTION].update_one(
            {'_id': ObjectId(user_id)},
            {'$set': data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete(user_id):
        """Soft delete user by marking as inactive."""
        return User.update(user_id, {'active': False})
    
    @staticmethod
    def verify_password(user, password):
        """
        Verify user password.
        
        Args:
            user (dict): User document
            password (str): Plain text password
            
        Returns:
            bool: True if password matches
        """
        return bcrypt.check_password_hash(user['password'], password)
    
    @staticmethod
    def find_all(filters=None, skip=0, limit=20):
        """
        Find all users with optional filters.
        
        Args:
            filters (dict): MongoDB query filters
            skip (int): Number of documents to skip
            limit (int): Maximum number of documents to return
            
        Returns:
            list: List of user documents
        """
        filters = filters or {}
        return list(mongo.db[User.COLLECTION].find(filters).skip(skip).limit(limit))
    
    @staticmethod
    def count(filters=None):
        """Count users matching filters."""
        filters = filters or {}
        return mongo.db[User.COLLECTION].count_documents(filters)
    
    @staticmethod
    def create_indexes():
        """Create database indexes for optimal performance."""
        mongo.db[User.COLLECTION].create_index('email', unique=True)
        mongo.db[User.COLLECTION].create_index('phone')
        mongo.db[User.COLLECTION].create_index('role')
        mongo.db[User.COLLECTION].create_index('pincode')
        mongo.db[User.COLLECTION].create_index([('email', 1), ('role', 1)])
    
    @staticmethod
    def to_dict(user):
        """
        Convert user document to dictionary (excluding sensitive data).
        
        Args:
            user (dict): User document from MongoDB
            
        Returns:
            dict: Sanitized user data
        """
        if not user:
            return None
        
        return {
            'id': str(user['_id']),
            'email': user.get('email'),
            'name': user.get('name'),
            'phone': user.get('phone'),
            'role': user.get('role'),
            'pincode': user.get('pincode'),
            'address': user.get('address'),
            'verified': user.get('verified', False),
            'active': user.get('active', True),
            'created_at': user.get('created_at'),
            'profile_image': user.get('profile_image')
        }

