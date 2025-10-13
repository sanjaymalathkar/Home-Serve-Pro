"""
Application factory for HomeServe Pro.
Initializes Flask app with all extensions and blueprints.
"""

from flask import Flask
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

# Initialize extensions
mongo = PyMongo()
jwt = JWTManager()
bcrypt = Bcrypt()
socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


def create_app(config_class):
    """
    Application factory pattern.
    Creates and configures the Flask application.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions with app
    mongo.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])

    # Initialize SocketIO (without message queue for development)
    message_queue = app.config.get('SOCKETIO_MESSAGE_QUEUE')
    if message_queue:
        socketio.init_app(app, message_queue=message_queue)
    else:
        socketio.init_app(app)

    limiter.init_app(app)
    
    # Create upload folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['AI_MODEL_PATH'], exist_ok=True)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register JWT handlers
    register_jwt_handlers(app)
    
    # Register SocketIO events
    register_socketio_events(app)
    
    # Register CLI commands
    register_cli_commands(app)
    
    return app


def register_blueprints(app):
    """Register all application blueprints."""
    
    # Import blueprints
    from app.routes.views import views_bp
    from app.routes.auth import auth_bp
    from app.routes.customer import customer_bp
    from app.routes.vendor import vendor_bp
    from app.routes.onboard_manager import onboard_manager_bp
    from app.routes.ops_manager import ops_manager_bp
    from app.routes.super_admin import super_admin_bp
    from app.routes.common import common_bp
    from app.routes.chatbot import chatbot_bp

    # Register blueprints with URL prefixes
    app.register_blueprint(views_bp)  # No prefix for root routes
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(customer_bp, url_prefix='/api/customer')
    app.register_blueprint(vendor_bp, url_prefix='/api/vendor')
    app.register_blueprint(onboard_manager_bp, url_prefix='/api/onboard-manager')
    app.register_blueprint(ops_manager_bp, url_prefix='/api/ops-manager')
    app.register_blueprint(super_admin_bp, url_prefix='/api/super_admin')
    app.register_blueprint(common_bp, url_prefix='/api')
    app.register_blueprint(chatbot_bp, url_prefix='/api/chatbot')


def register_error_handlers(app):
    """Register custom error handlers."""
    
    from app.utils.error_handlers import (
        handle_400_error,
        handle_401_error,
        handle_403_error,
        handle_404_error,
        handle_500_error
    )
    
    app.register_error_handler(400, handle_400_error)
    app.register_error_handler(401, handle_401_error)
    app.register_error_handler(403, handle_403_error)
    app.register_error_handler(404, handle_404_error)
    app.register_error_handler(500, handle_500_error)


def register_jwt_handlers(app):
    """Register JWT callback handlers."""

    from app.utils.jwt_handlers import (
        user_identity_lookup,
        user_lookup_callback,
        expired_token_callback,
        invalid_token_callback,
        unauthorized_callback
    )

    # Register JWT callbacks using decorators
    @jwt.user_identity_loader
    def _user_identity_loader(user):
        return user_identity_lookup(user)

    @jwt.user_lookup_loader
    def _user_lookup_loader(_jwt_header, jwt_data):
        return user_lookup_callback(_jwt_header, jwt_data)

    @jwt.expired_token_loader
    def _expired_token_loader(jwt_header, jwt_payload):
        return expired_token_callback(jwt_header, jwt_payload)

    @jwt.invalid_token_loader
    def _invalid_token_loader(error):
        return invalid_token_callback(error)

    @jwt.unauthorized_loader
    def _unauthorized_loader(error):
        return unauthorized_callback(error)


def register_socketio_events(app):
    """Register SocketIO event handlers."""
    
    from app.sockets import events
    # Events are registered via decorators in the events module


def register_cli_commands(app):
    """Register custom CLI commands."""
    
    from app.cli import init_db, create_admin, seed_data
    
    app.cli.add_command(init_db)
    app.cli.add_command(create_admin)
    app.cli.add_command(seed_data)

