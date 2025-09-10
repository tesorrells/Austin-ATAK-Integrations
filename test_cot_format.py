#!/usr/bin/env python3
"""Test script to verify CoT XML format."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.cot.build import build_incident_cot

# Test data
test_incident = {
    "traffic_report_id": "TEST123",
    "latitude": 30.2672,
    "longitude": -97.7431,
    "issue_reported": "TEST INCIDENT",
    "address": "123 Test St, Austin, TX",
    "traffic_report_status": "Active",
    "published_date": "2025-09-10T20:00:00.000Z"
}

# Build CoT XML
cot_xml = build_incident_cot(
    uid="austin.test.TEST123",
    lat=30.2672,
    lon=-97.7431,
    callsign="TEST: TEST INCIDENT",
    remarks="TEST INCIDENT @ 123 Test St, Austin, TX | Status: Active",
    link="https://data.austintexas.gov/Public-Safety/Traffic-Reports/dx9v-zd7x",
    cot_type="a-f-G-U-C",
    stale_minutes=10
)

print("Generated CoT XML:")
print("=" * 50)
print(cot_xml)
print("=" * 50)
print(f"Length: {len(cot_xml)} characters")
