#!/bin/bash

# Deployment script for Hestia Flutter App

set -e

echo "🚀 Deploying Hestia to Firebase..."

# Build Flutter web app
echo "📱 Building Flutter web app..."
cd athena_parent_copilot
flutter build web --release
cd ..

# Activate functions environment
echo "🐍 Preparing Firebase Functions..."
cd functions
source venv/bin/activate
cd ..

# Deploy to Firebase
echo "🔥 Deploying to Firebase..."
firebase deploy

echo "✅ Deployment complete!"
echo "Your app is now live at: https://athena-parent-copilot.web.app"