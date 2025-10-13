"""
AI Chatbot Service - Role-Aware Conversational Assistant
Provides context-aware assistance across all user roles
"""

import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from bson import ObjectId

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from app.models.user import User
from app.models.booking import Booking
from app.models.vendor import Vendor
from app.models.service import Service
from app.models.payment import Payment
from app.models.notification import Notification


class IntentClassifier:
    """
    Classifies user intents from natural language queries
    Uses pattern matching and keyword analysis
    """
    
    # Intent patterns for different user queries
    INTENT_PATTERNS = {
        'greeting': [
            r'\b(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b',
        ],
        'help': [
            r'\b(help|assist|support|guide|how to|how do i)\b',
        ],
        'booking_status': [
            r'\b(status|where is|track|booking|order|job)\b.*\b(status|progress|update)\b',
            r'\b(my booking|my order|my job)\b',
        ],
        'create_booking': [
            r'\b(book|schedule|arrange|need|want)\b.*\b(service|plumber|electrician|cleaner)\b',
            r'\b(how to book|create booking|make appointment)\b',
        ],
        'payment_info': [
            r'\b(payment|pay|cost|price|charge|fee|bill)\b',
            r'\b(how much|what is the cost)\b',
        ],
        'vendor_info': [
            r'\b(vendor|service provider|technician|worker)\b',
            r'\b(who is|assigned|coming)\b',
        ],
        'earnings': [
            r'\b(earnings|income|revenue|payout|money earned)\b',
        ],
        'availability': [
            r'\b(available|availability|online|offline|status)\b',
        ],
        'signature': [
            r'\b(sign|signature|approve|confirm|verify)\b',
        ],
        'rating': [
            r'\b(rate|rating|review|feedback|stars)\b',
        ],
        'analytics': [
            r'\b(analytics|statistics|stats|metrics|dashboard|report)\b',
        ],
        'user_management': [
            r'\b(users|accounts|manage users|activate|deactivate)\b',
        ],
        'service_catalog': [
            r'\b(services|catalog|add service|categories)\b',
        ],
        'onboarding': [
            r'\b(onboard|approve vendor|kyc|verification|pending vendors)\b',
        ],
        'operations': [
            r'\b(operations|live jobs|monitoring|alerts)\b',
        ],
    }
    
    @staticmethod
    def classify_intent(message: str) -> str:
        """
        Classify the intent of a user message
        
        Args:
            message: User's message text
            
        Returns:
            Intent classification string
        """
        message_lower = message.lower()
        
        # Check each intent pattern
        for intent, patterns in IntentClassifier.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent
        
        return 'general'


class ContextManager:
    """
    Manages conversation context for each user
    Stores recent interactions and user state
    """
    
    # In-memory context storage (use Redis in production)
    _contexts: Dict[str, Dict] = {}
    
    @classmethod
    def get_context(cls, user_id: str) -> Dict:
        """Get conversation context for a user"""
        if user_id not in cls._contexts:
            cls._contexts[user_id] = {
                'history': [],
                'last_intent': None,
                'last_entity': None,
                'created_at': datetime.utcnow()
            }
        return cls._contexts[user_id]
    
    @classmethod
    def update_context(cls, user_id: str, intent: str, entity: Optional[str] = None):
        """Update conversation context"""
        context = cls.get_context(user_id)
        context['last_intent'] = intent
        context['last_entity'] = entity
        context['history'].append({
            'intent': intent,
            'entity': entity,
            'timestamp': datetime.utcnow()
        })
        
        # Keep only last 10 interactions
        if len(context['history']) > 10:
            context['history'] = context['history'][-10:]
    
    @classmethod
    def clear_context(cls, user_id: str):
        """Clear conversation context"""
        if user_id in cls._contexts:
            del cls._contexts[user_id]


class ResponseGenerator:
    """
    Generates contextual responses based on user role and intent
    """
    
    # Role-specific greeting messages
    GREETINGS = {
        'customer': "Hi! I'm your HomeServe assistant. I can help you book services, track bookings, or answer questions. What can I do for you?",
        'vendor': "Hello! I can help you manage your jobs, check earnings, or update your availability. How can I assist?",
        'onboard_manager': "Hi! I can help you review pending vendors, approve KYC documents, or search vendors. What do you need?",
        'ops_manager': "Hello! I can show you live operations, pending signatures, or payment approvals. What would you like to see?",
        'super_admin': "Hi Admin! I can provide analytics, manage users, or help with system operations. What can I help with?",
    }
    
    # Role-specific help messages
    HELP_MESSAGES = {
        'customer': """
I can help you with:
• 📅 Book a service (plumbing, electrical, cleaning, etc.)
• 📊 Check booking status
• ✍️ Sign satisfaction documents
• ⭐ Rate and review services
• 💰 View payment information
• 🔔 Check notifications

Just ask me naturally, like "Book a plumber" or "What's my booking status?"
        """,
        'vendor': """
I can help you with:
• 🟢 Toggle availability (online/offline)
• 📋 View pending jobs
• ✅ Accept or reject bookings
• 📸 Upload job photos
• ✍️ Request customer signatures
• 💰 Check earnings and payouts
• 📊 View performance stats

Try asking "Show my pending jobs" or "What are my earnings?"
        """,
        'onboard_manager': """
I can help you with:
• 👥 View pending vendor applications
• ✅ Approve or reject vendors
• 📄 Review KYC documents
• 🔍 Search vendors
• 📊 View onboarding statistics

Ask me things like "Show pending vendors" or "Approve vendor"
        """,
        'ops_manager': """
I can help you with:
• 📊 View live operations dashboard
• ⏳ Check pending signatures
• 💰 Approve payments
• 🚨 View operational alerts
• 📈 Monitor booking trends
• 📝 Access audit logs

Try "Show live jobs" or "Pending signatures"
        """,
        'super_admin': """
I can help you with:
• 📊 System analytics and metrics
• 👥 User management
• 🛠️ Service catalog management
• 💰 Payout approvals
• 📝 Audit log viewing
• 🔧 System configuration

Ask me "Show analytics" or "Manage users"
        """,
    }
    
    @staticmethod
    def generate_response(user: Dict, intent: str, context: Dict, data: Optional[Dict] = None) -> Dict:
        """
        Generate a contextual response
        
        Args:
            user: User document
            intent: Classified intent
            context: Conversation context
            data: Additional data for response
            
        Returns:
            Response dictionary with message and actions
        """
        role = user.get('role', 'customer')
        
        if intent == 'greeting':
            return {
                'message': ResponseGenerator.GREETINGS.get(role, "Hello! How can I help you?"),
                'quick_replies': ResponseGenerator._get_quick_replies(role)
            }
        
        elif intent == 'help':
            return {
                'message': ResponseGenerator.HELP_MESSAGES.get(role, "I'm here to help!"),
                'quick_replies': ResponseGenerator._get_quick_replies(role)
            }
        
        elif intent == 'booking_status':
            return ResponseGenerator._handle_booking_status(user, data)
        
        elif intent == 'create_booking':
            return ResponseGenerator._handle_create_booking(user, data)
        
        elif intent == 'payment_info':
            return ResponseGenerator._handle_payment_info(user, data)
        
        elif intent == 'vendor_info':
            return ResponseGenerator._handle_vendor_info(user, data)
        
        elif intent == 'earnings':
            return ResponseGenerator._handle_earnings(user, data)
        
        elif intent == 'availability':
            return ResponseGenerator._handle_availability(user, data)
        
        elif intent == 'signature':
            return ResponseGenerator._handle_signature(user, data)
        
        elif intent == 'rating':
            return ResponseGenerator._handle_rating(user, data)
        
        elif intent == 'analytics':
            return ResponseGenerator._handle_analytics(user, data)
        
        elif intent == 'user_management':
            return ResponseGenerator._handle_user_management(user, data)
        
        elif intent == 'service_catalog':
            return ResponseGenerator._handle_service_catalog(user, data)
        
        elif intent == 'onboarding':
            return ResponseGenerator._handle_onboarding(user, data)
        
        elif intent == 'operations':
            return ResponseGenerator._handle_operations(user, data)
        
        else:
            return {
                'message': "I'm not sure I understand. Could you rephrase that? Type 'help' to see what I can do.",
                'quick_replies': ['Help', 'Start over']
            }
    
    @staticmethod
    def _get_quick_replies(role: str) -> List[str]:
        """Get quick reply suggestions based on role"""
        quick_replies = {
            'customer': ['Book Service', 'My Bookings', 'Help'],
            'vendor': ['My Jobs', 'Earnings', 'Toggle Availability'],
            'onboard_manager': ['Pending Vendors', 'Search Vendors', 'Stats'],
            'ops_manager': ['Live Jobs', 'Pending Signatures', 'Alerts'],
            'super_admin': ['Analytics', 'Manage Users', 'Services'],
        }
        return quick_replies.get(role, ['Help'])
    
    @staticmethod
    def _handle_booking_status(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle booking status queries"""
        from app import mongo
        
        user_id = str(user['_id'])
        bookings = list(mongo.db.bookings.find({
            'customer_id': user_id
        }).sort('created_at', -1).limit(5))
        
        if not bookings:
            return {
                'message': "You don't have any bookings yet. Would you like to book a service?",
                'quick_replies': ['Book Service', 'View Services']
            }
        
        latest = bookings[0]
        status_messages = {
            'pending': '⏳ Pending - Waiting for vendor acceptance',
            'accepted': '✅ Accepted - Vendor will arrive soon',
            'in_progress': '🔧 In Progress - Service is being performed',
            'completed': '✔️ Completed - Waiting for your signature',
            'verified': '🎉 Verified - Service completed successfully',
            'cancelled': '❌ Cancelled',
            'rejected': '❌ Rejected by vendor'
        }
        
        status = latest.get('status', 'pending')
        message = f"Your latest booking:\n\n"
        message += f"Status: {status_messages.get(status, status)}\n"
        message += f"Service: {latest.get('service_name', 'N/A')}\n"
        message += f"Date: {latest.get('scheduled_date', 'N/A')}\n"
        
        if status == 'completed':
            message += "\n✍️ Please sign the satisfaction document to release payment."
        
        return {
            'message': message,
            'data': {'booking_id': str(latest['_id'])},
            'quick_replies': ['View Details', 'All Bookings']
        }
    
    @staticmethod
    def _handle_create_booking(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle booking creation queries"""
        return {
            'message': "I can help you book a service! Here are our available services:\n\n"
                      "🔧 Plumbing\n"
                      "⚡ Electrical\n"
                      "🧹 Cleaning\n"
                      "🎨 Painting\n"
                      "❄️ AC Repair\n"
                      "🪛 Carpentry\n\n"
                      "Which service do you need?",
            'quick_replies': ['Plumbing', 'Electrical', 'Cleaning', 'Other'],
            'action': 'show_services'
        }
    
    @staticmethod
    def _handle_payment_info(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle payment information queries"""
        from app import mongo
        
        user_id = str(user['_id'])
        payments = list(mongo.db.payments.find({
            'customer_id': user_id
        }).sort('created_at', -1).limit(1))
        
        if not payments:
            return {
                'message': "You don't have any payment history yet.",
                'quick_replies': ['Book Service']
            }
        
        latest = payments[0]
        return {
            'message': f"Latest Payment:\n\n"
                      f"Amount: ₹{latest.get('amount', 0)}\n"
                      f"Status: {latest.get('status', 'N/A')}\n"
                      f"Date: {latest.get('created_at', 'N/A')}",
            'quick_replies': ['View All Payments']
        }
    
    @staticmethod
    def _handle_vendor_info(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle vendor information queries"""
        return {
            'message': "I can show you information about your assigned vendor. "
                      "Please provide your booking ID or check your latest booking.",
            'quick_replies': ['My Bookings']
        }
    
    @staticmethod
    def _handle_earnings(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle vendor earnings queries"""
        from app import mongo
        
        vendor = mongo.db.vendors.find_one({'user_id': str(user['_id'])})
        
        if not vendor:
            return {'message': "Vendor profile not found."}
        
        total_earnings = vendor.get('total_earnings', 0)
        pending_payout = vendor.get('pending_payout', 0)
        
        return {
            'message': f"💰 Your Earnings:\n\n"
                      f"Total Earned: ₹{total_earnings}\n"
                      f"Pending Payout: ₹{pending_payout}\n"
                      f"Available: ₹{total_earnings - pending_payout}",
            'quick_replies': ['Payout History', 'Performance Stats']
        }
    
    @staticmethod
    def _handle_availability(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle vendor availability queries"""
        from app import mongo
        
        vendor = mongo.db.vendors.find_one({'user_id': str(user['_id'])})
        
        if not vendor:
            return {'message': "Vendor profile not found."}
        
        is_available = vendor.get('is_available', False)
        status = "🟢 Online" if is_available else "🔴 Offline"
        
        return {
            'message': f"Your current status: {status}\n\n"
                      f"Would you like to change your availability?",
            'quick_replies': ['Go Online' if not is_available else 'Go Offline']
        }
    
    @staticmethod
    def _handle_signature(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle signature-related queries"""
        from app import mongo
        
        user_id = str(user['_id'])
        pending_signatures = mongo.db.bookings.count_documents({
            'customer_id': user_id,
            'status': 'completed',
            'signature_id': None
        })
        
        if pending_signatures == 0:
            return {
                'message': "You don't have any pending signatures.",
                'quick_replies': ['My Bookings']
            }
        
        return {
            'message': f"You have {pending_signatures} booking(s) waiting for your signature.\n\n"
                      f"Please review and sign to release payment to the vendor.",
            'quick_replies': ['View Pending Signatures'],
            'action': 'show_pending_signatures'
        }
    
    @staticmethod
    def _handle_rating(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle rating and review queries"""
        return {
            'message': "You can rate services after they're completed and signed.\n\n"
                      "Ratings help us maintain quality and help other customers choose the best vendors.",
            'quick_replies': ['My Bookings']
        }
    
    @staticmethod
    def _handle_analytics(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle analytics queries for admin"""
        from app import mongo
        
        total_users = mongo.db.users.count_documents({})
        total_bookings = mongo.db.bookings.count_documents({})
        total_vendors = mongo.db.vendors.count_documents({})
        
        return {
            'message': f"📊 Quick Stats:\n\n"
                      f"Total Users: {total_users}\n"
                      f"Total Bookings: {total_bookings}\n"
                      f"Total Vendors: {total_vendors}",
            'quick_replies': ['Full Analytics', 'Revenue Report'],
            'action': 'show_analytics'
        }
    
    @staticmethod
    def _handle_user_management(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle user management queries"""
        return {
            'message': "I can help you manage users:\n\n"
                      "• View all users\n"
                      "• Activate/deactivate accounts\n"
                      "• Search users\n"
                      "• View user details",
            'quick_replies': ['View Users', 'Search User'],
            'action': 'show_user_management'
        }
    
    @staticmethod
    def _handle_service_catalog(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle service catalog queries"""
        from app import mongo
        
        service_count = mongo.db.services.count_documents({'is_active': True})
        
        return {
            'message': f"📋 Service Catalog:\n\n"
                      f"Active Services: {service_count}\n\n"
                      f"You can add, edit, or deactivate services.",
            'quick_replies': ['View Services', 'Add Service'],
            'action': 'show_services'
        }
    
    @staticmethod
    def _handle_onboarding(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle vendor onboarding queries"""
        from app import mongo
        
        pending_count = mongo.db.vendors.count_documents({'onboarding_status': 'pending'})
        
        return {
            'message': f"👥 Vendor Onboarding:\n\n"
                      f"Pending Applications: {pending_count}\n\n"
                      f"Review KYC documents and approve/reject vendors.",
            'quick_replies': ['View Pending', 'Search Vendors'],
            'action': 'show_pending_vendors'
        }
    
    @staticmethod
    def _handle_operations(user: Dict, data: Optional[Dict]) -> Dict:
        """Handle operations monitoring queries"""
        from app import mongo
        
        live_jobs = mongo.db.bookings.count_documents({'status': 'in_progress'})
        pending_signatures = mongo.db.bookings.count_documents({
            'status': 'completed',
            'signature_id': None
        })
        
        return {
            'message': f"🔧 Live Operations:\n\n"
                      f"Jobs In Progress: {live_jobs}\n"
                      f"Pending Signatures: {pending_signatures}",
            'quick_replies': ['View Live Jobs', 'Pending Signatures'],
            'action': 'show_operations'
        }


class ChatbotService:
    """
    Main chatbot service that orchestrates intent classification,
    context management, and response generation
    """
    
    @staticmethod
    def process_message(user_id: str, message: str) -> Dict:
        """
        Process a user message and generate a response
        
        Args:
            user_id: User ID
            message: User's message text
            
        Returns:
            Response dictionary
        """
        from app import mongo
        
        # Get user
        user = User.find_by_id(user_id)
        if not user:
            return {'error': 'User not found'}
        
        # Classify intent
        intent = IntentClassifier.classify_intent(message)
        
        # Get conversation context
        context = ContextManager.get_context(user_id)
        
        # Generate response
        response = ResponseGenerator.generate_response(user, intent, context)
        
        # Update context
        ContextManager.update_context(user_id, intent)
        
        # Add metadata
        response['intent'] = intent
        response['timestamp'] = datetime.utcnow().isoformat()
        
        return response
    
    @staticmethod
    def clear_conversation(user_id: str):
        """Clear conversation history for a user"""
        ContextManager.clear_context(user_id)


class GoogleAIChatbot:
    """
    Enhanced chatbot using Google's Generative AI
    Falls back to pattern-based responses if API is unavailable
    """

    def __init__(self):
        """Initialize Google AI chatbot"""
        self.model = None
        self.api_key = os.getenv('GOOGLE_API_KEY')

        if GENAI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                print("✅ Google AI Chatbot initialized successfully")
            except Exception as e:
                print(f"⚠️ Failed to initialize Google AI: {e}")
                self.model = None
        else:
            print("⚠️ Google AI not available, using pattern-based responses")

    def generate_response(self, message: str, user_role: str, context: Dict = None) -> str:
        """
        Generate AI response using Google's Generative AI

        Args:
            message: User's message
            user_role: User's role (customer, vendor, admin, etc.)
            context: Additional context (bookings, services, etc.)

        Returns:
            AI-generated response
        """
        if not self.model:
            # Fallback to pattern-based response
            return self._fallback_response(message, user_role)

        try:
            # Build context-aware prompt
            prompt = self._build_prompt(message, user_role, context)

            # Generate response
            response = self.model.generate_content(prompt)

            if response and response.text:
                return response.text
            else:
                return self._fallback_response(message, user_role)

        except Exception as e:
            print(f"Error generating AI response: {e}")
            return self._fallback_response(message, user_role)

    def _build_prompt(self, message: str, user_role: str, context: Dict = None) -> str:
        """Build context-aware prompt for AI"""

        # System context
        system_context = f"""You are a helpful AI assistant for HomeServe Pro, a home services platform.
You are currently assisting a {user_role}.

Platform Information:
- HomeServe Pro connects customers with service providers for home services
- Services include: Plumbing, Electrical, Painting, Cleaning, Carpentry, AC Repair
- Users can book services, track bookings, make payments, and communicate with vendors

Your role:
- Provide helpful, accurate, and friendly responses
- Be concise but informative
- Use emojis sparingly for a friendly tone
- If you don't know something, admit it and suggest contacting support
- Always maintain a professional yet approachable tone
"""

        # Role-specific context
        role_context = ""
        if user_role == 'customer':
            role_context = """
As a customer assistant:
- Help with booking services
- Explain booking status and tracking
- Provide information about payments
- Answer questions about services and pricing
- Guide through the platform features
"""
        elif user_role == 'vendor':
            role_context = """
As a vendor assistant:
- Help manage job assignments
- Explain how to accept/reject jobs
- Provide guidance on completing jobs
- Answer questions about earnings and payments
- Assist with profile management
"""
        elif user_role in ['super_admin', 'ops_manager', 'onboard_manager']:
            role_context = """
As an admin assistant:
- Help with platform management
- Provide insights on users and vendors
- Assist with booking oversight
- Answer questions about system operations
- Guide through admin features
"""

        # Add context data if available
        data_context = ""
        if context:
            if 'bookings' in context:
                data_context += f"\nUser has {len(context['bookings'])} bookings."
            if 'services' in context:
                data_context += f"\nAvailable services: {len(context['services'])}."

        # Build final prompt
        full_prompt = f"""{system_context}

{role_context}

{data_context}

User's question: {message}

Provide a helpful response (keep it under 150 words):"""

        return full_prompt

    def _fallback_response(self, message: str, user_role: str) -> str:
        """Fallback response when AI is unavailable"""

        message_lower = message.lower()

        # Greeting
        if any(word in message_lower for word in ['hi', 'hello', 'hey']):
            return f"👋 Hello! I'm your HomeServe Pro assistant. How can I help you today?"

        # Help
        if any(word in message_lower for word in ['help', 'assist', 'support']):
            if user_role == 'customer':
                return "I can help you with:\n• Booking services\n• Tracking your bookings\n• Payment information\n• Service details\n\nWhat would you like to know?"
            elif user_role == 'vendor':
                return "I can help you with:\n• Managing your jobs\n• Accepting/rejecting bookings\n• Tracking earnings\n• Profile settings\n\nWhat do you need help with?"
            else:
                return "I can help you with:\n• Platform management\n• User oversight\n• Booking management\n• System operations\n\nHow can I assist you?"

        # Booking
        if 'book' in message_lower or 'service' in message_lower:
            if user_role == 'customer':
                return "To book a service:\n1. Click 'Book Service' in your dashboard\n2. Choose the service you need\n3. Fill in the booking details\n4. Confirm your booking\n\nWould you like to book a service now?"
            else:
                return "Customers can book services through their dashboard. They can choose from various services like plumbing, electrical, painting, and more."

        # Default
        return "I'm here to help! Could you please provide more details about what you need assistance with? You can ask me about bookings, services, payments, or any other platform features."


# Initialize global AI chatbot instance
ai_chatbot = GoogleAIChatbot()
