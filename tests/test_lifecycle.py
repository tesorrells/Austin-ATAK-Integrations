"""Test incident lifecycle management."""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.cot.lifecycle import (
    IncidentLifecycleManager, 
    is_incident_active, 
    should_send_closure_cot,
    get_closure_reason
)


async def test_incident_lifecycle():
    """Test incident lifecycle management functionality."""
    print("🔄 Testing Incident Lifecycle Management")
    print("=" * 50)
    
    # Test 1: Active incident detection
    print("\n1. Testing Active Incident Detection:")
    active_incident = {
        "traffic_report_id": "test123",
        "traffic_report_status": "ACTIVE",
        "issue_reported": "STRUCTURE FIRE",
        "address": "123 Test St"
    }
    
    archived_incident = {
        "traffic_report_id": "test456", 
        "traffic_report_status": "ARCHIVED",
        "issue_reported": "TRAFFIC HAZARD",
        "address": "456 Test Ave"
    }
    
    print(f"  Active incident: {is_incident_active(active_incident)}")
    print(f"  Archived incident: {is_incident_active(archived_incident)}")
    
    # Test 2: Closure detection
    print("\n2. Testing Closure Detection:")
    should_close = should_send_closure_cot(active_incident, archived_incident)
    print(f"  Should send closure CoT: {should_close}")
    
    should_not_close = should_send_closure_cot(archived_incident, active_incident)
    print(f"  Should not send closure CoT: {should_not_close}")
    
    # Test 3: Closure reason
    print("\n3. Testing Closure Reason:")
    reason = get_closure_reason(archived_incident)
    print(f"  Closure reason: {reason}")
    
    # Test 4: Lifecycle manager
    print("\n4. Testing Lifecycle Manager:")
    manager = IncidentLifecycleManager()
    
    # Track some incidents
    manager.track_incident("incident1", active_incident)
    manager.track_incident("incident2", archived_incident)
    
    # Simulate current state (incident1 is now archived, incident2 is gone)
    current_incidents = {
        "incident1": {
            "traffic_report_id": "incident1",
            "traffic_report_status": "ARCHIVED",
            "issue_reported": "STRUCTURE FIRE",
            "address": "123 Test St",
            "latitude": "30.2714",
            "longitude": "-97.7420"
        }
    }
    
    # Check for closures
    closure_cots = manager.check_for_closures(current_incidents, "fire")
    print(f"  Closure CoTs generated: {len(closure_cots)}")
    
    if closure_cots:
        print("  Sample closure CoT:")
        print(f"    {closure_cots[0][:200]}...")
    
    # Test 5: Statistics
    print("\n5. Testing Statistics:")
    stats = manager.get_tracking_stats()
    print(f"  Tracking stats: {stats}")
    
    print("\n✅ Lifecycle management tests completed!")


async def test_closure_cot_generation():
    """Test closure CoT generation."""
    print("\n📄 Testing Closure CoT Generation")
    print("=" * 50)
    
    from app.cot.lifecycle import build_incident_closure_cot
    
    # Test fire incident closure
    fire_incident = {
        "traffic_report_id": "fire123",
        "traffic_report_status": "ARCHIVED",
        "issue_reported": "STRUCTURE FIRE",
        "address": "123 Fire St",
        "latitude": "30.2714",
        "longitude": "-97.7420",
        "published_date": "2025-09-10T17:00:00.000Z"
    }
    
    closure_cot = build_incident_closure_cot(fire_incident, "fire", "INCIDENT ARCHIVED")
    print("Fire incident closure CoT:")
    print(f"  {closure_cot[:300]}...")
    
    # Test traffic incident closure
    traffic_incident = {
        "traffic_report_id": "traffic456",
        "traffic_report_status": "ARCHIVED", 
        "issue_reported": "TRAFFIC HAZARD",
        "address": "456 Traffic Ave",
        "latitude": "30.2714",
        "longitude": "-97.7420",
        "published_date": "2025-09-10T17:00:00.000Z"
    }
    
    closure_cot = build_incident_closure_cot(traffic_incident, "traffic", "INCIDENT RESOLVED")
    print("\nTraffic incident closure CoT:")
    print(f"  {closure_cot[:300]}...")
    
    print("\n✅ Closure CoT generation tests completed!")


async def main():
    """Run all lifecycle tests."""
    print("🧪 Austin ATAK Integrations - Lifecycle Management Tests")
    print("=" * 60)
    
    await test_incident_lifecycle()
    await test_closure_cot_generation()
    
    print("\n" + "=" * 60)
    print("✅ All lifecycle tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
