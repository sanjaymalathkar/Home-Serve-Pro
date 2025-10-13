#!/bin/bash

# HomeServe Pro - Quick Start Script
# This script automates the initial setup process

echo "🏠 HomeServe Pro - Quick Start Setup"
echo "===================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file with your MongoDB URI and secret keys"
    echo "   Minimum required:"
    echo "   - MONGO_URI (get from MongoDB Atlas)"
    echo "   - SECRET_KEY (generate random string)"
    echo "   - JWT_SECRET_KEY (generate random string)"
    echo ""
    read -p "Press Enter after you've configured .env file..."
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads models logs

# Initialize database
echo "🗄️  Initializing database..."
flask init-db

# Ask if user wants to seed data
echo ""
read -p "Do you want to seed sample data? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🌱 Seeding sample data..."
    flask seed-data
    echo ""
    echo "✅ Sample accounts created:"
    echo "   Customer: customer@test.com / password123"
    echo "   Vendor: vendor@test.com / password123"
    echo "   Onboard Manager: onboard@test.com / password123"
    echo "   Ops Manager: ops@test.com / password123"
fi

# Ask if user wants to create admin
echo ""
read -p "Do you want to create a super admin account? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "👤 Creating super admin..."
    flask create-admin
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To start the application, run:"
echo "   python run.py"
echo ""
echo "📚 Documentation:"
echo "   - README.md - Overview and features"
echo "   - SETUP_GUIDE.md - Detailed setup instructions"
echo "   - API_DOCUMENTATION.md - Complete API reference"
echo ""
echo "🌐 The application will be available at:"
echo "   http://localhost:5000"
echo ""
echo "Happy coding! 🎉"

