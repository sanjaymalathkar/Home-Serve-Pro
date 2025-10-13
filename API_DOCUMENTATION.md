# HomeServe Pro API Documentation

## Base URL
```
http://localhost:5000/api
```

## Authentication

All authenticated endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## Authentication Endpoints

### Register User
Create a new user account.

**Endpoint:** `POST /auth/register`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe",
  "phone": "1234567890",
  "role": "customer",
  "pincode": "12345",
  "address": "123 Main St"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Registration successful",
  "data": {
    "user_id": "user_id_here",
    "access_token": "jwt_token",
    "refresh_token": "refresh_token",
    "role": "customer"
  }
}
```

### Login
Authenticate user and receive tokens.

**Endpoint:** `POST /auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "jwt_token",
    "refresh_token": "refresh_token",
    "user": {
      "id": "user_id",
      "email": "user@example.com",
      "name": "John Doe",
      "role": "customer"
    }
  }
}
```

### Refresh Token
Get new access token using refresh token.

**Endpoint:** `POST /auth/refresh`

**Headers:**
```
Authorization: Bearer <refresh_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "new_jwt_token"
  }
}
```

---

## Customer Endpoints

### Get Services
Retrieve available services with optional search.

**Endpoint:** `GET /customer/services`

**Query Parameters:**
- `q` (optional): Search query
- `pincode` (optional): Filter by pincode

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "service_id",
      "name": "Plumbing - Leak Repair",
      "description": "Fix leaking pipes and faucets",
      "category": "plumbing",
      "base_price": 50.0,
      "duration_minutes": 60
    }
  ]
}
```

### Create Booking
Book a service.

**Endpoint:** `POST /customer/bookings`

**Request Body:**
```json
{
  "service_id": "service_id_here",
  "service_date": "2024-01-15",
  "service_time": "10:00",
  "address": "123 Main St",
  "pincode": "12345",
  "description": "Leaking kitchen faucet"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Booking created successfully",
  "data": {
    "booking_id": "booking_id",
    "vendor_name": "Mike Vendor"
  }
}
```

### Get Bookings
Retrieve customer's bookings.

**Endpoint:** `GET /customer/bookings`

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20)

**Response:**
```json
{
  "success": true,
  "data": {
    "bookings": [...],
    "total": 10,
    "page": 1,
    "pages": 1
  }
}
```

### Sign Booking
Provide digital signature for completed service.

**Endpoint:** `POST /customer/bookings/<booking_id>/sign`

**Request Body:**
```json
{
  "signature_data": "base64_encoded_signature_image",
  "satisfied": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Signature recorded successfully",
  "data": {
    "signature_id": "signature_id",
    "signature_hash": "sha256_hash"
  }
}
```

### Rate Booking
Rate and review a completed booking.

**Endpoint:** `POST /customer/bookings/<booking_id>/rate`

**Request Body:**
```json
{
  "rating": 5,
  "review": "Excellent service!"
}
```

---

## Vendor Endpoints

### Get Profile
Retrieve vendor profile.

**Endpoint:** `GET /vendor/profile`

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "vendor_id",
    "name": "Mike Vendor",
    "services": ["Plumbing", "Electrical"],
    "availability": true,
    "ratings": 4.8,
    "completed_jobs": 150
  }
}
```

### Toggle Availability
Change vendor availability status.

**Endpoint:** `POST /vendor/availability`

**Response:**
```json
{
  "success": true,
  "message": "Availability updated successfully",
  "data": {
    "availability": true
  }
}
```

### Get Bookings
Retrieve vendor's bookings.

**Endpoint:** `GET /vendor/bookings`

**Query Parameters:**
- `status` (optional): Filter by status
- `page` (optional): Page number
- `limit` (optional): Items per page

### Accept Booking
Accept a booking request.

**Endpoint:** `POST /vendor/bookings/<booking_id>/accept`

### Reject Booking
Reject a booking request.

**Endpoint:** `POST /vendor/bookings/<booking_id>/reject`

### Upload Photos
Upload before/after photos.

**Endpoint:** `POST /vendor/bookings/<booking_id>/photos`

**Form Data:**
- `photo`: Image file
- `type`: "before" or "after"

### Request Signature
Request customer signature.

**Endpoint:** `POST /vendor/bookings/<booking_id>/request-signature`

### Get Earnings
Retrieve earnings summary.

**Endpoint:** `GET /vendor/earnings`

**Response:**
```json
{
  "success": true,
  "data": {
    "total_earnings": 5000.0,
    "completed_jobs": 150,
    "rating": 4.8,
    "total_ratings": 120
  }
}
```

---

## Onboard Manager Endpoints

### Get Pending Vendors
Retrieve vendors pending approval.

**Endpoint:** `GET /onboard-manager/vendors/pending`

### Approve Vendor
Approve vendor onboarding.

**Endpoint:** `POST /onboard-manager/vendors/<vendor_id>/approve`

**Request Body:**
```json
{
  "notes": "All documents verified"
}
```

### Reject Vendor
Reject vendor onboarding.

**Endpoint:** `POST /onboard-manager/vendors/<vendor_id>/reject`

**Request Body:**
```json
{
  "reason": "Incomplete KYC documents"
}
```

---

## Ops Manager Endpoints

### Get Live Bookings
Monitor active bookings.

**Endpoint:** `GET /ops-manager/bookings/live`

### Get Pending Signatures
View bookings with pending signatures.

**Endpoint:** `GET /ops-manager/bookings/pending-signatures`

**Query Parameters:**
- `days` (optional): Days threshold (default: 2)

### Approve Payment
Manually approve a payment.

**Endpoint:** `POST /ops-manager/payments/<payment_id>/approve`

### Get Dashboard Stats
Retrieve operational statistics.

**Endpoint:** `GET /ops-manager/dashboard/stats`

### Get Alerts
Retrieve operational alerts.

**Endpoint:** `GET /ops-manager/alerts`

---

## Super Admin Endpoints

### Get Analytics
Comprehensive system analytics.

**Endpoint:** `GET /super-admin/dashboard/analytics`

**Query Parameters:**
- `days` (optional): Time period in days (default: 30)

**Response:**
```json
{
  "success": true,
  "data": {
    "users": {
      "total": 1000,
      "new": 50,
      "customers": 800,
      "vendors": 150
    },
    "bookings": {
      "total": 5000,
      "completed": 4500,
      "pending": 100
    },
    "revenue": {
      "total": 250000.0,
      "period_days": 30
    }
  }
}
```

### Get All Users
Retrieve all users with filters.

**Endpoint:** `GET /super-admin/users`

**Query Parameters:**
- `role` (optional): Filter by role
- `active` (optional): Filter by active status
- `page`, `limit`: Pagination

### Toggle User Active Status
Activate/deactivate user account.

**Endpoint:** `POST /super-admin/users/<user_id>/toggle-active`

### Create Service
Add new service to catalog.

**Endpoint:** `POST /super-admin/services`

**Request Body:**
```json
{
  "name": "AC Repair",
  "description": "Air conditioner repair service",
  "category": "appliance_repair",
  "base_price": 80.0,
  "duration_minutes": 90
}
```

### Approve Payout
Approve vendor payout.

**Endpoint:** `POST /super-admin/payouts/<payment_id>/approve`

---

## Chatbot Endpoints

### Send Message to Chatbot

**Endpoint:** `POST /chatbot/message`

**Description:** Send a message to the AI chatbot and receive a contextual response

**Authentication:** Required (JWT)

**Request Body:**
```json
{
  "message": "What's my booking status?"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Message processed successfully",
  "data": {
    "message": "Your latest booking:\n\nStatus: ✅ Accepted\nService: Plumbing\nDate: 2024-01-15",
    "intent": "booking_status",
    "quick_replies": ["View Details", "All Bookings"],
    "action": "show_bookings",
    "timestamp": "2024-01-01T12:00:00"
  }
}
```

### Clear Conversation History

**Endpoint:** `POST /chatbot/clear`

**Description:** Clear the conversation context and history

**Authentication:** Required (JWT)

### Get Suggested Questions

**Endpoint:** `GET /chatbot/suggestions`

**Description:** Get role-specific suggested questions

**Authentication:** Required (JWT)

**Response:**
```json
{
  "success": true,
  "data": {
    "suggestions": [
      "What's my booking status?",
      "Book a plumbing service",
      "Show my payment history"
    ]
  }
}
```

### Get Quick Actions

**Endpoint:** `GET /chatbot/quick-actions`

**Description:** Get role-specific quick action buttons

**Authentication:** Required (JWT)

**Response:**
```json
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
```

---

## Common Endpoints

### Get Profile
Get current user profile.

**Endpoint:** `GET /profile`

### Update Profile
Update user profile.

**Endpoint:** `PUT /profile`

### Upload Profile Photo
Upload profile picture.

**Endpoint:** `POST /profile/photo`

**Form Data:**
- `photo`: Image file

### Get Notifications
Retrieve user notifications.

**Endpoint:** `GET /notifications`

**Query Parameters:**
- `unread` (optional): true/false
- `page`, `limit`: Pagination

### Mark Notification Read
Mark notification as read.

**Endpoint:** `POST /notifications/<notification_id>/read`

---

## WebSocket Events

### Connect
```javascript
const socket = io('http://localhost:5000');
```

### Authenticate
```javascript
socket.emit('authenticate', { token: 'jwt_token' });
```

### Listen for Events
```javascript
// New booking notification
socket.on('new_booking', (data) => {
  console.log('New booking:', data);
});

// Booking status changed
socket.on('booking_status_changed', (data) => {
  console.log('Status changed:', data);
});

// Signature request
socket.on('signature_request', (data) => {
  console.log('Signature requested:', data);
});

// New notification
socket.on('new_notification', (data) => {
  console.log('Notification:', data);
});
```

---

## Error Responses

All error responses follow this format:

```json
{
  "success": false,
  "error": "Error message here"
}
```

### Common HTTP Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `500`: Internal Server Error

---

## Rate Limiting

Default rate limits:
- 200 requests per day
- 50 requests per hour
- Authentication endpoints: 10 per minute

Exceeded rate limit response:
```json
{
  "error": "Rate limit exceeded"
}
```

