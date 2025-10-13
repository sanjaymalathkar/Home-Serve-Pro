"""
Booking model for HomeServe Pro.
Manages service bookings between customers and vendors.
"""

from datetime import datetime
from bson import ObjectId
from app import mongo


class Booking:
    """Booking model for service requests."""
    
    COLLECTION = 'bookings'
    
    # Status constants
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_VERIFIED = 'verified'
    STATUS_CANCELLED = 'cancelled'
    
    VALID_STATUSES = [
        STATUS_PENDING,
        STATUS_ACCEPTED,
        STATUS_REJECTED,
        STATUS_IN_PROGRESS,
        STATUS_COMPLETED,
        STATUS_VERIFIED,
        STATUS_CANCELLED
    ]
    
    @staticmethod
    def create(data):
        """
        Create a new booking.
        
        Args:
            data (dict): Booking data
            
        Returns:
            str: Inserted booking ID
        """
        # Convert string IDs to ObjectId
        if 'customer_id' in data and isinstance(data['customer_id'], str):
            data['customer_id'] = ObjectId(data['customer_id'])
        if 'vendor_id' in data and isinstance(data['vendor_id'], str):
            data['vendor_id'] = ObjectId(data['vendor_id'])
        if 'service_id' in data and isinstance(data['service_id'], str):
            data['service_id'] = ObjectId(data['service_id'])
        
        # Set defaults
        data.setdefault('status', Booking.STATUS_PENDING)
        data.setdefault('before_photos', [])
        data.setdefault('after_photos', [])
        data.setdefault('signature_status', 'unsigned')  # unsigned, requested, signed, expired
        data.setdefault('signature_hash', None)
        data.setdefault('signature_requested_at', None)
        data.setdefault('signature_submitted_at', None)
        data.setdefault('signature_timeout_at', None)
        data.setdefault('signature_escalated', False)
        data.setdefault('payment_status', 'pending')
        data.setdefault('created_at', datetime.utcnow())
        data.setdefault('updated_at', datetime.utcnow())
        
        # Validate status
        if data.get('status') not in Booking.VALID_STATUSES:
            raise ValueError(f"Invalid status. Must be one of {Booking.VALID_STATUSES}")
        
        result = mongo.db[Booking.COLLECTION].insert_one(data)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_id(booking_id):
        """Find booking by ID."""
        try:
            return mongo.db[Booking.COLLECTION].find_one({'_id': ObjectId(booking_id)})
        except:
            return None
    
    @staticmethod
    def find_by_customer(customer_id, skip=0, limit=20):
        """Find all bookings for a customer."""
        try:
            customer_oid = ObjectId(customer_id)
            return list(
                mongo.db[Booking.COLLECTION]
                .find({'customer_id': customer_oid})
                .sort('created_at', -1)
                .skip(skip)
                .limit(limit)
            )
        except:
            return []
    
    @staticmethod
    def find_by_vendor(vendor_id, skip=0, limit=20):
        """Find all bookings for a vendor."""
        try:
            vendor_oid = ObjectId(vendor_id)
            return list(
                mongo.db[Booking.COLLECTION]
                .find({'vendor_id': vendor_oid})
                .sort('created_at', -1)
                .skip(skip)
                .limit(limit)
            )
        except:
            return []
    
    @staticmethod
    def find_by_status(status, skip=0, limit=20):
        """Find bookings by status."""
        return list(
            mongo.db[Booking.COLLECTION]
            .find({'status': status})
            .sort('created_at', -1)
            .skip(skip)
            .limit(limit)
        )
    
    @staticmethod
    def update(booking_id, data):
        """
        Update booking data.
        
        Args:
            booking_id (str): Booking ID
            data (dict): Data to update
            
        Returns:
            bool: True if updated successfully
        """
        data['updated_at'] = datetime.utcnow()
        
        result = mongo.db[Booking.COLLECTION].update_one(
            {'_id': ObjectId(booking_id)},
            {'$set': data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def update_status(booking_id, status):
        """Update booking status."""
        if status not in Booking.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        return Booking.update(booking_id, {'status': status})
    
    @staticmethod
    def add_photo(booking_id, photo_url, photo_type='before'):
        """
        Add photo to booking.
        
        Args:
            booking_id (str): Booking ID
            photo_url (str): URL of uploaded photo
            photo_type (str): 'before' or 'after'
        """
        field = f'{photo_type}_photos'
        result = mongo.db[Booking.COLLECTION].update_one(
            {'_id': ObjectId(booking_id)},
            {
                '$push': {field: photo_url},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    @staticmethod
    def find_all(filters=None, sort=None, skip=0, limit=20):
        """Find all bookings with optional filters and sorting.
        Args:
            filters (dict): Mongo query filters
            sort (list|tuple|str): e.g., [('created_at', -1)] or 'created_at'
            skip (int): number of documents to skip
            limit (int): max documents to return
        """
        filters = filters or {}
        # Coerce common ID fields from string to ObjectId when possible
        try:
            for key in ('vendor_id', 'customer_id', 'service_id', '_id'):
                if key in filters and isinstance(filters[key], str):
                    filters[key] = ObjectId(filters[key])
        except Exception:
            pass
        cursor = mongo.db[Booking.COLLECTION].find(filters)
        if sort:
            cursor = cursor.sort(sort)
        else:
            cursor = cursor.sort('created_at', -1)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    @staticmethod
    def count(filters=None):
        """Count bookings matching filters."""
        filters = filters or {}
        # Coerce common ID fields from string to ObjectId when possible
        try:
            for key in ('vendor_id', 'customer_id', 'service_id', '_id'):
                if key in filters and isinstance(filters[key], str):
                    filters[key] = ObjectId(filters[key])
        except Exception:
            pass
        return mongo.db[Booking.COLLECTION].count_documents(filters)

    @staticmethod
    def get_pending_signatures(days=2):
        """Get bookings with pending signatures older than specified days."""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        return list(
            mongo.db[Booking.COLLECTION].find({
                'status': Booking.STATUS_COMPLETED,
                'signature_status': {'$in': ['unsigned', 'requested']},
                'updated_at': {'$lt': cutoff_date}
            })
        )

    @staticmethod
    def request_signature(booking_id, timeout_hours=48):
        """Request signature for a completed booking."""
        from datetime import timedelta
        timeout_at = datetime.utcnow() + timedelta(hours=timeout_hours)

        result = mongo.db[Booking.COLLECTION].update_one(
            {'_id': ObjectId(booking_id)},
            {
                '$set': {
                    'signature_status': 'requested',
                    'signature_requested_at': datetime.utcnow(),
                    'signature_timeout_at': timeout_at,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0

    @staticmethod
    def submit_signature(booking_id, signature_hash):
        """Submit signature for a booking."""
        result = mongo.db[Booking.COLLECTION].update_one(
            {'_id': ObjectId(booking_id)},
            {
                '$set': {
                    'signature_status': 'signed',
                    'signature_hash': signature_hash,
                    'signature_submitted_at': datetime.utcnow(),
                    'status': Booking.STATUS_VERIFIED,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0

    @staticmethod
    def escalate_signature_timeout(booking_id):
        """Escalate booking due to signature timeout."""
        result = mongo.db[Booking.COLLECTION].update_one(
            {'_id': ObjectId(booking_id)},
            {
                '$set': {
                    'signature_status': 'expired',
                    'signature_escalated': True,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0

    @staticmethod
    def get_expired_signatures():
        """Get bookings with expired signature requests."""
        current_time = datetime.utcnow()

        return list(
            mongo.db[Booking.COLLECTION].find({
                'signature_status': 'requested',
                'signature_timeout_at': {'$lt': current_time},
                'signature_escalated': False
            })
        )
    
    @staticmethod
    def create_indexes():
        """Create database indexes for optimal performance."""
        mongo.db[Booking.COLLECTION].create_index('customer_id')
        mongo.db[Booking.COLLECTION].create_index('vendor_id')
        mongo.db[Booking.COLLECTION].create_index('service_id')
        mongo.db[Booking.COLLECTION].create_index('status')
        mongo.db[Booking.COLLECTION].create_index('signature_status')
        mongo.db[Booking.COLLECTION].create_index('payment_status')
        mongo.db[Booking.COLLECTION].create_index('signature_timeout_at')
        mongo.db[Booking.COLLECTION].create_index('signature_escalated')
        mongo.db[Booking.COLLECTION].create_index([('status', 1), ('created_at', -1)])
        mongo.db[Booking.COLLECTION].create_index([('vendor_id', 1), ('status', 1)])
        mongo.db[Booking.COLLECTION].create_index([('signature_status', 1), ('signature_timeout_at', 1)])
        mongo.db[Booking.COLLECTION].create_index([('status', 1), ('signature_status', 1)])
    
    @staticmethod
    def to_dict(booking):
        """Convert booking document to dictionary."""
        if not booking:
            return None
        
        return {
            'id': str(booking['_id']),
            'service_id': str(booking.get('service_id')),
            'customer_id': str(booking.get('customer_id')),
            'vendor_id': str(booking.get('vendor_id')),
            'status': booking.get('status'),
            'service_date': booking.get('service_date'),
            'service_time': booking.get('service_time'),
            'address': booking.get('address'),
            'pincode': booking.get('pincode'),
            'description': booking.get('description'),
            'before_photos': booking.get('before_photos', []),
            'after_photos': booking.get('after_photos', []),
            'signature_status': booking.get('signature_status'),
            'signature_hash': booking.get('signature_hash'),
            'payment_status': booking.get('payment_status'),
            'amount': booking.get('amount'),
            'created_at': booking.get('created_at'),
            'updated_at': booking.get('updated_at'),
            'rating': booking.get('rating'),
            'review': booking.get('review')
        }

