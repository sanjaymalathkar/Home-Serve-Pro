"""
Main entry point for HomeServe Pro application.
Initializes and runs the Flask application with SocketIO support.
"""

import os
from app import create_app, socketio
from config import get_config

# Get environment and create app
env = os.getenv('FLASK_ENV', 'development')
app = create_app(get_config(env))

if __name__ == '__main__':
    # Run with SocketIO support
    port = int(os.getenv('PORT', 5001))  # Use port 5001 by default
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=app.config['DEBUG'],
        use_reloader=app.config['DEBUG']
    )

