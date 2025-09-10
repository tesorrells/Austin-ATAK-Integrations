"""Test CoT XML generation with real API data."""

import asyncio
import json
import httpx
from datetime import datetime, timezone, timedelta
import sys
import os

# Add the app directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.cot.build import build_fire_incident_cot, build_traffic_incident_cot


async def test_cot_with_real_fire_data():
    """Test CoT generation with real fire incident data."""
    print("🔥 Testing CoT Generation with Real Fire Data...")
    
    base_url = "https://data.austintexas.gov/resource"
    dataset_id = "wpu4-x69d"
    
    async with httpx.AsyncClient() as client:
        url = f"{base_url}/{dataset_id}.json"
        params = {"$limit": 3}
        
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            incidents = response.json()
            
            print(f"📊 Fetched {len(incidents)} fire incidents")
            
            for i, incident in enumerate(incidents, 1):
                print(f"\n🔍 Fire Incident {i}:")
                print(f"  ID: {incident.get('traffic_report_id', 'N/A')}")
                print(f"  Issue: {incident.get('issue_reported', 'N/A')}")
                print(f"  Address: {incident.get('address', 'N/A')}")
                print(f"  Status: {incident.get('traffic_report_status', 'N/A')}")
                print(f"  Coordinates: {incident.get('latitude', 'N/A')}, {incident.get('longitude', 'N/A')}")
                
                # Generate CoT XML
                try:
                    cot_xml = build_fire_incident_cot(incident, stale_minutes=10)
                    print(f"  ✅ CoT Generated Successfully")
                    print(f"  📄 CoT XML Preview:")
                    # Show first few lines of the CoT
                    lines = cot_xml.split('\n')
                    for line in lines[:5]:
                        print(f"    {line}")
                    if len(lines) > 5:
                        print(f"    ... ({len(lines) - 5} more lines)")
                        
                except Exception as e:
                    print(f"  ❌ CoT Generation Failed: {e}")
                    
        except Exception as e:
            print(f"❌ Fire API Error: {e}")


async def test_cot_with_real_traffic_data():
    """Test CoT generation with real traffic incident data."""
    print("\n🚗 Testing CoT Generation with Real Traffic Data...")
    
    base_url = "https://data.austintexas.gov/resource"
    dataset_id = "dx9v-zd7x"
    
    async with httpx.AsyncClient() as client:
        url = f"{base_url}/{dataset_id}.json"
        params = {"$limit": 3}
        
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            incidents = response.json()
            
            print(f"📊 Fetched {len(incidents)} traffic incidents")
            
            for i, incident in enumerate(incidents, 1):
                print(f"\n🔍 Traffic Incident {i}:")
                print(f"  ID: {incident.get('traffic_report_id', 'N/A')}")
                print(f"  Issue: {incident.get('issue_reported', 'N/A')}")
                print(f"  Address: {incident.get('address', 'N/A')}")
                print(f"  Status: {incident.get('traffic_report_status', 'N/A')}")
                print(f"  Coordinates: {incident.get('latitude', 'N/A')}, {incident.get('longitude', 'N/A')}")
                
                # Generate CoT XML
                try:
                    cot_xml = build_traffic_incident_cot(incident, stale_minutes=10)
                    print(f"  ✅ CoT Generated Successfully")
                    print(f"  📄 CoT XML Preview:")
                    # Show first few lines of the CoT
                    lines = cot_xml.split('\n')
                    for line in lines[:5]:
                        print(f"    {line}")
                    if len(lines) > 5:
                        print(f"    ... ({len(lines) - 5} more lines)")
                        
                except Exception as e:
                    print(f"  ❌ CoT Generation Failed: {e}")
                    
        except Exception as e:
            print(f"❌ Traffic API Error: {e}")


async def test_recent_incidents_corrected():
    """Test getting recent incidents with corrected date format."""
    print("\n⏰ Testing Recent Incidents with Corrected Date Format...")
    
    base_url = "https://data.austintexas.gov/resource"
    
    # Use a more recent date to ensure we get results
    recent_date = datetime.now(timezone.utc) - timedelta(days=1)
    date_str = recent_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    async with httpx.AsyncClient() as client:
        # Test fire incidents
        try:
            fire_url = f"{base_url}/wpu4-x69d.json"
            fire_params = {
                "$where": f"published_date >= '{date_str}'",
                "$order": "published_date DESC",
                "$limit": 5
            }
            
            response = await client.get(fire_url, params=fire_params)
            response.raise_for_status()
            fire_data = response.json()
            
            print(f"🔥 Recent Fire Incidents (since {date_str}): {len(fire_data)}")
            for incident in fire_data[:2]:  # Show first 2
                print(f"  - {incident.get('traffic_report_id', 'N/A')}: {incident.get('issue_reported', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Recent Fire API Error: {e}")
        
        # Test traffic incidents
        try:
            traffic_url = f"{base_url}/dx9v-zd7x.json"
            traffic_params = {
                "$where": f"published_date >= '{date_str}'",
                "$order": "published_date DESC",
                "$limit": 5
            }
            
            response = await client.get(traffic_url, params=traffic_params)
            response.raise_for_status()
            traffic_data = response.json()
            
            print(f"🚗 Recent Traffic Incidents (since {date_str}): {len(traffic_data)}")
            for incident in traffic_data[:2]:  # Show first 2
                print(f"  - {incident.get('traffic_report_id', 'N/A')}: {incident.get('issue_reported', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Recent Traffic API Error: {e}")


async def main():
    """Run all CoT generation tests."""
    print("🧪 Austin ATAK Integrations - CoT Generation Tests")
    print("=" * 60)
    
    await test_cot_with_real_fire_data()
    await test_cot_with_real_traffic_data()
    await test_recent_incidents_corrected()
    
    print("\n" + "=" * 60)
    print("✅ CoT generation tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
