#!/bin/bash

echo "🧪 Testing Firebase deployment process..."

# 1. Test local functions first
echo "Step 1: Testing functions locally..."
cd /Users/matthewtaruno/dev/parenting-copilot
python3 test_local.py

if [ $? -ne 0 ]; then
    echo "❌ Local tests failed. Fix before deploying."
    exit 1
fi

# 2. Deploy to Firebase
echo -e "\nStep 2: Deploying to Firebase..."
firebase deploy --only functions

if [ $? -ne 0 ]; then
    echo "❌ Deployment failed"
    exit 1
fi

# 3. Test deployed functions
echo -e "\nStep 3: Testing deployed functions..."

# Test the test_function endpoint
echo "Testing test_function..."
firebase functions:shell --only test_function

echo -e "\n✅ Deployment test complete!"
echo "Next: Test from your Flutter app"