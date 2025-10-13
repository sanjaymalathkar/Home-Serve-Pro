"""
Configuration module for HomeServe Pro application.
Handles different environment configurations (Development, Testing, Production).
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration class with common settings."""
    
    # Flask Core Settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # MongoDB Configuration
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/homeservepro')
    MONGO_DBNAME = os.getenv('MONGO_DBNAME', 'homeservepro')
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 1)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 30)))
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SECURE = False  # Set to True in production with HTTPS
    JWT_COOKIE_CSRF_PROTECT = True
    
    # Payment Gateway (Stripe)
    STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', '')
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    
    # DocuSign Configuration
    DOCUSIGN_INTEGRATION_KEY = os.getenv('DOCUSIGN_INTEGRATION_KEY', '')
    DOCUSIGN_USER_ID = os.getenv('DOCUSIGN_USER_ID', '')
    DOCUSIGN_ACCOUNT_ID = os.getenv('DOCUSIGN_ACCOUNT_ID', '')
    DOCUSIGN_PRIVATE_KEY_PATH = os.getenv('DOCUSIGN_PRIVATE_KEY_PATH', './keys/docusign_private.key')
    DOCUSIGN_BASE_PATH = os.getenv('DOCUSIGN_BASE_PATH', 'https://demo.docusign.net/restapi')
    
    # Google Maps API
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')

    # Google AI API (for Chatbot)
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'gif'}
    
    # Security Settings
    BCRYPT_LOG_ROUNDS = int(os.getenv('BCRYPT_LOG_ROUNDS', 12))
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('RATELIMIT_STORAGE_URL', 'memory://')
    RATELIMIT_DEFAULT = "200 per day, 50 per hour"
    
    # SocketIO Configuration
    SOCKETIO_MESSAGE_QUEUE = os.getenv('SOCKETIO_MESSAGE_QUEUE', None)
    SOCKETIO_ASYNC_MODE = os.getenv('SOCKETIO_ASYNC_MODE', 'eventlet')
    
    # AI/ML Configuration
    AI_MODEL_PATH = os.getenv('AI_MODEL_PATH', './models')
    PINCODE_CLUSTERING_MODEL = os.getenv('PINCODE_CLUSTERING_MODEL', 'pincode_cluster.pkl')
    TRAVEL_TIME_MODEL = os.getenv('TRAVEL_TIME_MODEL', 'travel_time_model.h5')
    
    # Application Settings
    APP_NAME = os.getenv('APP_NAME', 'HomeServe Pro')
    APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@homeservepro.com')
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # Session Configuration
    SESSION_COOKIE_SECURE = False  # Set to True in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)


class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    DEBUG = True
    TESTING = False
    
    # More verbose logging in development
    LOG_LEVEL = 'DEBUG'


class TestingConfig(Config):
    """Testing environment configuration."""
    
    DEBUG = False
    TESTING = True
    
    # Use separate test database
    MONGO_URI = 'mongodb://localhost:27017/homeservepro_test'
    MONGO_DBNAME = 'homeservepro_test'
    
    # Disable CSRF for testing
    JWT_COOKIE_CSRF_PROTECT = False
    WTF_CSRF_ENABLED = False
    
    # Faster password hashing for tests
    BCRYPT_LOG_ROUNDS = 4


class ProductionConfig(Config):
    """Production environment configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    JWT_COOKIE_SECURE = True
    
    # Production logging
    LOG_LEVEL = 'INFO'
    
    # Ensure critical settings are set
    @classmethod
    def init_app(cls, app):
        """Initialize production-specific settings."""
        Config.init_app(app)
        
        # Ensure critical environment variables are set
        assert os.getenv('SECRET_KEY'), 'SECRET_KEY must be set in production'
        assert os.getenv('JWT_SECRET_KEY'), 'JWT_SECRET_KEY must be set in production'
        assert os.getenv('MONGO_URI'), 'MONGO_URI must be set in production'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """Get configuration based on environment."""
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])

