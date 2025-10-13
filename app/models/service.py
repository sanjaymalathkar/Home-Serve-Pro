"""
Service model for HomeServe Pro.
Manages available services and pricing.
"""

from datetime import datetime
from bson import ObjectId
from app import mongo


class Service:
    """Service model for available services."""

    COLLECTION = 'services'

    # Service categories
    CATEGORY_PLUMBING = 'plumbing'
    CATEGORY_ELECTRICAL = 'electrical'
    CATEGORY_PAINTING = 'painting'
    CATEGORY_CLEANING = 'cleaning'
    CATEGORY_CARPENTRY = 'carpentry'
    CATEGORY_APPLIANCE_REPAIR = 'appliance_repair'

    @staticmethod
    def create(data):
        """
        Create a new service.

        Args:
            data (dict): Service data

        Returns:
            str: Inserted service ID
        """
        data.setdefault('active', True)
        data.setdefault('created_at', datetime.utcnow())
        data.setdefault('updated_at', datetime.utcnow())

        result = mongo.db[Service.COLLECTION].insert_one(data)
        return str(result.inserted_id)

    @staticmethod
    def find_by_id(service_id):
        """Find service by ID."""
        try:
            return mongo.db[Service.COLLECTION].find_one({'_id': ObjectId(service_id)})
        except:
            return None

    @staticmethod
    def find_by_name(name):
        """Find service by name."""
        return mongo.db[Service.COLLECTION].find_one({'name': name})

    @staticmethod
    def find_by_category(category):
        """Find all services in a category."""
        return list(mongo.db[Service.COLLECTION].find({'category': category, 'active': True}))

    @staticmethod
    def find_all_active():
        """Find all active services."""
        return list(mongo.db[Service.COLLECTION].find({'active': True}))
    @staticmethod
    def find_all():
        """Find all services (any status)."""
        return list(mongo.db[Service.COLLECTION].find({}))



    @staticmethod
    def update(service_id, data):
        """Update service data."""
        data['updated_at'] = datetime.utcnow()

        result = mongo.db[Service.COLLECTION].update_one(
            {'_id': ObjectId(service_id)},
            {'$set': data}
        )
        return result.modified_count > 0

    @staticmethod
    def search(query, pincode=None):
        """
        Search services by name or description.

        Args:
            query (str): Search query
            pincode (str): Optional pincode for pricing

        Returns:
            list: Matching services
        """
        search_filter = {
            'active': True,
            '$or': [
                {'name': {'$regex': query, '$options': 'i'}},
                {'description': {'$regex': query, '$options': 'i'}},
                {'category': {'$regex': query, '$options': 'i'}}
            ]
        }

        return list(mongo.db[Service.COLLECTION].find(search_filter))

    @staticmethod
    def add_sub_service(service_id, sub_service):
        """Append a sub-service item with its own price and active flag."""
        # ensure an id for sub_service
        if '_id' not in sub_service:
            sub_service['_id'] = ObjectId()
        sub_service.setdefault('active', True)
        sub_service.setdefault('created_at', datetime.utcnow())
        result = mongo.db[Service.COLLECTION].update_one(
            {'_id': ObjectId(service_id)},
            {'$push': {'sub_services': sub_service}, '$set': {'updated_at': datetime.utcnow()}}
        )
        return str(sub_service['_id']) if result.modified_count > 0 else None

    @staticmethod
    def remove_sub_service(service_id, sub_id):
        """Remove a sub-service by its id."""
        result = mongo.db[Service.COLLECTION].update_one(
            {'_id': ObjectId(service_id)},
            {'$pull': {'sub_services': {'_id': ObjectId(sub_id)}}, '$set': {'updated_at': datetime.utcnow()}}
        )
        return result.modified_count > 0

    @staticmethod
    def set_commission(service_id, commission):
        """Set commission policy for a service.
        Example commission: {"type":"percent|fixed|hybrid","percent":10,"fixed":50,"cancellation_fee_percent":20}
        """
        commission = commission or {}
        result = mongo.db[Service.COLLECTION].update_one(
            {'_id': ObjectId(service_id)},
            {'$set': {'commission': commission, 'updated_at': datetime.utcnow()}}
        )
        return result.modified_count > 0

    @staticmethod
    def create_indexes():
        """Create database indexes for optimal performance."""
        mongo.db[Service.COLLECTION].create_index('name', unique=True)
        mongo.db[Service.COLLECTION].create_index('category')
        mongo.db[Service.COLLECTION].create_index('active')
        mongo.db[Service.COLLECTION].create_index([('name', 'text'), ('description', 'text')])

    @staticmethod
    def to_dict(service):
        """Convert service document to dictionary."""
        if not service:
            return None

        # Normalize sub_services for output
        sub_services = []
        for s in service.get('sub_services', []) or []:
            sub_services.append({
                'id': str(s.get('_id')) if s.get('_id') else None,
                'name': s.get('name'),
                'base_price': s.get('base_price'),
                'active': s.get('active', True)
            })

        return {
            'id': str(service['_id']),
            'name': service.get('name'),
            'description': service.get('description'),
            'category': service.get('category'),
            'base_price': service.get('base_price'),
            'duration_minutes': service.get('duration_minutes'),
            'image_url': service.get('image_url'),
            'active': service.get('active', True),
            'sub_services': sub_services,
            'commission': service.get('commission', {})
        }

