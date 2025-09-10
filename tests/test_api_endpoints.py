"""Test actual API endpoints to see what data they return."""

import asyncio
import json
import httpx
from datetime import datetime, timezone, timedelta


async def test_fire_api_endpoint():
    """Test the actual fire incidents API endpoint."""
    print("🔥 Testing Fire Incidents API...")
    
    base_url = "https://data.austintexas.gov/resource"
    dataset_id = "wpu4-x69d"
    
    # Test basic endpoint
    url = f"{base_url}/{dataset_id}.json"
    params = {"$limit": 5}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Fire API Response Status: {response.status_code}")
            print(f"📊 Fire API Records Returned: {len(data)}")
            
            if data:
                print("\n🔍 Sample Fire Incident Data:")
                print(json.dumps(data[0], indent=2))
                
                # Check for required fields
                sample = data[0]
                required_fields = ['incident_number', 'latitude', 'longitude', 'category']
                missing_fields = [field for field in required_fields if field not in sample]
                
                if missing_fields:
                    print(f"⚠️  Missing fields in fire data: {missing_fields}")
                else:
                    print("✅ All required fields present in fire data")
                    
                # Show all available fields
                print(f"\n📋 All available fields in fire data:")
                for key in sorted(sample.keys()):
                    print(f"  - {key}: {type(sample[key]).__name__}")
                    
        except Exception as e:
            print(f"❌ Fire API Error: {e}")


async def test_traffic_api_endpoint():
    """Test the actual traffic incidents API endpoint."""
    print("\n🚗 Testing Traffic Incidents API...")
    
    base_url = "https://data.austintexas.gov/resource"
    dataset_id = "dx9v-zd7x"
    
    # Test basic endpoint
    url = f"{base_url}/{dataset_id}.json"
    params = {"$limit": 5}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Traffic API Response Status: {response.status_code}")
            print(f"📊 Traffic API Records Returned: {len(data)}")
            
            if data:
                print("\n🔍 Sample Traffic Incident Data:")
                print(json.dumps(data[0], indent=2))
                
                # Check for required fields
                sample = data[0]
                required_fields = ['event_id', 'latitude', 'longitude', 'category']
                missing_fields = [field for field in required_fields if field not in sample]
                
                if missing_fields:
                    print(f"⚠️  Missing fields in traffic data: {missing_fields}")
                else:
                    print("✅ All required fields present in traffic data")
                    
                # Show all available fields
                print(f"\n📋 All available fields in traffic data:")
                for key in sorted(sample.keys()):
                    print(f"  - {key}: {type(sample[key]).__name__}")
                    
        except Exception as e:
            print(f"❌ Traffic API Error: {e}")


async def test_recent_incidents():
    """Test getting recent incidents from both APIs."""
    print("\n⏰ Testing Recent Incidents (last 10 minutes)...")
    
    base_url = "https://data.austintexas.gov/resource"
    ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
    where_clause = f"last_update >= '{ten_minutes_ago.isoformat()}'"
    
    async with httpx.AsyncClient() as client:
        # Test fire incidents
        try:
            fire_url = f"{base_url}/wpu4-x69d.json"
            fire_params = {
                "$where": where_clause,
                "$order": "last_update DESC",
                "$limit": 10
            }
            
            response = await client.get(fire_url, params=fire_params)
            response.raise_for_status()
            fire_data = response.json()
            
            print(f"🔥 Recent Fire Incidents: {len(fire_data)}")
            if fire_data:
                print(f"   Latest: {fire_data[0].get('incident_number', 'N/A')} - {fire_data[0].get('category', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Recent Fire API Error: {e}")
        
        # Test traffic incidents
        try:
            traffic_url = f"{base_url}/dx9v-zd7x.json"
            traffic_params = {
                "$where": where_clause,
                "$order": "last_update DESC", 
                "$limit": 10
            }
            
            response = await client.get(traffic_url, params=traffic_params)
            response.raise_for_status()
            traffic_data = response.json()
            
            print(f"🚗 Recent Traffic Incidents: {len(traffic_data)}")
            if traffic_data:
                print(f"   Latest: {traffic_data[0].get('event_id', 'N/A')} - {traffic_data[0].get('category', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Recent Traffic API Error: {e}")


async def main():
    """Run all API endpoint tests."""
    print("🧪 Austin ATAK Integrations - API Endpoint Tests")
    print("=" * 60)
    
    await test_fire_api_endpoint()
    await test_traffic_api_endpoint()
    await test_recent_incidents()
    
    print("\n" + "=" * 60)
    print("✅ API endpoint tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
