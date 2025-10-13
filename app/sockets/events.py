"""
SocketIO event handlers for HomeServe Pro.
Handles real-time notifications and updates.
"""

from flask_socketio import emit, join_room, leave_room, disconnect
from flask import request
from app import socketio
from app.models.user import User
import jwt
import os


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f'Client connected: {request.sid}')
    emit('connected', {'message': 'Connected to HomeServe Pro'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f'Client disconnected: {request.sid}')


@socketio.on('authenticate')
def handle_authenticate(data):
    """
    Authenticate user and join their personal room.
    
    Data:
        - token: JWT access token
    """
    try:
        token = data.get('token')
        if not token:
            emit('error', {'message': 'No token provided'})
            return
        
        # Decode JWT token
        secret_key = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        user_id = payload.get('sub')
        
        if not user_id:
            emit('error', {'message': 'Invalid token'})
            return
        
        # Verify user exists
        user = User.find_by_id(user_id)
        if not user:
            emit('error', {'message': 'User not found'})
            return
        
        # Join user's personal room
        join_room(user_id)
        
        emit('authenticated', {
            'message': 'Successfully authenticated',
            'user_id': user_id,
            'role': user.get('role')
        })
        
        print(f'User {user_id} authenticated and joined room')
        
    except jwt.ExpiredSignatureError:
        emit('error', {'message': 'Token expired'})
    except jwt.InvalidTokenError:
        emit('error', {'message': 'Invalid token'})
    except Exception as e:
        emit('error', {'message': f'Authentication failed: {str(e)}'})


@socketio.on('join_room')
def handle_join_room(data):
    """
    Join a specific room.
    
    Data:
        - room: Room ID to join
    """
    try:
        room = data.get('room')
        if room:
            join_room(room)
            emit('joined_room', {'room': room})
            print(f'Client {request.sid} joined room {room}')
    except Exception as e:
        emit('error', {'message': f'Failed to join room: {str(e)}'})


@socketio.on('leave_room')
def handle_leave_room(data):
    """
    Leave a specific room.
    
    Data:
        - room: Room ID to leave
    """
    try:
        room = data.get('room')
        if room:
            leave_room(room)
            emit('left_room', {'room': room})
            print(f'Client {request.sid} left room {room}')
    except Exception as e:
        emit('error', {'message': f'Failed to leave room: {str(e)}'})


@socketio.on('ping')
def handle_ping():
    """Handle ping for connection testing."""
    emit('pong', {'timestamp': str(request.sid)})


@socketio.on('booking_update')
def handle_booking_update(data):
    """
    Broadcast booking update to relevant users.
    
    Data:
        - booking_id: Booking ID
        - status: New status
        - customer_id: Customer user ID
        - vendor_id: Vendor user ID
    """
    try:
        booking_id = data.get('booking_id')
        status = data.get('status')
        customer_id = data.get('customer_id')
        vendor_id = data.get('vendor_id')
        
        # Emit to customer
        if customer_id:
            emit('booking_status_changed', {
                'booking_id': booking_id,
                'status': status
            }, room=customer_id)
        
        # Emit to vendor
        if vendor_id:
            emit('booking_status_changed', {
                'booking_id': booking_id,
                'status': status
            }, room=vendor_id)
        
    except Exception as e:
        emit('error', {'message': f'Failed to broadcast update: {str(e)}'})


@socketio.on('vendor_availability_changed')
def handle_vendor_availability(data):
    """
    Broadcast vendor availability change.
    
    Data:
        - vendor_id: Vendor user ID
        - available: Boolean availability status
    """
    try:
        vendor_id = data.get('vendor_id')
        available = data.get('available')
        
        # Broadcast to all connected clients (or specific rooms)
        emit('vendor_availability_update', {
            'vendor_id': vendor_id,
            'available': available
        }, broadcast=True)
        
    except Exception as e:
        emit('error', {'message': f'Failed to broadcast availability: {str(e)}'})


@socketio.on('notification')
def handle_notification(data):
    """
    Send notification to specific user.
    
    Data:
        - user_id: Target user ID
        - type: Notification type
        - title: Notification title
        - message: Notification message
    """
    try:
        user_id = data.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'User ID required'})
            return
        
        # Emit to specific user's room
        emit('new_notification', {
            'type': data.get('type'),
            'title': data.get('title'),
            'message': data.get('message'),
            'data': data.get('data', {})
        }, room=user_id)
        
    except Exception as e:
        emit('error', {'message': f'Failed to send notification: {str(e)}'})


@socketio.on_error_default
def default_error_handler(e):
    """Default error handler for SocketIO events."""
    print(f'SocketIO error: {str(e)}')
    emit('error', {'message': 'An error occurred'})

