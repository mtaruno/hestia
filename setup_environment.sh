#!/bin/bash

# Hestia Flutter App Deployment Environment Setup
# This script sets up the complete environment for deploying the Flutter app with Firebase Functions

set -e  # Exit on any error

echo "🚀 Setting up Hestia deployment environment..."

# Check if we're in the right directory
if [ ! -f "firebase.json" ]; then
    echo "❌ Error: firebase.json not found. Please run this script from the project root."
    exit 1
fi

# 1. Install Flutter dependencies
echo "📱 Installing Flutter dependencies..."
cd athena_parent_copilot
flutter pub get
cd ..

# 2. Set up Python virtual environment for Firebase Functions
echo "🐍 Setting up Python environment for Firebase Functions..."
cd functions

# Remove existing venv if it exists
if [ -d "venv" ]; then
    echo "Removing existing venv..."
    rm -rf venv
fi

# Create new virtual environment using the hestia-graphrag venv as base
cp -r ../hestia-graphrag venv

# Activate the new venv and install function-specific dependencies
source venv/bin/activate
pip install -r requirements.txt

echo "✅ Firebase Functions Python environment ready"
cd ..

# 3. Activate the GraphRAG virtual environment and install dependencies
echo "🧠 Setting up GraphRAG environment..."
cd hestia-graphrag
source bin/activate

# Install any additional dependencies if needed
pip install --upgrade pip

echo "✅ GraphRAG environment ready"
cd ..

# 4. Install Firebase CLI if not already installed
echo "🔥 Checking Firebase CLI..."
if ! command -v firebase &> /dev/null; then
    echo "Installing Firebase CLI..."
    npm install -g firebase-tools
else
    echo "Firebase CLI already installed"
fi

# 5. Login to Firebase (if not already logged in)
echo "🔐 Checking Firebase authentication..."
if ! firebase projects:list &> /dev/null; then
    echo "Please login to Firebase:"
    firebase login
fi

# 6. Set up environment variables
echo "⚙️  Setting up environment variables..."
if [ ! -f "config.env" ]; then
    echo "Creating config.env template..."
    cat > config.env << EOF
# Firebase Configuration
FIREBASE_PROJECT_ID=athena-parent-copilot

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Neo4j Configuration (if using)
NEO4J_URI=your_neo4j_uri_here
NEO4J_USERNAME=your_neo4j_username_here
NEO4J_PASSWORD=your_neo4j_password_here

# Other API keys and configurations
EOF
    echo "⚠️  Please update config.env with your actual API keys and configuration"
fi

# 7. Build Flutter app for web (optional, for Firebase Hosting)
echo "🌐 Building Flutter web app..."
cd athena_parent_copilot
flutter build web
cd ..

echo ""
echo "🎉 Environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Update config.env with your API keys"
echo "2. Test locally: ./test_local.sh"
echo "3. Deploy: firebase deploy"
echo ""
echo "Available commands:"
echo "- Deploy functions only: firebase deploy --only functions"
echo "- Deploy hosting only: firebase deploy --only hosting"
echo "- Test functions locally: firebase emulators:start"