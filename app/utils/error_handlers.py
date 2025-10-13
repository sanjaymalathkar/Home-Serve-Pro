"""
Error handlers for HomeServe Pro.
Centralized error handling for consistent API responses.
"""

from flask import jsonify
from werkzeug.exceptions import HTTPException


def handle_400_error(error):
    """Handle 400 Bad Request errors."""
    return jsonify({
        'error': 'Bad Request',
        'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
    }), 400


def handle_401_error(error):
    """Handle 401 Unauthorized errors."""
    return jsonify({
        'error': 'Unauthorized',
        'message': 'Authentication required'
    }), 401


def handle_403_error(error):
    """Handle 403 Forbidden errors."""
    return jsonify({
        'error': 'Forbidden',
        'message': 'You do not have permission to access this resource'
    }), 403


def handle_404_error(error):
    """Handle 404 Not Found errors."""
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource was not found'
    }), 404


def handle_500_error(error):
    """Handle 500 Internal Server Error."""
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred. Please try again later.'
    }), 500


def api_error_response(message, status_code=400, errors=None):
    """
    Generate a standardized API error response.
    
    Args:
        message (str): Error message
        status_code (int): HTTP status code
        errors (dict): Optional detailed errors
        
    Returns:
        tuple: JSON response and status code
    """
    response = {
        'success': False,
        'error': message
    }
    
    if errors:
        response['errors'] = errors
    
    return jsonify(response), status_code


def api_success_response(data=None, message=None, status_code=200):
    """
    Generate a standardized API success response.
    
    Args:
        data: Response data
        message (str): Optional success message
        status_code (int): HTTP status code
        
    Returns:
        tuple: JSON response and status code
    """
    response = {
        'success': True
    }
    
    if message:
        response['message'] = message
    
    if data is not None:
        response['data'] = data
    
    return jsonify(response), status_code

