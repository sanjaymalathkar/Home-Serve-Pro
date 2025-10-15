# 🏠 HomeServe Pro - AI-Powered In-House Services Platform

A comprehensive, role-based full-stack web application designed as a secure in-house service platform that connects customers, vendors, and administrators through intelligent workflows and digital satisfaction signatures.

## 🚀 Features

### Core Features
- **Role-Based Access Control (RBAC)**: 5 distinct user roles with separate dashboards
- **AI Chatbot Assistant**: Context-aware conversational AI for all user roles
- **Digital Signature System**: Tamper-proof Smart Signature Vault with SHA-256 hashing
- **Real-Time Communication**: WebSocket-based live updates and notifications
- **AI-Powered Operations**: Pincode clustering, smart scheduling, and vendor allocation
- **Payment Integration**: Dual-mode payouts (auto/manual) with Stripe/Razorpay
- **Immutable Audit Logs**: Complete tracking of all critical operations

### User Roles

#### 1. 👤 Customer Dashboard
- Search and book services based on pincode
- View booking history and status updates
- Approve/reject vendor satisfaction requests with digital e-signature
- Provide ratings and reviews
- Real-time notifications for booking updates

#### 2. 👷 Vendor Dashboard
- Toggle availability (Online/Offline)
- Manage daily job queue with AI-buffered scheduling
- Upload before/after job photos
- Request customer satisfaction signature
- Access earning reports and payout history
- Automated alerts for pending signatures

#### 3. 🧑‍💼 Onboard Manager Dashboard
- Manage vendor onboarding process
- Review uploaded documents and KYC proofs
- AI-flag suspicious entries or duplicate vendors
- Approve/reject vendor profiles
- Limited visibility into booking and payment logs

#### 4. 📊 Ops Manager Dashboard
- Monitor live jobs and booking statuses
- Access AI pincode scaling map showing high-demand clusters
- Oversee manual payment approvals
- Real-time alerts for pending signatures and delayed bookings
- View audit logs

#### 5. 🦸 Super Admin Dashboard
- Central control panel for system management
- Manage all roles and access levels
- View immutable audit trails
- Approve vendor payouts (manual/auto)
- Analytics dashboards: revenue, customer growth, top vendors

## 🛠️ Tech Stack

- **Backend**: Python Flask 3.0
- **Database**: MongoDB Atlas
- **Authentication**: JWT with Flask-JWT-Extended
- **Real-Time**: Flask-SocketIO with eventlet
- **AI/ML**: Scikit-learn, NumPy, TensorFlow
- **Payment**: Stripe API
- **Digital Signature**: DocuSign API
- **Maps**: Google Maps API
- **Image Processing**: Pillow

## 📋 Prerequisites

- Python 3.8+
- MongoDB Atlas account (or local MongoDB)
- Node.js (optional, for frontend development)

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "Home Serve Pro"
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# MongoDB
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/homeservepro

# JWT Secret Keys
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# Stripe (Optional)
STRIPE_SECRET_KEY=sk_test_your_key

# Google Maps (Optional)
GOOGLE_MAPS_API_KEY=your_api_key
```

### 5. Initialize Database

```bash
flask init-db
```

### 6. Seed Sample Data (Optional)

```bash
flask seed-data
```

This creates sample services and test users:
- Customer: `customer@test.com` / `password123`
- Vendor: `vendor@test.com` / `password123`
- Onboard Manager: `onboard@test.com` / `password123`
- Ops Manager: `ops@test.com` / `password123`

### 7. Create Super Admin

```bash
flask create-admin
```

Follow the prompts to create your super admin account.

## 🚀 Running the Application

### Development Mode

```bash
python run.py
```

The application will be available at `http://localhost:5000`

### Production Mode

```bash
export FLASK_ENV=production
gunicorn -k eventlet -w 1 --bind 0.0.0.0:5000 run:app
```

## 📡 API Documentation

### Authentication Endpoints

#### Register User
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe",
  "phone": "1234567890",
  "role": "customer",
  "pincode": "12345"
}
```

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

#### Get Current User
```http
GET /api/auth/me
Authorization: Bearer <access_token>
```

### Customer Endpoints

#### Get Services
```http
GET /api/customer/services?q=plumbing&pincode=12345
Authorization: Bearer <access_token>
```

#### Create Booking
```http
POST /api/customer/bookings
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "service_id": "service_id_here",
  "service_date": "2024-01-15",
  "service_time": "10:00",
  "address": "123 Main St",
  "pincode": "12345",
  "description": "Leaking faucet in kitchen"
}
```

#### Sign Booking
```http
POST /api/customer/bookings/<booking_id>/sign
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "signature_data": "base64_encoded_signature",
  "satisfied": true
}
```

### Vendor Endpoints

#### Toggle Availability
```http
POST /api/vendor/availability
Authorization: Bearer <access_token>
```

#### Get Bookings
```http
GET /api/vendor/bookings?status=pending
Authorization: Bearer <access_token>
```

#### Upload Photos
```http
POST /api/vendor/bookings/<booking_id>/photos
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

photo: <file>
type: before|after
```

#### Request Signature
```http
POST /api/vendor/bookings/<booking_id>/request-signature
Authorization: Bearer <access_token>
```

### Admin Endpoints

See full API documentation in `/docs` folder.

## 🔐 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: Bcrypt with configurable rounds
- **Rate Limiting**: Protection against brute force attacks
- **CORS Protection**: Configurable allowed origins
- **Immutable Audit Logs**: All critical operations logged
- **Digital Signature Verification**: SHA-256 hashing for tamper-proof signatures

## 🤖 AI/ML Features

### AI Chatbot Assistant
- **Role-Aware Responses**: Contextual assistance based on user role
- **Natural Language Processing**: Understands user queries in natural language
- **Intent Classification**: Automatically detects user intent (booking status, payments, etc.)
- **Quick Actions**: Provides role-specific quick action buttons
- **Conversation Context**: Maintains conversation history for better responses
- **Smart Suggestions**: Offers relevant suggestions based on user activity

**Chatbot Capabilities by Role:**
- **Customer**: Book services, check booking status, sign documents, view payments
- **Vendor**: View jobs, check earnings, toggle availability, upload photos
- **Onboard Manager**: Review pending vendors, approve KYC, search vendors
- **Ops Manager**: Monitor live operations, approve payments, view alerts
- **Super Admin**: System analytics, user management, audit logs

### Pincode Pulse Engine
- Clusters pincodes by demand patterns
- Predicts service demand for optimal pricing
- Identifies high-demand areas for vendor allocation

### Smart Buffering Engine
- Predicts travel time between jobs
- Calculates optimal buffer time
- Optimizes vendor schedules using TSP algorithms

### Vendor Allocation Engine
- Scores vendors based on ratings, location, and availability
- Automatically assigns best-matched vendor to bookings
- Considers workload balancing

### Dynamic Pricing
- Adjusts prices based on demand
- Peak hour multipliers
- Location-based pricing

## 📊 Database Schema

### Collections

- **users**: All user accounts (customers, vendors, admins)
- **vendors**: Vendor-specific profiles and KYC data
- **services**: Available services catalog
- **bookings**: Service bookings and job tracking
- **signatures**: Digital signatures with hashes
- **payments**: Payment transactions and payouts
- **audit_logs**: Immutable operation logs
- **notifications**: User notifications

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## 📦 Project Structure

```
Home Serve Pro/
├── app/
│   ├── __init__.py           # App factory
│   ├── models/               # MongoDB models
│   ├── routes/               # API blueprints
│   ├── services/             # Business logic & AI
│   ├── sockets/              # WebSocket handlers
│   └── utils/                # Helpers & middleware
├── uploads/                  # File uploads
├── models/                   # AI/ML models
├── config.py                 # Configuration
├── run.py                    # Application entry point
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🔄 Real-Time Features

The application uses Flask-SocketIO for real-time communication:

- Booking status updates
- Signature requests and completions
- Payment notifications
- Vendor availability changes
- Live dashboard updates

## 🌐 Deployment

### Docker Deployment (Recommended)

```bash
docker build -t homeservepro .
docker run -p 5000:5000 --env-file .env homeservepro
```

### Heroku Deployment

```bash
heroku create homeservepro
heroku addons:create mongolab
git push heroku main
```

## 📝 License

This project is proprietary software. All rights reserved.

## 👥 Contributors

- Development Team

## 📞 Support

For support, email sanjaymalathkarsr33@gmail.com

---

**Built with ❤️ using Flask, MongoDB, and AI**

