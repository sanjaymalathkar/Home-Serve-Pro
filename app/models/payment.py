"""
Payment model for HomeServe Pro.
Manages payment transactions and payouts.
"""

from datetime import datetime
from bson import ObjectId
from app import mongo


class Payment:
    """Payment model for transactions."""
    
    COLLECTION = 'payments'
    
    # Payment status constants
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'
    
    # Payment type constants
    TYPE_BOOKING = 'booking'
    TYPE_PAYOUT = 'payout'
    
    @staticmethod
    def create(data):
        """
        Create a new payment record.
        
        Args:
            data (dict): Payment data
            
        Returns:
            str: Inserted payment ID
        """
        # Convert IDs to ObjectId
        if 'booking_id' in data and isinstance(data['booking_id'], str):
            data['booking_id'] = ObjectId(data['booking_id'])
        if 'customer_id' in data and isinstance(data['customer_id'], str):
            data['customer_id'] = ObjectId(data['customer_id'])
        if 'vendor_id' in data and isinstance(data['vendor_id'], str):
            data['vendor_id'] = ObjectId(data['vendor_id'])
        
        # Set defaults
        data.setdefault('status', Payment.STATUS_PENDING)
        data.setdefault('payment_type', Payment.TYPE_BOOKING)
        data.setdefault('created_at', datetime.utcnow())
        data.setdefault('updated_at', datetime.utcnow())
        
        result = mongo.db[Payment.COLLECTION].insert_one(data)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_id(payment_id):
        """Find payment by ID."""
        try:
            return mongo.db[Payment.COLLECTION].find_one({'_id': ObjectId(payment_id)})
        except:
            return None
    
    @staticmethod
    def find_by_booking(booking_id):
        """Find payment by booking ID."""
        try:
            booking_oid = ObjectId(booking_id)
            return mongo.db[Payment.COLLECTION].find_one({'booking_id': booking_oid})
        except:
            return None
    
    @staticmethod
    def find_by_vendor(vendor_id, skip=0, limit=20):
        """Find all payments for a vendor."""
        try:
            vendor_oid = ObjectId(vendor_id)
            return list(
                mongo.db[Payment.COLLECTION]
                .find({'vendor_id': vendor_oid})
                .sort('created_at', -1)
                .skip(skip)
                .limit(limit)
            )
        except:
            return []
    
    @staticmethod
    def update(payment_id, data):
        """Update payment data."""
        data['updated_at'] = datetime.utcnow()
        
        result = mongo.db[Payment.COLLECTION].update_one(
            {'_id': ObjectId(payment_id)},
            {'$set': data}
        )
        return result.modified_count > 0
    
    @staticmethod
    def update_status(payment_id, status, transaction_id=None):
        """
        Update payment status.
        
        Args:
            payment_id (str): Payment ID
            status (str): New status
            transaction_id (str): Optional transaction ID from payment gateway
        """
        update_data = {'status': status}
        if transaction_id:
            update_data['transaction_id'] = transaction_id
        
        if status == Payment.STATUS_COMPLETED:
            update_data['completed_at'] = datetime.utcnow()
        
        return Payment.update(payment_id, update_data)
    
    @staticmethod
    def create_payout(vendor_id, amount, booking_ids=None):
        """
        Create a payout record for vendor.
        
        Args:
            vendor_id (str): Vendor ID
            amount (float): Payout amount
            booking_ids (list): Optional list of booking IDs included in payout
            
        Returns:
            str: Payment ID
        """
        payout_data = {
            'vendor_id': vendor_id,
            'amount': amount,
            'payment_type': Payment.TYPE_PAYOUT,
            'status': Payment.STATUS_PENDING,
            'booking_ids': booking_ids or []
        }
        
        return Payment.create(payout_data)
    
    @staticmethod
    def get_vendor_earnings(vendor_id):
        """Calculate total earnings for a vendor."""
        try:
            vendor_oid = ObjectId(vendor_id)
            pipeline = [
                {
                    '$match': {
                        'vendor_id': vendor_oid,
                        'status': Payment.STATUS_COMPLETED,
                        'payment_type': Payment.TYPE_BOOKING
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total': {'$sum': '$amount'}
                    }
                }
            ]
            
            result = list(mongo.db[Payment.COLLECTION].aggregate(pipeline))
            return result[0]['total'] if result else 0.0
        except:
            return 0.0
    
    @staticmethod
    def find_pending_payouts():
        """Find all pending payout requests."""
        return list(
            mongo.db[Payment.COLLECTION].find({
                'payment_type': Payment.TYPE_PAYOUT,
                'status': Payment.STATUS_PENDING
            })
        )
    
    @staticmethod
    def create_indexes():
        """Create database indexes for optimal performance."""
        mongo.db[Payment.COLLECTION].create_index('booking_id')
        mongo.db[Payment.COLLECTION].create_index('customer_id')
        mongo.db[Payment.COLLECTION].create_index('vendor_id')
        mongo.db[Payment.COLLECTION].create_index('status')
        mongo.db[Payment.COLLECTION].create_index('payment_type')
        mongo.db[Payment.COLLECTION].create_index([('vendor_id', 1), ('status', 1)])
    
    @staticmethod
    def to_dict(payment):
        """Convert payment document to dictionary."""
        if not payment:
            return None
        
        return {
            'id': str(payment['_id']),
            'booking_id': str(payment.get('booking_id')) if payment.get('booking_id') else None,
            'customer_id': str(payment.get('customer_id')) if payment.get('customer_id') else None,
            'vendor_id': str(payment.get('vendor_id')) if payment.get('vendor_id') else None,
            'amount': payment.get('amount'),
            'status': payment.get('status'),
            'payment_type': payment.get('payment_type'),
            'transaction_id': payment.get('transaction_id'),
            'payment_method': payment.get('payment_method'),
            'created_at': payment.get('created_at'),
            'completed_at': payment.get('completed_at')
        }

