"""Run all tests for Austin ATAK Integrations."""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import test modules
from test_api_endpoints import main as test_api_endpoints
from test_cot_generation import main as test_cot_generation
from test_feed_pollers import main as test_feed_pollers


async def run_all_tests():
    """Run all test suites."""
    print("🚀 Austin ATAK Integrations - Complete Test Suite")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    test_results = []
    
    # Test 1: API Endpoints
    print("\n📡 TEST 1: API Endpoints")
    print("-" * 40)
    try:
        await test_api_endpoints()
        test_results.append(("API Endpoints", "✅ PASSED"))
    except Exception as e:
        print(f"❌ API Endpoints test failed: {e}")
        test_results.append(("API Endpoints", f"❌ FAILED: {e}"))
    
    # Test 2: CoT Generation
    print("\n📄 TEST 2: CoT Generation")
    print("-" * 40)
    try:
        await test_cot_generation()
        test_results.append(("CoT Generation", "✅ PASSED"))
    except Exception as e:
        print(f"❌ CoT Generation test failed: {e}")
        test_results.append(("CoT Generation", f"❌ FAILED: {e}"))
    
    # Test 3: Feed Pollers
    print("\n🔄 TEST 3: Feed Pollers")
    print("-" * 40)
    try:
        await test_feed_pollers()
        test_results.append(("Feed Pollers", "✅ PASSED"))
    except Exception as e:
        print(f"❌ Feed Pollers test failed: {e}")
        test_results.append(("Feed Pollers", f"❌ FAILED: {e}"))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results:
        print(f"{result} {test_name}")
        if "✅ PASSED" in result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 70)
    print(f"Total Tests: {len(test_results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(test_results)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed! The system is ready for deployment.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the errors above.")
    
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
