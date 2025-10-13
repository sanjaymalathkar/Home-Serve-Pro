# HomeServe Pro - Complete Setup Guide

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] Python 3.8 or higher installed
- [ ] MongoDB Atlas account (free tier works) OR local MongoDB
- [ ] Git installed
- [ ] Text editor (VS Code recommended)
- [ ] Terminal/Command Prompt access

## 🚀 Quick Start (5 Minutes)

### Step 1: Clone and Setup

```bash
# Navigate to your project directory
cd "Home Serve Pro"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your settings
# Minimum required: MONGO_URI, SECRET_KEY, JWT_SECRET_KEY
```

**Quick MongoDB Setup (MongoDB Atlas):**
1. Go to https://www.mongodb.com/cloud/atlas
2. Create free account
3. Create a cluster (free M0 tier)
4. Click "Connect" → "Connect your application"
5. Copy connection string
6. Replace `<password>` with your database password
7. Paste into `.env` as `MONGO_URI`

### Step 3: Initialize Database

```bash
# Create indexes
flask init-db

# Seed sample data (optional but recommended)
flask seed-data

# Create your admin account
flask create-admin
```

### Step 4: Run the Application

```bash
python run.py
```

Visit: http://localhost:5000

## 🎯 Testing the Application

### Sample Accounts (if you ran `flask seed-data`)

| Role | Email | Password |
|------|-------|----------|
| Customer | customer@test.com | password123 |
| Vendor | vendor@test.com | password123 |
| Onboard Manager | onboard@test.com | password123 |
| Ops Manager | ops@test.com | password123 |

### Test Workflow

1. **Login as Customer** (customer@test.com)
   - Browse services
   - Create a booking
   - View booking status

2. **Login as Vendor** (vendor@test.com)
   - Toggle availability to Online
   - View pending bookings
   - Accept a booking
   - Upload before photos
   - Mark as in progress
   - Upload after photos
   - Complete the booking
   - Request signature

3. **Login as Customer Again**
   - View completed booking
   - Sign satisfaction document
   - Rate the service

4. **Login as Ops Manager** (ops@test.com)
   - View live bookings
   - Check dashboard stats
   - View audit logs

5. **Login as Super Admin** (your created admin)
   - View analytics
   - Manage users
   - Create new services
   - View system-wide audit logs

## 🔧 Configuration Details

### Essential Environment Variables

```env
# Flask
SECRET_KEY=generate-a-random-secret-key-here
FLASK_ENV=development

# MongoDB
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/homeservepro
MONGO_DBNAME=homeservepro

# JWT
JWT_SECRET_KEY=generate-another-random-secret-key
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000
```

### Optional Integrations

#### Stripe Payment (Optional)
```env
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
```

#### Google Maps (Optional)
```env
GOOGLE_MAPS_API_KEY=your_api_key
```

#### DocuSign (Optional)
```env
DOCUSIGN_INTEGRATION_KEY=your_key
DOCUSIGN_USER_ID=your_user_id
DOCUSIGN_ACCOUNT_ID=your_account_id
```

## 📱 API Testing

### Using cURL

```bash
# Register a user
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "name": "Test User",
    "phone": "1234567890",
    "role": "customer",
    "pincode": "12345"
  }'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'

# Get services (with token)
curl -X GET http://localhost:5000/api/customer/services \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Using Postman

1. Import the API collection (see API_DOCUMENTATION.md)
2. Set environment variable `base_url` to `http://localhost:5000/api`
3. Login to get access token
4. Set `access_token` environment variable
5. Test endpoints

## 🐳 Docker Deployment

### Using Docker Compose

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Using Docker Only

```bash
# Build image
docker build -t homeservepro .

# Run container
docker run -p 5000:5000 \
  -e MONGO_URI="your_mongo_uri" \
  -e SECRET_KEY="your_secret" \
  -e JWT_SECRET_KEY="your_jwt_secret" \
  homeservepro
```

## 🔍 Troubleshooting

### Common Issues

#### 1. MongoDB Connection Error
```
Error: MongoServerError: Authentication failed
```
**Solution:** Check your MongoDB URI, username, and password in `.env`

#### 2. Module Not Found
```
ModuleNotFoundError: No module named 'flask'
```
**Solution:** Ensure virtual environment is activated and dependencies are installed:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

#### 3. Port Already in Use
```
OSError: [Errno 48] Address already in use
```
**Solution:** Change port in `run.py` or kill process using port 5000:
```bash
# On macOS/Linux
lsof -ti:5000 | xargs kill -9

# On Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

#### 4. JWT Token Errors
```
Error: Token has expired
```
**Solution:** Login again to get a new token. Tokens expire after 1 hour by default.

#### 5. File Upload Errors
```
Error: Failed to save photo
```
**Solution:** Ensure `uploads` directory exists and has write permissions:
```bash
mkdir -p uploads
chmod 755 uploads
```

## 📊 Database Management

### View Collections

```bash
# Using MongoDB Compass (GUI)
# Download from: https://www.mongodb.com/products/compass
# Connect using your MONGO_URI

# Using MongoDB Shell
mongosh "your_mongo_uri"
use homeservepro
show collections
db.users.find().pretty()
```

### Backup Database

```bash
# Export all data
mongodump --uri="your_mongo_uri" --out=./backup

# Restore data
mongorestore --uri="your_mongo_uri" ./backup
```

### Reset Database

```bash
# Drop all collections (WARNING: Deletes all data)
mongosh "your_mongo_uri" --eval "db.dropDatabase()"

# Reinitialize
flask init-db
flask seed-data
```

## 🧪 Running Tests

```bash
# Install test dependencies
pip install pytest pytest-flask pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_auth.py
```

## 🚀 Production Deployment

### Heroku

```bash
# Login to Heroku
heroku login

# Create app
heroku create homeservepro

# Add MongoDB addon
heroku addons:create mongolab

# Set environment variables
heroku config:set SECRET_KEY="your_secret"
heroku config:set JWT_SECRET_KEY="your_jwt_secret"

# Deploy
git push heroku main

# Initialize database
heroku run flask init-db
heroku run flask create-admin
```

### AWS/DigitalOcean

1. Set up Ubuntu server
2. Install Python, Nginx, and dependencies
3. Clone repository
4. Set up virtual environment
5. Configure Nginx as reverse proxy
6. Use Gunicorn with systemd service
7. Set up SSL with Let's Encrypt

See detailed deployment guide in `DEPLOYMENT.md`

## 📚 Additional Resources

- **API Documentation**: See `API_DOCUMENTATION.md`
- **Architecture Overview**: See `ARCHITECTURE.md`
- **Contributing Guide**: See `CONTRIBUTING.md`
- **Security Best Practices**: See `SECURITY.md`

## 🆘 Getting Help

- Check the troubleshooting section above
- Review API documentation
- Check application logs: `logs/app.log`
- Open an issue on GitHub
- Contact support: support@homeservepro.com

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] Application starts without errors
- [ ] Can access http://localhost:5000
- [ ] Can register a new user
- [ ] Can login successfully
- [ ] Can view services
- [ ] Can create a booking (as customer)
- [ ] Can accept booking (as vendor)
- [ ] Real-time notifications work
- [ ] File uploads work
- [ ] Database indexes created

## 🎉 Next Steps

1. Customize the application for your needs
2. Add your branding and styling
3. Configure payment gateway
4. Set up email notifications
5. Deploy to production
6. Monitor and maintain

---

**Congratulations! Your HomeServe Pro platform is ready to use! 🚀**

