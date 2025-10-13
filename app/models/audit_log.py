"""
Audit Log model for HomeServe Pro.
Immutable logging system for all critical operations.
"""

from datetime import datetime
from bson import ObjectId
from app import mongo


class AuditLog:
    """Audit Log model for immutable operation tracking."""
    
    COLLECTION = 'audit_logs'
    
    # Action types
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'
    ACTION_SIGNATURE = 'signature'
    ACTION_ESCALATION = 'escalation'
    ACTION_PAYMENT = 'payment'
    ACTION_STATUS_CHANGE = 'status_change'
    
    @staticmethod
    def log(action, entity_type, entity_id, user_id, details=None, ip_address=None):
        """
        Create an immutable audit log entry.
        
        Args:
            action (str): Action performed
            entity_type (str): Type of entity (user, booking, payment, etc.)
            entity_id (str): ID of the entity
            user_id (str): ID of user performing action
            details (dict): Additional details about the action
            ip_address (str): IP address of the request
            
        Returns:
            str: Inserted log ID
        """
        log_entry = {
            'action': action,
            'entity_type': entity_type,
            'entity_id': str(entity_id),
            'user_id': str(user_id),
            'details': details or {},
            'ip_address': ip_address,
            'timestamp': datetime.utcnow()
        }
        
        result = mongo.db[AuditLog.COLLECTION].insert_one(log_entry)
        return str(result.inserted_id)
    
    @staticmethod
    def find_by_entity(entity_type, entity_id, skip=0, limit=50):
        """Find all logs for a specific entity."""
        return list(
            mongo.db[AuditLog.COLLECTION]
            .find({
                'entity_type': entity_type,
                'entity_id': str(entity_id)
            })
            .sort('timestamp', -1)
            .skip(skip)
            .limit(limit)
        )
    
    @staticmethod
    def find_by_user(user_id, skip=0, limit=50):
        """Find all logs for a specific user."""
        return list(
            mongo.db[AuditLog.COLLECTION]
            .find({'user_id': str(user_id)})
            .sort('timestamp', -1)
            .skip(skip)
            .limit(limit)
        )
    
    @staticmethod
    def find_by_action(action, skip=0, limit=50):
        """Find all logs for a specific action type."""
        return list(
            mongo.db[AuditLog.COLLECTION]
            .find({'action': action})
            .sort('timestamp', -1)
            .skip(skip)
            .limit(limit)
        )
    
    @staticmethod
    def find_all(filters=None, skip=0, limit=50):
        """Find all audit logs with optional filters."""
        filters = filters or {}
        return list(
            mongo.db[AuditLog.COLLECTION]
            .find(filters)
            .sort('timestamp', -1)
            .skip(skip)
            .limit(limit)
        )
    
    @staticmethod
    def count(filters=None):
        """Count audit logs matching filters."""
        filters = filters or {}
        return mongo.db[AuditLog.COLLECTION].count_documents(filters)
    
    @staticmethod
    def create_indexes():
        """Create database indexes for optimal performance."""
        mongo.db[AuditLog.COLLECTION].create_index('entity_type')
        mongo.db[AuditLog.COLLECTION].create_index('entity_id')
        mongo.db[AuditLog.COLLECTION].create_index('user_id')
        mongo.db[AuditLog.COLLECTION].create_index('action')
        mongo.db[AuditLog.COLLECTION].create_index('timestamp')
        mongo.db[AuditLog.COLLECTION].create_index([('entity_type', 1), ('entity_id', 1), ('timestamp', -1)])
    
    @staticmethod
    def to_dict(log):
        """Convert audit log document to dictionary."""
        if not log:
            return None
        
        return {
            'id': str(log['_id']),
            'action': log.get('action'),
            'entity_type': log.get('entity_type'),
            'entity_id': log.get('entity_id'),
            'user_id': log.get('user_id'),
            'details': log.get('details', {}),
            'ip_address': log.get('ip_address'),
            'timestamp': log.get('timestamp')
        }

