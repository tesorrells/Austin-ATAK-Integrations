#!/usr/bin/env python3
"""
Simple test runner for Austin ATAK Integrations.
This script runs the core functionality tests without requiring full app configuration.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def run_core_tests():
    """Run core functionality tests."""
    print("🧪 Austin ATAK Integrations - Core Tests")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Test 1: API Endpoints
    print("\n📡 Testing API Endpoints...")
    try:
        from tests.test_api_endpoints import main as test_api
        await test_api()
        print("✅ API Endpoints: PASSED")
    except Exception as e:
        print(f"❌ API Endpoints: FAILED - {e}")
        return False
    
    # Test 2: CoT Generation
    print("\n📄 Testing CoT Generation...")
    try:
        from tests.test_cot_generation import main as test_cot
        await test_cot()
        print("✅ CoT Generation: PASSED")
    except Exception as e:
        print(f"❌ CoT Generation: FAILED - {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All core tests passed!")
    print("The system is ready for deployment.")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = asyncio.run(run_core_tests())
    sys.exit(0 if success else 1)
