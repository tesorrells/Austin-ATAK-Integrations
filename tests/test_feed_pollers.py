"""Test fire and traffic feed pollers with real data."""

import asyncio
import json
import sys
import os
from datetime import datetime, timezone, timedelta

# Add the app directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.feeds.fire import FireFeedPoller
from app.feeds.traffic import TrafficFeedPoller
from app.store.seen import SeenStore


async def test_fire_feed_poller():
    """Test the fire feed poller with real data."""
    print("🔥 Testing Fire Feed Poller...")
    
    # Create a test store
    test_store = SeenStore(":memory:")  # In-memory SQLite for testing
    await test_store.connect()
    
    # Create fire feed poller
    fire_poller = FireFeedPoller()
    
    try:
        # Start the poller (this will create HTTP client)
        await fire_poller.start()
        
        # Test a single poll
        print("  📡 Performing test poll...")
        await fire_poller._poll_incidents()
        
        # Get stats
        stats = await fire_poller.get_stats()
        print(f"  📊 Fire Feed Stats: {stats}")
        
        # Stop the poller
        await fire_poller.stop()
        
        print("  ✅ Fire feed poller test completed successfully")
        
    except Exception as e:
        print(f"  ❌ Fire feed poller test failed: {e}")
        await fire_poller.stop()
    finally:
        await test_store.disconnect()


async def test_traffic_feed_poller():
    """Test the traffic feed poller with real data."""
    print("\n🚗 Testing Traffic Feed Poller...")
    
    # Create a test store
    test_store = SeenStore(":memory:")  # In-memory SQLite for testing
    await test_store.connect()
    
    # Create traffic feed poller
    traffic_poller = TrafficFeedPoller()
    
    try:
        # Start the poller (this will create HTTP client)
        await traffic_poller.start()
        
        # Test a single poll
        print("  📡 Performing test poll...")
        await traffic_poller._poll_incidents()
        
        # Get stats
        stats = await traffic_poller.get_stats()
        print(f"  📊 Traffic Feed Stats: {stats}")
        
        # Stop the poller
        await traffic_poller.stop()
        
        print("  ✅ Traffic feed poller test completed successfully")
        
    except Exception as e:
        print(f"  ❌ Traffic feed poller test failed: {e}")
        await traffic_poller.stop()
    finally:
        await test_store.disconnect()


async def test_incident_validation():
    """Test incident validation logic."""
    print("\n🔍 Testing Incident Validation...")
    
    # Test fire incident validation
    fire_poller = FireFeedPoller()
    
    # Valid fire incident
    valid_fire_incident = {
        "traffic_report_id": "test_fire_123",
        "latitude": "30.2714",
        "longitude": "-97.7420",
        "issue_reported": "STRUCTURE FIRE",
        "address": "123 Test St",
        "traffic_report_status": "ACTIVE"
    }
    
    is_valid = fire_poller._validate_incident(valid_fire_incident)
    print(f"  ✅ Valid fire incident: {is_valid}")
    
    # Invalid fire incident (missing coordinates)
    invalid_fire_incident = {
        "traffic_report_id": "test_fire_456",
        "issue_reported": "STRUCTURE FIRE",
        "address": "123 Test St"
    }
    
    is_valid = fire_poller._validate_incident(invalid_fire_incident)
    print(f"  ❌ Invalid fire incident (no coords): {is_valid}")
    
    # Test traffic incident validation
    traffic_poller = TrafficFeedPoller()
    
    # Valid traffic incident
    valid_traffic_incident = {
        "traffic_report_id": "test_traffic_123",
        "latitude": "30.2714",
        "longitude": "-97.7420",
        "issue_reported": "CRASH",
        "address": "456 Test Ave",
        "traffic_report_status": "ACTIVE"
    }
    
    is_valid = traffic_poller._validate_incident(valid_traffic_incident)
    print(f"  ✅ Valid traffic incident: {is_valid}")
    
    # Invalid traffic incident (missing ID)
    invalid_traffic_incident = {
        "latitude": "30.2714",
        "longitude": "-97.7420",
        "issue_reported": "CRASH",
        "address": "456 Test Ave"
    }
    
    is_valid = traffic_poller._validate_incident(invalid_traffic_incident)
    print(f"  ❌ Invalid traffic incident (no ID): {is_valid}")


async def test_deduplication():
    """Test deduplication logic."""
    print("\n🔄 Testing Deduplication Logic...")
    
    # Create a test store
    test_store = SeenStore(":memory:")
    await test_store.connect()
    
    try:
        # Test incident data
        test_incident = {
            "traffic_report_id": "test_dedup_123",
            "latitude": "30.2714",
            "longitude": "-97.7420",
            "issue_reported": "TEST INCIDENT",
            "address": "789 Test Blvd"
        }
        
        # First time - should not be seen
        is_seen = await test_store.is_incident_seen("fire", test_incident)
        print(f"  🔍 First check (should be False): {is_seen}")
        
        # Mark as seen
        incident_id = await test_store.mark_incident_seen("fire", test_incident, cot_sent=True)
        print(f"  ✅ Marked incident as seen: {incident_id}")
        
        # Second time - should be seen
        is_seen = await test_store.is_incident_seen("fire", test_incident)
        print(f"  🔍 Second check (should be True): {is_seen}")
        
        # Test with different incident
        different_incident = {
            "traffic_report_id": "test_dedup_456",
            "latitude": "30.2714",
            "longitude": "-97.7420",
            "issue_reported": "DIFFERENT INCIDENT",
            "address": "789 Test Blvd"
        }
        
        is_seen = await test_store.is_incident_seen("fire", different_incident)
        print(f"  🔍 Different incident (should be False): {is_seen}")
        
        print("  ✅ Deduplication test completed successfully")
        
    except Exception as e:
        print(f"  ❌ Deduplication test failed: {e}")
    finally:
        await test_store.disconnect()


async def main():
    """Run all feed poller tests."""
    print("🧪 Austin ATAK Integrations - Feed Poller Tests")
    print("=" * 60)
    
    await test_incident_validation()
    await test_deduplication()
    await test_fire_feed_poller()
    await test_traffic_feed_poller()
    
    print("\n" + "=" * 60)
    print("✅ Feed poller tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
