# HomeServe Pro - System Architecture

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  Web Browser  │  Mobile App  │  Admin Dashboard  │  API Clients │
└────────┬────────────────┬────────────────┬──────────────────────┘
         │                │                │
         └────────────────┴────────────────┘
                          │
                    HTTP/WebSocket
                          │
┌─────────────────────────▼─────────────────────────────────────┐
│                    APPLICATION LAYER                           │
├────────────────────────────────────────────────────────────────┤
│                     Flask Application                          │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              API Gateway (Flask Routes)                   │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  Auth │ Customer │ Vendor │ Managers │ Admin │ Common   │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Middleware Layer                             │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  JWT Auth │ RBAC │ Rate Limit │ CORS │ Error Handler   │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Business Logic Layer                         │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  AI Services │ Payment │ Signature │ Notification       │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Data Access Layer (Models)                   │ │
│  ├──────────────────────────────────────────────────────────┤ │
│  │  User │ Vendor │ Booking │ Service │ Payment │ Audit   │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────────────────────┬───────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌────────────────┐ ┌──────────┐ ┌──────────────┐
│   MongoDB      │ │  Redis   │ │ File Storage │
│   Database     │ │  Cache   │ │   (S3/Local) │
└────────────────┘ └──────────┘ └──────────────┘
```

## 📦 Component Architecture

### 1. Application Layer

```
app/
├── __init__.py              # Application Factory
│   ├── Flask App
│   ├── Extensions (JWT, SocketIO, Bcrypt, etc.)
│   └── Blueprint Registration
│
├── routes/                  # API Endpoints (Controllers)
│   ├── auth.py             # Authentication endpoints
│   ├── customer.py         # Customer operations
│   ├── vendor.py           # Vendor operations
│   ├── onboard_manager.py  # Vendor onboarding
│   ├── ops_manager.py      # Operations management
│   ├── super_admin.py      # System administration
│   └── common.py           # Shared endpoints
│
├── models/                  # Data Models (ORM)
│   ├── user.py             # User authentication
│   ├── vendor.py           # Vendor profiles
│   ├── booking.py          # Service bookings
│   ├── service.py          # Service catalog
│   ├── signature.py        # Digital signatures
│   ├── payment.py          # Payments & payouts
│   ├── audit_log.py        # Audit trails
│   └── notification.py     # User notifications
│
├── services/                # Business Logic
│   └── ai_service.py       # AI/ML engines
│       ├── PincodePulseEngine
│       ├── SmartBufferingEngine
│       ├── VendorAllocationEngine
│       └── PricingOptimizationEngine
│
├── utils/                   # Utilities & Helpers
│   ├── decorators.py       # RBAC decorators
│   ├── error_handlers.py   # Error responses
│   ├── jwt_handlers.py     # JWT callbacks
│   └── file_upload.py      # File handling
│
├── sockets/                 # WebSocket Handlers
│   └── events.py           # Real-time events
│
└── templates/               # HTML Templates
    ├── base.html           # Base template
    └── index.html          # Landing page
```

## 🔄 Request Flow

### Standard API Request Flow

```
1. Client Request
   │
   ▼
2. Flask Route Handler
   │
   ▼
3. Middleware (JWT, RBAC, Rate Limit)
   │
   ▼
4. Route Function (Controller)
   │
   ▼
5. Business Logic (Services)
   │
   ▼
6. Data Access (Models)
   │
   ▼
7. MongoDB Query
   │
   ▼
8. Response Formatting
   │
   ▼
9. Client Response
```

### WebSocket Event Flow

```
1. Client Connects
   │
   ▼
2. Socket.IO Handler
   │
   ▼
3. Authentication
   │
   ▼
4. Join User Room
   │
   ▼
5. Listen for Events
   │
   ▼
6. Emit to Specific Rooms
   │
   ▼
7. Client Receives Update
```

## 🗄️ Database Schema

### Collections & Relationships

```
┌─────────────┐
│    Users    │
│─────────────│
│ _id (PK)    │◄─────┐
│ email       │      │
│ password    │      │
│ role        │      │
│ name        │      │
└─────────────┘      │
                     │
┌─────────────┐      │
│   Vendors   │      │
│─────────────│      │
│ _id (PK)    │      │
│ user_id (FK)├──────┘
│ services    │
│ ratings     │
│ earnings    │
└──────┬──────┘
       │
       │
┌──────▼──────┐      ┌─────────────┐
│  Bookings   │      │  Services   │
│─────────────│      │─────────────│
│ _id (PK)    │      │ _id (PK)    │
│ customer_id ├──────┤ name        │
│ vendor_id   │      │ category    │
│ service_id  ├──────┤ base_price  │
│ status      │      └─────────────┘
│ amount      │
└──────┬──────┘
       │
       │
┌──────▼──────┐      ┌─────────────┐
│ Signatures  │      │  Payments   │
│─────────────│      │─────────────│
│ _id (PK)    │      │ _id (PK)    │
│ booking_id  ├──────┤ booking_id  │
│ hash        │      │ amount      │
│ verified    │      │ status      │
└─────────────┘      └─────────────┘

┌─────────────┐      ┌──────────────┐
│ AuditLogs   │      │Notifications │
│─────────────│      │──────────────│
│ _id (PK)    │      │ _id (PK)     │
│ action      │      │ user_id      │
│ entity_type │      │ type         │
│ user_id     │      │ message      │
│ timestamp   │      │ read         │
└─────────────┘      └──────────────┘
```

## 🔐 Security Architecture

### Authentication Flow

```
1. User Login
   │
   ▼
2. Verify Credentials (Bcrypt)
   │
   ▼
3. Generate JWT Tokens
   ├── Access Token (1 hour)
   └── Refresh Token (30 days)
   │
   ▼
4. Return Tokens to Client
   │
   ▼
5. Client Stores Tokens
   │
   ▼
6. Subsequent Requests
   │
   ▼
7. Verify JWT Token
   │
   ▼
8. Check User Role (RBAC)
   │
   ▼
9. Allow/Deny Access
```

### Authorization Layers

```
┌─────────────────────────────────────┐
│         Request Received            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    Layer 1: JWT Verification        │
│    - Token valid?                   │
│    - Token expired?                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    Layer 2: User Lookup             │
│    - User exists?                   │
│    - Account active?                │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    Layer 3: Role Check (RBAC)       │
│    - Has required role?             │
│    - Permission granted?            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    Layer 4: Rate Limiting           │
│    - Within rate limit?             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         Process Request             │
└─────────────────────────────────────┘
```

## 🤖 AI/ML Architecture

### AI Services Pipeline

```
┌─────────────────────────────────────────────┐
│           Booking Request                   │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│    Pincode Pulse Engine                     │
│    - Analyze demand                         │
│    - Cluster pincodes                       │
│    - Predict demand score                   │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│    Vendor Allocation Engine                 │
│    - Score available vendors                │
│    - Consider: rating, location, workload   │
│    - Select best match                      │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│    Dynamic Pricing Engine                   │
│    - Calculate demand multiplier            │
│    - Apply peak hour factor                 │
│    - Return final price                     │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│    Smart Buffering Engine                   │
│    - Predict travel time                    │
│    - Calculate buffer                       │
│    - Optimize schedule                      │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│         Create Booking                      │
└─────────────────────────────────────────────┘
```

## 🔄 Real-Time Communication

### WebSocket Architecture

```
┌──────────────┐
│   Client 1   │
└──────┬───────┘
       │
       │ WebSocket
       │
┌──────▼───────────────────────────────┐
│      Flask-SocketIO Server           │
│  ┌────────────────────────────────┐  │
│  │     Connection Manager         │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │     Room Management            │  │
│  │  - User Rooms                  │  │
│  │  - Role Rooms                  │  │
│  │  - Booking Rooms               │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │     Event Handlers             │  │
│  │  - authenticate                │  │
│  │  - booking_update              │  │
│  │  - notification                │  │
│  └────────────────────────────────┘  │
└──────┬───────────────────────────────┘
       │
       │ Emit to Rooms
       │
┌──────▼───────┐  ┌──────────┐
│   Client 2   │  │ Client 3 │
└──────────────┘  └──────────┘
```

## 📊 Data Flow Diagrams

### Booking Creation Flow

```
Customer → Search Services
    ↓
Select Service
    ↓
AI: Find Best Vendor ──→ Vendor Allocation Engine
    ↓                         ↓
Create Booking ←──────── Score & Select
    ↓
Save to MongoDB
    ↓
Create Notification
    ↓
Emit WebSocket Event ──→ Vendor Receives Alert
    ↓
Log to Audit Trail
    ↓
Return Booking ID
```

### Digital Signature Flow

```
Vendor Completes Job
    ↓
Upload Photos
    ↓
Request Signature
    ↓
Create Notification ──→ Customer Receives Alert
    ↓
Customer Reviews
    ↓
Customer Signs
    ↓
Generate SHA-256 Hash
    ↓
Store in Signature Vault
    ↓
Update Booking Status
    ↓
Trigger Payment Release
    ↓
Update Vendor Earnings
    ↓
Log All Actions
```

## 🚀 Deployment Architecture

### Production Deployment

```
┌─────────────────────────────────────────────┐
│              Load Balancer                  │
│              (Nginx/AWS ELB)                │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│  App Server │ │  App Server │
│   (Flask)   │ │   (Flask)   │
└──────┬──────┘ └──────┬──────┘
       │               │
       └───────┬───────┘
               │
       ┌───────┴───────┬───────────┐
       │               │           │
       ▼               ▼           ▼
┌─────────────┐ ┌──────────┐ ┌─────────┐
│  MongoDB    │ │  Redis   │ │   S3    │
│   Atlas     │ │  Cache   │ │ Storage │
└─────────────┘ └──────────┘ └─────────┘
```

## 🔧 Technology Stack

### Backend Stack
```
┌─────────────────────────────────────┐
│         Python 3.8+                 │
├─────────────────────────────────────┤
│  Flask 3.0 (Web Framework)          │
│  Flask-PyMongo (MongoDB)            │
│  Flask-JWT-Extended (Auth)          │
│  Flask-SocketIO (Real-time)         │
│  Flask-Bcrypt (Password Hashing)    │
│  Flask-CORS (CORS)                  │
│  Flask-Limiter (Rate Limiting)      │
├─────────────────────────────────────┤
│  Scikit-learn (ML)                  │
│  NumPy (Numerical Computing)        │
│  TensorFlow (Deep Learning)         │
├─────────────────────────────────────┤
│  Pillow (Image Processing)          │
│  Stripe (Payments)                  │
│  DocuSign (Signatures)              │
│  Google Maps (Location)             │
└─────────────────────────────────────┘
```

## 📈 Scalability Considerations

### Horizontal Scaling
- Stateless API design
- JWT tokens (no server-side sessions)
- MongoDB sharding support
- Redis for distributed caching
- Load balancer ready

### Vertical Scaling
- Efficient database queries
- Proper indexing
- Connection pooling
- Caching strategies

### Performance Optimization
- Database indexing
- Query optimization
- Image compression
- CDN for static files
- Lazy loading

---

**This architecture supports:**
- ✅ High availability
- ✅ Horizontal scaling
- ✅ Real-time communication
- ✅ Security best practices
- ✅ Microservices migration path
- ✅ Cloud deployment ready

