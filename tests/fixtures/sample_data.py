"""Sample data from actual API responses for testing."""

# Sample fire incident data from actual API
SAMPLE_FIRE_INCIDENT = {
    "traffic_report_id": "2482DA779B41C3381F0868E0F43445F13D68907F_1757523101_fire_incident",
    "published_date": "2025-09-10T16:51:41.000Z",
    "issue_reported": "GRASS - Small Grass Fire",
    "location": {
        "type": "Point",
        "coordinates": [-97.553651, 30.198823]
    },
    "latitude": "30.198823",
    "longitude": "-97.553651",
    "address": "3520 Victorine Ln",
    "traffic_report_status": "ACTIVE",
    "traffic_report_status_date_time": "2025-09-10T16:55:12.000Z",
    "agency": "FIRE"
}

# Sample traffic incident data from actual API
SAMPLE_TRAFFIC_INCIDENT = {
    "traffic_report_id": "F350D780EA8AAA48030B4DB64F790C14DBCD757F_1709688579",
    "published_date": "2024-03-06T01:29:39.000Z",
    "issue_reported": "Stalled Vehicle",
    "location": {
        "type": "Point",
        "coordinates": [-97.705874, 30.32358]
    },
    "latitude": "30.32358",
    "longitude": "-97.705874",
    "address": "E 290 Svrd Wb To Ih 35 Nb Ramp / N Ih 35 Svrd Sb At E 290 Tr",
    "traffic_report_status": "ARCHIVED",
    "traffic_report_status_date_time": "2024-03-06T02:10:12.000Z",
    "agency": "AUSTIN PD           "
}

# Expected CoT XML for fire incident
EXPECTED_FIRE_COT = '''<event version="2.0" uid="austin.fire.2482DA779B41C3381F0868E0F43445F13D68907F_1757523101_fire_incident" type="b-e-i" time="2025-09-10T16:51:41.000Z" start="2025-09-10T16:51:41.000Z" stale="2025-09-10T17:01:41.000Z" how="m-g">
  <point lat="30.198823" lon="-97.553651" hae="9999999.0" ce="9999999.0" le="9999999.0"/>
  <detail>
    <contact callsign="AFD: GRASS - Small Grass Fire"/>
    <link url="https://data.austintexas.gov/resource/wpu4-x69d.json?traffic_report_id=2482DA779B41C3381F0868E0F43445F13D68907F_1757523101_fire_incident"/>
    <remarks>GRASS - Small Grass Fire @ 3520 Victorine Ln | Status: ACTIVE</remarks>
  </detail>
</event>'''

# Expected CoT XML for traffic incident
EXPECTED_TRAFFIC_COT = '''<event version="2.0" uid="austin.traffic.F350D780EA8AAA48030B4DB64F790C14DBCD757F_1709688579" type="b-e-i" time="2024-03-06T01:29:39.000Z" start="2024-03-06T01:29:39.000Z" stale="2024-03-06T01:39:39.000Z" how="m-g">
  <point lat="30.32358" lon="-97.705874" hae="9999999.0" ce="9999999.0" le="9999999.0"/>
  <detail>
    <contact callsign="APD: Stalled Vehicle"/>
    <link url="https://data.austintexas.gov/resource/dx9v-zd7x.json?traffic_report_id=F350D780EA8AAA48030B4DB64F790C14DBCD757F_1709688579"/>
    <remarks>Stalled Vehicle @ E 290 Svrd Wb To Ih 35 Nb Ramp / N Ih 35 Svrd Sb At E 290 Tr | Status: ARCHIVED</remarks>
  </detail>
</event>'''
