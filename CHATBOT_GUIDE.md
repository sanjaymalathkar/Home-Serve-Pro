# 🤖 AI Chatbot Assistant - Complete Guide

## Overview

The HomeServe Pro AI Chatbot is a role-aware conversational assistant that provides context-aware help across all user dashboards. It uses natural language processing to understand user queries and provides intelligent responses based on the user's role and current context.

## Features

### 🎯 Core Capabilities

1. **Natural Language Understanding**
   - Understands queries in natural language
   - No need for specific commands or syntax
   - Handles variations in phrasing

2. **Intent Classification**
   - Automatically detects what the user wants
   - 15+ intent types supported
   - Context-aware intent detection

3. **Role-Aware Responses**
   - Customized responses for each user role
   - Role-specific quick actions
   - Relevant suggestions based on permissions

4. **Conversation Context**
   - Maintains conversation history
   - Remembers last 10 interactions
   - Context-aware follow-up responses

5. **Quick Actions**
   - Dynamic action buttons
   - One-click navigation
   - Role-specific shortcuts

## Supported Intents

### General Intents
- **greeting**: Hi, Hello, Hey
- **help**: Help, Assist, Guide me
- **general**: Fallback for unrecognized queries

### Customer Intents
- **booking_status**: Check booking status
- **create_booking**: Book a service
- **payment_info**: View payment information
- **vendor_info**: Get vendor details
- **signature**: Sign documents
- **rating**: Rate and review services

### Vendor Intents
- **earnings**: Check earnings and payouts
- **availability**: Toggle online/offline status
- **booking_status**: View assigned jobs

### Manager Intents
- **onboarding**: Vendor onboarding (Onboard Manager)
- **operations**: Live operations monitoring (Ops Manager)
- **analytics**: System analytics (Super Admin)
- **user_management**: Manage users (Super Admin)
- **service_catalog**: Manage services (Super Admin)

## Usage Examples

### For Customers

```
User: "What's my booking status?"
Bot: Your latest booking:
     Status: ✅ Accepted - Vendor will arrive soon
     Service: Plumbing
     Date: 2024-01-15
     [View Details] [All Bookings]

User: "Book a plumber"
Bot: I can help you book a service! Here are our available services:
     🔧 Plumbing
     ⚡ Electrical
     🧹 Cleaning
     [Plumbing] [Electrical] [Cleaning]

User: "How much did I pay?"
Bot: Latest Payment:
     Amount: ₹500
     Status: Completed
     Date: 2024-01-10
     [View All Payments]
```

### For Vendors

```
User: "Show my pending jobs"
Bot: You have 3 pending jobs:
     1. Plumbing - 123 Main St - 10:00 AM
     2. Electrical - 456 Oak Ave - 2:00 PM
     3. Cleaning - 789 Pine Rd - 4:00 PM
     [Accept Jobs] [View Details]

User: "What are my earnings?"
Bot: 💰 Your Earnings:
     Total Earned: ₹5,000
     Pending Payout: ₹1,200
     Available: ₹3,800
     [Payout History] [Performance Stats]

User: "Go online"
Bot: Your current status: 🔴 Offline
     Would you like to change your availability?
     [Go Online]
```

### For Managers

```
User: "Show pending vendors" (Onboard Manager)
Bot: 👥 Vendor Onboarding:
     Pending Applications: 5
     Review KYC documents and approve/reject vendors.
     [View Pending] [Search Vendors]

User: "Show live jobs" (Ops Manager)
Bot: 🔧 Live Operations:
     Jobs In Progress: 12
     Pending Signatures: 3
     [View Live Jobs] [Pending Signatures]

User: "Show analytics" (Super Admin)
Bot: 📊 Quick Stats:
     Total Users: 1,000
     Total Bookings: 5,000
     Total Vendors: 150
     [Full Analytics] [Revenue Report]
```

## API Endpoints

### 1. Send Message

**Endpoint:** `POST /api/chatbot/message`

**Request:**
```json
{
  "message": "What's my booking status?"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "message": "Your latest booking...",
    "intent": "booking_status",
    "quick_replies": ["View Details", "All Bookings"],
    "action": "show_bookings",
    "data": {
      "booking_id": "507f1f77bcf86cd799439011"
    },
    "timestamp": "2024-01-01T12:00:00"
  }
}
```

### 2. Clear Conversation

**Endpoint:** `POST /api/chatbot/clear`

Clears conversation history and context.

### 3. Get Suggestions

**Endpoint:** `GET /api/chatbot/suggestions`

Returns role-specific suggested questions.

### 4. Get Quick Actions

**Endpoint:** `GET /api/chatbot/quick-actions`

Returns role-specific quick action buttons.

### 5. Get Context

**Endpoint:** `GET /api/chatbot/context`

Returns current conversation context.

### 6. Submit Feedback

**Endpoint:** `POST /api/chatbot/feedback`

Submit feedback on chatbot responses.

## Frontend Integration

### Chatbot Widget

The chatbot widget is automatically included in all pages through the base template. It appears as a floating button in the bottom-right corner.

**Features:**
- Floating chat button
- Expandable chat window
- Real-time message updates
- Typing indicators
- Quick reply buttons
- Auto-scroll to latest message
- Mobile responsive

### Usage

The chatbot widget is automatically initialized. Users can:

1. Click the chat button to open
2. Type a message and press Enter or click Send
3. Click quick reply buttons for common actions
4. Close the chat window anytime

### Customization

To customize the chatbot appearance, edit `app/templates/chatbot_widget.html`:

```css
/* Change primary color */
.chatbot-toggle {
    background: linear-gradient(135deg, #your-color-1 0%, #your-color-2 100%);
}

/* Change chat bubble colors */
.chatbot-message.user .chatbot-message-bubble {
    background: #your-color;
}
```

## Architecture

### Components

1. **IntentClassifier**
   - Pattern-based intent detection
   - Regex matching for keywords
   - Extensible intent patterns

2. **ContextManager**
   - In-memory context storage
   - Conversation history tracking
   - Context cleanup

3. **ResponseGenerator**
   - Role-specific response templates
   - Dynamic data integration
   - Quick reply generation

4. **ChatbotService**
   - Main orchestration layer
   - Coordinates all components
   - API interface

### Data Flow

```
User Message
    ↓
Intent Classification
    ↓
Context Retrieval
    ↓
Response Generation
    ↓
Context Update
    ↓
Response to User
```

## Extending the Chatbot

### Adding New Intents

1. Add intent pattern to `IntentClassifier.INTENT_PATTERNS`:

```python
'new_intent': [
    r'\b(keyword1|keyword2)\b',
    r'\b(phrase pattern)\b',
]
```

2. Add response handler to `ResponseGenerator`:

```python
@staticmethod
def _handle_new_intent(user: Dict, data: Optional[Dict]) -> Dict:
    return {
        'message': "Your response here",
        'quick_replies': ['Action 1', 'Action 2']
    }
```

3. Add case to `generate_response` method:

```python
elif intent == 'new_intent':
    return ResponseGenerator._handle_new_intent(user, data)
```

### Adding Role-Specific Responses

Update the role-specific dictionaries in `ResponseGenerator`:

```python
GREETINGS = {
    'new_role': "Custom greeting for new role",
}

HELP_MESSAGES = {
    'new_role': """
    Custom help message for new role
    """,
}
```

## Best Practices

### For Users

1. **Be Natural**: Ask questions naturally, like talking to a person
2. **Be Specific**: Provide context when asking about specific items
3. **Use Quick Replies**: Click suggested buttons for faster navigation
4. **Clear Context**: Use "start over" if conversation gets confusing

### For Developers

1. **Keep Patterns Simple**: Use clear, unambiguous regex patterns
2. **Test Thoroughly**: Test with various phrasings
3. **Provide Fallbacks**: Always have a default response
4. **Monitor Usage**: Track common queries to improve responses
5. **Update Regularly**: Add new intents based on user feedback

## Performance Considerations

### Current Implementation

- **Context Storage**: In-memory (suitable for development)
- **Pattern Matching**: Regex-based (fast for current scale)
- **Response Time**: < 100ms for most queries

### Production Recommendations

1. **Use Redis for Context**: Store conversation context in Redis
2. **Add Caching**: Cache common responses
3. **Implement ML Models**: Use trained models for better intent classification
4. **Add Analytics**: Track chatbot usage and effectiveness
5. **Rate Limiting**: Prevent abuse with rate limits

## Future Enhancements

### Planned Features

1. **Machine Learning Integration**
   - Train custom NLP models
   - Improve intent classification accuracy
   - Learn from user interactions

2. **Multi-language Support**
   - Support multiple languages
   - Auto-detect user language
   - Translate responses

3. **Voice Integration**
   - Voice input support
   - Text-to-speech responses
   - Voice commands

4. **Advanced Context**
   - Multi-turn conversations
   - Entity extraction
   - Slot filling

5. **Proactive Assistance**
   - Suggest actions based on user behavior
   - Send proactive notifications
   - Predictive assistance

## Troubleshooting

### Common Issues

**Issue: Chatbot not responding**
- Check if user is authenticated
- Verify JWT token is valid
- Check browser console for errors

**Issue: Wrong responses**
- Clear conversation context
- Check intent patterns
- Verify user role

**Issue: Widget not appearing**
- Ensure base template includes chatbot_widget.html
- Check if JavaScript is enabled
- Verify Font Awesome is loaded

## Support

For issues or questions about the chatbot:

1. Check this documentation
2. Review API documentation
3. Check application logs
4. Contact development team

---

**The AI Chatbot makes HomeServe Pro more accessible and user-friendly for all roles!** 🤖✨

