"""
Notification model for HomeServe Pro.
Manages real-time notifications for all users.
"""

from datetime import datetime
from bson import ObjectId
from app import mongo


class Notification:
    """Notification model for user notifications."""

    COLLECTION = 'notifications'

    # Notification types
    TYPE_BOOKING_CREATED = 'booking_created'
    TYPE_BOOKING_ACCEPTED = 'booking_accepted'
    TYPE_BOOKING_REJECTED = 'booking_rejected'
    TYPE_BOOKING_COMPLETED = 'booking_completed'
    TYPE_SIGNATURE_REQUEST = 'signature_request'
    TYPE_SIGNATURE_REQUIRED = 'signature_required'
    TYPE_SIGNATURE_COMPLETED = 'signature_completed'
    TYPE_SIGNATURE_REMINDER = 'signature_reminder'
    TYPE_ESCALATION = 'escalation'
    TYPE_PAYMENT_RECEIVED = 'payment_received'
    TYPE_PAYMENT_RELEASED = 'payment_released'
    TYPE_VENDOR_APPROVED = 'vendor_approved'
    TYPE_VENDOR_REJECTED = 'vendor_rejected'
    TYPE_VENDOR_REGISTRATION = 'vendor_registration'

    @staticmethod
    def create(data):
        """
        Create a new notification.

        Args:
            data (dict): Notification data

        Returns:
            str: Inserted notification ID
        """
        # Convert user_id to ObjectId
        if 'user_id' in data and isinstance(data['user_id'], str):
            data['user_id'] = ObjectId(data['user_id'])

        # Set defaults
        data.setdefault('read', False)
        data.setdefault('created_at', datetime.utcnow())

        result = mongo.db[Notification.COLLECTION].insert_one(data)
        return str(result.inserted_id)

    @staticmethod
    def find_by_user(user_id, unread_only=False, skip=0, limit=20):
        """
        Find notifications for a user.

        Args:
            user_id (str): User ID
            unread_only (bool): Return only unread notifications
            skip (int): Number to skip
            limit (int): Maximum number to return

        Returns:
            list: List of notifications
        """
        try:
            user_oid = ObjectId(user_id)
            query = {'user_id': user_oid}

            if unread_only:
                query['read'] = False

            return list(
                mongo.db[Notification.COLLECTION]
                .find(query)
                .sort('created_at', -1)
                .skip(skip)
                .limit(limit)
            )
        except:
            return []


    @staticmethod
    def find_all(filters=None, sort=None, skip=0, limit=20):
        """Generic find for notifications with optional filters, sort, skip, and limit.
        Args:
            filters (dict): Mongo query filters
            sort (list|tuple): e.g., [('created_at', -1)]
            skip (int): number of documents to skip
            limit (int): max documents to return
        Returns:
            list: List of notifications
        """
        filters = filters or {}
        # Coerce string IDs to ObjectId when applicable
        try:
            if 'user_id' in filters and isinstance(filters['user_id'], str):
                filters['user_id'] = ObjectId(filters['user_id'])
        except Exception:
            pass
        cursor = mongo.db[Notification.COLLECTION].find(filters)
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)
    @staticmethod
    def count(filters=None):
        """Count notifications matching filters."""
        filters = filters or {}
        try:
            if 'user_id' in filters and isinstance(filters['user_id'], str):
                filters['user_id'] = ObjectId(filters['user_id'])
        except Exception:
            pass
        return mongo.db[Notification.COLLECTION].count_documents(filters)




    @staticmethod
    def mark_as_read(notification_id):
        """Mark notification as read."""
        result = mongo.db[Notification.COLLECTION].update_one(
            {'_id': ObjectId(notification_id)},
            {'$set': {'read': True, 'read_at': datetime.utcnow()}}
        )
        return result.modified_count > 0

    @staticmethod
    def mark_all_as_read(user_id):
        """Mark all notifications as read for a user."""
        try:
            user_oid = ObjectId(user_id)
            result = mongo.db[Notification.COLLECTION].update_many(
                {'user_id': user_oid, 'read': False},
                {'$set': {'read': True, 'read_at': datetime.utcnow()}}
            )
            return result.modified_count
        except:
            return 0

    @staticmethod
    def count_unread(user_id):
        """Count unread notifications for a user."""
        try:
            user_oid = ObjectId(user_id)
            return mongo.db[Notification.COLLECTION].count_documents({
                'user_id': user_oid,
                'read': False
            })
        except:
            return 0

    @staticmethod
    def delete_old_notifications(days=30):
        """Delete notifications older than specified days."""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = mongo.db[Notification.COLLECTION].delete_many({
            'created_at': {'$lt': cutoff_date},
            'read': True
        })
        return result.deleted_count

    @staticmethod
    def create_indexes():
        """Create database indexes for optimal performance."""
        mongo.db[Notification.COLLECTION].create_index('user_id')
        mongo.db[Notification.COLLECTION].create_index('read')
        mongo.db[Notification.COLLECTION].create_index([('user_id', 1), ('read', 1), ('created_at', -1)])

    @staticmethod
    def to_dict(notification):
        """Convert notification document to dictionary."""
        if not notification:
            return None

        return {
            'id': str(notification['_id']),
            'user_id': str(notification.get('user_id')),
            'type': notification.get('type'),
            'title': notification.get('title'),
            'message': notification.get('message'),
            'data': notification.get('data', {}),
            'read': notification.get('read', False),
            'created_at': notification.get('created_at'),
            'read_at': notification.get('read_at')
        }

