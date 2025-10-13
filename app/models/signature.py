"""
Signature model for HomeServe Pro.
Manages digital signatures with Smart Signature Vault.
"""

from datetime import datetime
from bson import ObjectId
import hashlib
from app import mongo


class Signature:
    """Signature model for digital signature verification."""
    
    COLLECTION = 'signatures'
    
    @staticmethod
    def create(data):
        """
        Create a new signature record.
        
        Args:
            data (dict): Signature data including booking_id, customer_id, signature_data
            
        Returns:
            str: Inserted signature ID
        """
        # Convert IDs to ObjectId
        if 'booking_id' in data and isinstance(data['booking_id'], str):
            data['booking_id'] = ObjectId(data['booking_id'])
        if 'customer_id' in data and isinstance(data['customer_id'], str):
            data['customer_id'] = ObjectId(data['customer_id'])
        if 'vendor_id' in data and isinstance(data['vendor_id'], str):
            data['vendor_id'] = ObjectId(data['vendor_id'])
        
        # Generate signature hash (SHA-256)
        signature_content = f"{data['booking_id']}{data['customer_id']}{datetime.utcnow().isoformat()}"
        data['signature_hash'] = hashlib.sha256(signature_content.encode()).hexdigest()
        
        # Set defaults
        data.setdefault('verified', True)
        data.setdefault('signed_at', datetime.utcnow())
        data.setdefault('created_at', datetime.utcnow())
        
        result = mongo.db[Signature.COLLECTION].insert_one(data)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_id(signature_id):
        """Find signature by ID."""
        try:
            return mongo.db[Signature.COLLECTION].find_one({'_id': ObjectId(signature_id)})
        except:
            return None
    
    @staticmethod
    def find_by_booking(booking_id):
        """Find signature by booking ID."""
        try:
            booking_oid = ObjectId(booking_id)
            return mongo.db[Signature.COLLECTION].find_one({'booking_id': booking_oid})
        except:
            return None
    
    @staticmethod
    def verify_signature(signature_id, signature_hash):
        """
        Verify signature integrity.
        
        Args:
            signature_id (str): Signature ID
            signature_hash (str): Hash to verify
            
        Returns:
            bool: True if signature is valid
        """
        signature = Signature.find_by_id(signature_id)
        if not signature:
            return False
        
        return signature.get('signature_hash') == signature_hash
    
    @staticmethod
    def create_docusign_envelope(booking_id, customer_email, vendor_name):
        """
        Create DocuSign envelope for signature request.
        
        Args:
            booking_id (str): Booking ID
            customer_email (str): Customer email
            vendor_name (str): Vendor name
            
        Returns:
            dict: Envelope information with URL
        """
        # This is a placeholder for DocuSign integration
        # In production, this would call DocuSign API
        envelope_data = {
            'envelope_id': f'env_{booking_id}_{datetime.utcnow().timestamp()}',
            'signing_url': f'https://demo.docusign.net/signing/{booking_id}',
            'status': 'sent',
            'created_at': datetime.utcnow()
        }
        
        return envelope_data
    
    @staticmethod
    def find_all(filters=None, skip=0, limit=20):
        """Find all signatures with optional filters."""
        filters = filters or {}
        return list(
            mongo.db[Signature.COLLECTION]
            .find(filters)
            .sort('created_at', -1)
            .skip(skip)
            .limit(limit)
        )
    
    @staticmethod
    def create_indexes():
        """Create database indexes for optimal performance."""
        mongo.db[Signature.COLLECTION].create_index('booking_id', unique=True)
        mongo.db[Signature.COLLECTION].create_index('customer_id')
        mongo.db[Signature.COLLECTION].create_index('signature_hash', unique=True)
        mongo.db[Signature.COLLECTION].create_index('signed_at')
    
    @staticmethod
    def to_dict(signature):
        """Convert signature document to dictionary."""
        if not signature:
            return None
        
        return {
            'id': str(signature['_id']),
            'booking_id': str(signature.get('booking_id')),
            'customer_id': str(signature.get('customer_id')),
            'vendor_id': str(signature.get('vendor_id')),
            'signature_hash': signature.get('signature_hash'),
            'signature_data': signature.get('signature_data'),
            'verified': signature.get('verified', False),
            'signed_at': signature.get('signed_at'),
            'docusign_envelope_id': signature.get('docusign_envelope_id')
        }

