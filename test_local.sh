#!/bin/bash

# Local testing script for Hestia Firebase Functions

set -e

echo "🧪 Testing Hestia Firebase Functions locally..."

# Use the GraphRAG virtual environment for functions
export PYTHONPATH="$PWD/functions:$PYTHONPATH"
cd functions
source venv/bin/activate
cd ..

# Start Firebase emulators
echo "Starting Firebase emulators..."
firebase emulators:start --only functions

# Note: This will start the functions emulator on http://localhost:5001
# You can test your functions at:
# http://localhost:5001/athena-parent-copilot/us-central1/get_chat
# http://localhost:5001/athena-parent-copilot/us-central1/auto_respond_post
# http://localhost:5001/athena-parent-copilot/us-central1/test_function