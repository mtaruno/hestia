#!/usr/bin/env python3
"""Quick local test of Firebase functions before deployment"""

import sys
import os
sys.path.append('functions')

from functions.ai_query.kg_query import run_query
from functions.get_auto_response.get_auto_response import getAutoResponse

def test_chat_function():
    """Test the chat function locally"""
    print("Testing chat function...")
    try:
        response = run_query("How do I handle toddler tantrums?")
        print(f"✅ Chat function works. Response length: {len(response)}")
        return True
    except Exception as e:
        print(f"❌ Chat function failed: {e}")
        return False

def test_auto_response_function():
    """Test the auto response function locally"""
    print("Testing auto response function...")
    try:
        response = getAutoResponse("Help with bedtime", "My 3-year-old won't go to sleep")
        print(f"✅ Auto response works. Response length: {len(response)}")
        return True
    except Exception as e:
        print(f"❌ Auto response failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Firebase functions locally...\n")
    
    chat_ok = test_chat_function()
    print()
    auto_ok = test_auto_response_function()
    
    print(f"\n📊 Results:")
    print(f"Chat function: {'✅' if chat_ok else '❌'}")
    print(f"Auto response: {'✅' if auto_ok else '❌'}")
    
    if chat_ok and auto_ok:
        print("\n🚀 Ready for deployment!")
    else:
        print("\n⚠️  Fix issues before deploying")