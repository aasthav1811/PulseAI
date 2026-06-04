#!/bin/bash

# Social Intelligence Platform — Setup Script
# This script automates the installation process

set -e

echo "🚀 Social Intelligence Platform — Setup"
echo "======================================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Found Python $PYTHON_VERSION"
echo ""

# Navigate to backend
echo "📦 Installing backend dependencies..."
cd backend

# Install requirements
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "✅ Backend dependencies installed"
echo ""

# Download NLTK data
echo "📥 Downloading NLTK data (for fallback sentiment)..."
python3 -c "import nltk; nltk.download('vader_lexicon', quiet=True)"
echo "✅ NLTK data downloaded"
echo ""

cd ..

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo ""
echo "1. Start the backend:"
echo "   cd backend"
echo "   python3 main.py"
echo ""
echo "2. In a new terminal, start the frontend:"
echo "   cd frontend"
echo "   python3 -m http.server 3000"
echo ""
echo "3. Open your browser to:"
echo "   http://localhost:3000"
echo ""
echo "📚 See README.md for detailed instructions"
echo ""
