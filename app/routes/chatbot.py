"""
Chatbot API Routes
Provides endpoints for AI chatbot interactions
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.chatbot_service import ChatbotService, ai_chatbot
from app.utils.decorators import role_required
from app.utils.error_handlers import api_error_response, api_success_response
from app.models.user import User
from app.models.booking import Booking
from app.models.service import Service

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api/chatbot')


@chatbot_bp.route('/message', methods=['POST'])
@jwt_required()
def send_message():
    """
    Send a message to the chatbot
    
    Request Body:
        {
            "message": "What's my booking status?"
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "message": "Response from chatbot",
                "intent": "booking_status",
                "quick_replies": ["View Details", "All Bookings"],
                "action": "show_bookings",
                "timestamp": "2024-01-01T12:00:00"
            }
        }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'message' not in data:
            return api_error_response('Message is required', 400)
        
        message = data['message'].strip()
        
        if not message:
            return api_error_response('Message cannot be empty', 400)
        
        if len(message) > 500:
            return api_error_response('Message too long (max 500 characters)', 400)
        
        # Get user info
        user = User.find_by_id(user_id)
        if not user:
            return api_error_response('User not found', 404)

        user_role = user.get('role', 'customer')

        # Build context for AI
        context = {}

        # Add bookings context for customers and vendors
        if user_role == 'customer':
            bookings = list(Booking.find_by_customer(user_id))
            context['bookings'] = bookings
        elif user_role == 'vendor':
            bookings = list(Booking.find_by_vendor(user_id))
            context['bookings'] = bookings

        # Add services context
        services = list(Service.find_all_active())
        context['services'] = services

        # Try Google AI first, fallback to pattern-based
        try:
            ai_response = ai_chatbot.generate_response(message, user_role, context)

            response = {
                'message': ai_response,
                'intent': 'general',
                'quick_replies': [],
                'action': None,
                'timestamp': None,
                'ai_powered': True
            }

            return api_success_response(response, 'Message processed successfully')

        except Exception as e:
            print(f"AI response failed, using pattern-based: {e}")
            # Fallback to pattern-based chatbot
            response = ChatbotService.process_message(user_id, message)

            if 'error' in response:
                return api_error_response(response['error'], 400)

            response['ai_powered'] = False
            return api_success_response(response, 'Message processed successfully')
        
    except Exception as e:
        return api_error_response(f'Failed to process message: {str(e)}', 500)


@chatbot_bp.route('/clear', methods=['POST'])
@jwt_required()
def clear_conversation():
    """
    Clear conversation history
    
    Returns:
        {
            "success": true,
            "message": "Conversation cleared"
        }
    """
    try:
        user_id = get_jwt_identity()
        
        ChatbotService.clear_conversation(user_id)
        
        return api_success_response(None, 'Conversation cleared successfully')
        
    except Exception as e:
        return api_error_response(f'Failed to clear conversation: {str(e)}', 500)


@chatbot_bp.route('/suggestions', methods=['GET'])
@jwt_required()
def get_suggestions():
    """
    Get suggested questions based on user role
    
    Returns:
        {
            "success": true,
            "data": {
                "suggestions": [
                    "What's my booking status?",
                    "Book a service",
                    "View my payments"
                ]
            }
        }
    """
    try:
        user_id = get_jwt_identity()
        user = User.find_by_id(user_id)
        
        if not user:
            return api_error_response('User not found', 404)
        
        role = user.get('role', 'customer')
        
        # Role-specific suggestions
        suggestions = {
            'customer': [
                "What's my booking status?",
                "Book a plumbing service",
                "Show my payment history",
                "How do I sign a document?",
                "Rate my last service",
                "View available services"
            ],
            'vendor': [
                "Show my pending jobs",
                "What are my earnings?",
                "Toggle my availability",
                "How do I upload photos?",
                "Request customer signature",
                "View my performance stats"
            ],
            'onboard_manager': [
                "Show pending vendor applications",
                "How do I approve a vendor?",
                "Search for a vendor",
                "View onboarding statistics",
                "Review KYC documents"
            ],
            'ops_manager': [
                "Show live operations",
                "Pending signatures",
                "Approve payments",
                "View operational alerts",
                "Monitor booking trends"
            ],
            'super_admin': [
                "Show system analytics",
                "Manage users",
                "View service catalog",
                "Approve payouts",
                "View audit logs",
                "System statistics"
            ]
        }
        
        return api_success_response({
            'suggestions': suggestions.get(role, suggestions['customer'])
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get suggestions: {str(e)}', 500)


@chatbot_bp.route('/quick-actions', methods=['GET'])
@jwt_required()
def get_quick_actions():
    """
    Get quick action buttons based on user role
    
    Returns:
        {
            "success": true,
            "data": {
                "actions": [
                    {
                        "label": "Book Service",
                        "action": "create_booking",
                        "icon": "calendar"
                    }
                ]
            }
        }
    """
    try:
        user_id = get_jwt_identity()
        user = User.find_by_id(user_id)
        
        if not user:
            return api_error_response('User not found', 404)
        
        role = user.get('role', 'customer')
        
        # Role-specific quick actions
        actions = {
            'customer': [
                {'label': 'Book Service', 'action': 'create_booking', 'icon': 'calendar'},
                {'label': 'My Bookings', 'action': 'view_bookings', 'icon': 'list'},
                {'label': 'Pending Signatures', 'action': 'view_signatures', 'icon': 'edit'},
                {'label': 'Payment History', 'action': 'view_payments', 'icon': 'credit-card'}
            ],
            'vendor': [
                {'label': 'Pending Jobs', 'action': 'view_jobs', 'icon': 'briefcase'},
                {'label': 'Toggle Availability', 'action': 'toggle_availability', 'icon': 'power'},
                {'label': 'My Earnings', 'action': 'view_earnings', 'icon': 'dollar-sign'},
                {'label': 'Performance', 'action': 'view_stats', 'icon': 'trending-up'}
            ],
            'onboard_manager': [
                {'label': 'Pending Vendors', 'action': 'view_pending_vendors', 'icon': 'users'},
                {'label': 'Search Vendors', 'action': 'search_vendors', 'icon': 'search'},
                {'label': 'Statistics', 'action': 'view_stats', 'icon': 'bar-chart'}
            ],
            'ops_manager': [
                {'label': 'Live Jobs', 'action': 'view_live_jobs', 'icon': 'activity'},
                {'label': 'Pending Signatures', 'action': 'view_signatures', 'icon': 'edit'},
                {'label': 'Payment Approvals', 'action': 'view_payments', 'icon': 'check-circle'},
                {'label': 'Alerts', 'action': 'view_alerts', 'icon': 'bell'}
            ],
            'super_admin': [
                {'label': 'Analytics', 'action': 'view_analytics', 'icon': 'pie-chart'},
                {'label': 'Manage Users', 'action': 'manage_users', 'icon': 'users'},
                {'label': 'Services', 'action': 'manage_services', 'icon': 'tool'},
                {'label': 'Audit Logs', 'action': 'view_audit_logs', 'icon': 'file-text'}
            ]
        }
        
        return api_success_response({
            'actions': actions.get(role, actions['customer'])
        })
        
    except Exception as e:
        return api_error_response(f'Failed to get quick actions: {str(e)}', 500)


@chatbot_bp.route('/context', methods=['GET'])
@jwt_required()
def get_context():
    """
    Get current conversation context
    
    Returns:
        {
            "success": true,
            "data": {
                "last_intent": "booking_status",
                "history": [...]
            }
        }
    """
    try:
        user_id = get_jwt_identity()
        
        from app.services.chatbot_service import ContextManager
        context = ContextManager.get_context(user_id)
        
        # Remove sensitive data
        safe_context = {
            'last_intent': context.get('last_intent'),
            'history_count': len(context.get('history', []))
        }
        
        return api_success_response(safe_context)
        
    except Exception as e:
        return api_error_response(f'Failed to get context: {str(e)}', 500)


@chatbot_bp.route('/feedback', methods=['POST'])
@jwt_required()
def submit_feedback():
    """
    Submit feedback on chatbot response
    
    Request Body:
        {
            "intent": "booking_status",
            "helpful": true,
            "comment": "Very helpful!"
        }
    
    Returns:
        {
            "success": true,
            "message": "Feedback submitted"
        }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return api_error_response('Feedback data is required', 400)
        
        # In production, store feedback in database for ML training
        # For now, just acknowledge receipt
        
        return api_success_response(None, 'Thank you for your feedback!')
        
    except Exception as e:
        return api_error_response(f'Failed to submit feedback: {str(e)}', 500)

