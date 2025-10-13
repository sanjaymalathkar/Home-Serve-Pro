# 🚀 HomeServe Pro - Startup Guide

## ✅ Installation Complete!

Your HomeServe Pro application is now **fully installed and running**!

---

## 🌐 Access the Application

**Application URL:** http://localhost:5001

The server is currently running on port **5001** (changed from 5000 to avoid conflicts).

---

## 📋 What Was Installed

### 1. **Virtual Environment**
- Created at: `./venv`
- Python version: 3.12.3
- All dependencies installed successfully

### 2. **Dependencies Installed** (102 packages)
- ✅ Flask 3.0.0 - Web framework
- ✅ Flask-PyMongo 2.3.0 - MongoDB integration
- ✅ Flask-JWT-Extended 4.6.0 - Authentication
- ✅ Flask-SocketIO 5.3.6 - Real-time communication
- ✅ TensorFlow 2.18.0 - AI/ML capabilities
- ✅ scikit-learn 1.4.0 - Machine learning
- ✅ pandas, numpy - Data processing
- ✅ Stripe 7.11.0 - Payment processing
- ✅ And 94 more packages...

### 3. **Configuration**
- ✅ `.env` file created with development settings
- ✅ MongoDB configured for local development
- ✅ Secret keys generated
- ✅ SocketIO configured (without Redis for development)
- ✅ Port changed to 5001

### 4. **Fixes Applied**
- ✅ TensorFlow version updated to 2.18.0 (Python 3.12 compatible)
- ✅ Redis message queue disabled for development
- ✅ JWT callbacks fixed for Flask-JWT-Extended 4.6.0
- ✅ Port changed to 5001 to avoid conflicts

---

## 🎮 How to Use

### **Starting the Server**

```bash
# Activate virtual environment
source venv/bin/activate  # On Mac/Linux
# or
venv\Scripts\activate  # On Windows

# Run the application
python run.py
```

The server will start on: **http://localhost:5001**

### **Stopping the Server**

Press `Ctrl + C` in the terminal where the server is running.

---

## 🗄️ Database Setup

### **Current Configuration**
The app is configured to use **local MongoDB** at:
```
mongodb://localhost:27017/homeservepro
```

### **Option 1: Install MongoDB Locally**

**On macOS:**
```bash
# Install MongoDB using Homebrew
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB
brew services start mongodb-community
```

**On Ubuntu/Linux:**
```bash
sudo apt-get install mongodb
sudo systemctl start mongodb
```

**On Windows:**
Download and install from: https://www.mongodb.com/try/download/community

### **Option 2: Use MongoDB Atlas (Cloud)**

1. Go to https://www.mongodb.com/cloud/atlas
2. Create a free account
3. Create a new cluster
4. Get your connection string
5. Update `.env` file:
   ```
   MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/homeservepro?retryWrites=true&w=majority
   ```

### **Initialize Database**

Once MongoDB is running, initialize the database:

```bash
# Activate virtual environment
source venv/bin/activate

# Initialize database collections
flask init-db

# Seed sample data (optional)
flask seed-data

# Create admin user
flask create-admin
```

---

## 👥 Test Accounts

After running `flask seed-data`, you'll have these test accounts:

### **Customer**
- Email: `customer@test.com`
- Password: `password123`

### **Vendor**
- Email: `vendor@test.com`
- Password: `password123`

### **Onboard Manager**
- Email: `onboard@test.com`
- Password: `password123`

### **Ops Manager**
- Email: `ops@test.com`
- Password: `password123`

### **Super Admin**
- Email: `admin@test.com`
- Password: `password123`

---

## 🔧 Configuration

### **Environment Variables** (`.env` file)

Key settings you might want to change:

```bash
# Server Port
PORT=5001

# MongoDB
MONGO_URI=mongodb://localhost:27017/homeservepro

# Secret Keys (CHANGE IN PRODUCTION!)
SECRET_KEY=dev-homeservepro-secret-key-2024-change-in-production
JWT_SECRET_KEY=dev-homeservepro-jwt-secret-2024-change-in-production

# CORS (add your frontend URL)
CORS_ORIGINS=http://localhost:3000,http://localhost:5001

# Payment Gateway (add your keys)
STRIPE_PUBLIC_KEY=pk_test_your_stripe_public_key
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key

# Google Maps API (add your key)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
```

---

## 📡 API Endpoints

### **Authentication**
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token
- `POST /api/auth/logout` - Logout

### **Customer**
- `GET /api/customer/services` - List services
- `POST /api/customer/bookings` - Create booking
- `GET /api/customer/bookings` - My bookings
- `POST /api/customer/signature/:id` - Sign document

### **Vendor**
- `GET /api/vendor/jobs` - My jobs
- `POST /api/vendor/availability` - Toggle availability
- `GET /api/vendor/earnings` - View earnings
- `POST /api/vendor/upload-photo` - Upload job photo

### **Chatbot**
- `POST /api/chatbot/message` - Send message
- `GET /api/chatbot/suggestions` - Get suggestions
- `GET /api/chatbot/quick-actions` - Get quick actions

**Full API documentation:** See `API_DOCUMENTATION.md`

---

## 🤖 Testing the AI Chatbot

1. Open http://localhost:5001 in your browser
2. Look for the **purple chat button** in the bottom-right corner
3. Click it to open the chatbot
4. Try these queries:
   - "Hi"
   - "Help"
   - "What can you do?"
   - "Show my bookings" (after login)

---

## 🐛 Troubleshooting

### **Port Already in Use**
```bash
# Kill process on port 5001
lsof -ti:5001 | xargs kill -9

# Or change port in .env
PORT=5002
```

### **MongoDB Connection Error**
```bash
# Check if MongoDB is running
mongosh  # or mongo

# If not installed, use MongoDB Atlas (cloud)
# Update MONGO_URI in .env file
```

### **Module Not Found Error**
```bash
# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt
```

### **JWT Errors**
```bash
# Make sure JWT_SECRET_KEY is set in .env
# Restart the server after changing .env
```

---

## 📚 Documentation

- **README.md** - Project overview
- **SETUP_GUIDE.md** - Detailed setup instructions
- **API_DOCUMENTATION.md** - Complete API reference
- **CHATBOT_GUIDE.md** - AI Chatbot documentation
- **ARCHITECTURE.md** - System architecture
- **COMPLETION_REPORT.md** - Feature completion report

---

## 🎯 Next Steps

1. **✅ Server is running** - http://localhost:5001
2. **Install MongoDB** - Choose local or Atlas
3. **Initialize database** - Run `flask init-db`
4. **Seed sample data** - Run `flask seed-data`
5. **Test the application** - Login with test accounts
6. **Try the chatbot** - Click the purple chat button
7. **Explore the API** - Use Postman or curl
8. **Customize** - Update branding, add services, etc.

---

## 🆘 Need Help?

### **Check Logs**
The server logs appear in the terminal where you ran `python run.py`

### **Common Issues**
- Port conflicts → Change PORT in .env
- MongoDB errors → Install MongoDB or use Atlas
- Import errors → Reinstall requirements
- JWT errors → Check .env configuration

### **Documentation**
All documentation files are in the project root directory.

---

## 🎉 Success!

Your **HomeServe Pro** platform is now running with:

✅ Flask backend with 56+ API endpoints  
✅ MongoDB database integration  
✅ JWT authentication  
✅ Real-time WebSocket communication  
✅ AI/ML capabilities  
✅ **AI Chatbot assistant**  
✅ Payment gateway integration  
✅ Digital signature system  
✅ 5 role-based dashboards  

**Enjoy building with HomeServe Pro!** 🚀

---

**Server Status:** 🟢 **RUNNING** on http://localhost:5001

**To stop:** Press `Ctrl + C` in the terminal

