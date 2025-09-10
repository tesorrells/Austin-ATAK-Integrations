"""CoT XML builder for incident events."""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Optional
import html


def xml_escape(text: str) -> str:
    """Escape text for XML content."""
    return html.escape(str(text), quote=True)


def build_incident_cot(
    uid: str,
    lat: float,
    lon: float,
    callsign: str,
    remarks: str,
    link: str,
    cot_type: str = "b-e-i",
    stale_minutes: int = 10,
    how: str = "m-g"
) -> str:
    """
    Build a CoT XML event for an incident.
    
    Args:
        uid: Unique identifier for the event
        lat: Latitude coordinate
        lon: Longitude coordinate
        callsign: Contact callsign (e.g., "AFD: STRUCTURE FIRE")
        remarks: Incident remarks/description
        link: URL link to source data
        cot_type: CoT event type (default: "b-e-i" for incident)
        stale_minutes: Minutes until event becomes stale
        how: How the event was generated (default: "m-g" for machine-generated)
    
    Returns:
        CoT XML string
    """
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    stale = now + timedelta(minutes=stale_minutes)
    
    # Create root event element
    event = ET.Element("event")
    event.set("version", "2.0")
    event.set("uid", xml_escape(uid))
    event.set("type", cot_type)
    event.set("time", now.isoformat())
    event.set("start", now.isoformat())
    event.set("stale", stale.isoformat())
    event.set("how", how)
    
    # Add point element
    point = ET.SubElement(event, "point")
    point.set("lat", str(lat))
    point.set("lon", str(lon))
    point.set("hae", "9999999.0")
    point.set("ce", "9999999.0")
    point.set("le", "9999999.0")
    
    # Add detail element
    detail = ET.SubElement(event, "detail")
    
    # Add contact
    contact = ET.SubElement(detail, "contact")
    contact.set("callsign", xml_escape(callsign))
    
    # Add link
    link_elem = ET.SubElement(detail, "link")
    link_elem.set("url", xml_escape(link))
    
    # Add remarks
    remarks_elem = ET.SubElement(detail, "remarks")
    remarks_elem.text = xml_escape(remarks)
    
    # Convert to string
    return ET.tostring(event, encoding="unicode")


def build_fire_incident_cot(
    incident_data: dict,
    stale_minutes: int = 10
) -> str:
    """
    Build a CoT XML event for a fire incident.
    
    Args:
        incident_data: Fire incident data from SODA API
        stale_minutes: Minutes until event becomes stale
    
    Returns:
        CoT XML string
    """
    # Extract fields - adjust field names based on actual SODA response
    incident_id = incident_data.get("incident_number", incident_data.get("id", "unknown"))
    uid = f"austin.fire.{incident_id}"
    
    # Get coordinates - adjust field names as needed
    lat = float(incident_data.get("latitude", incident_data.get("lat", 0)))
    lon = float(incident_data.get("longitude", incident_data.get("lon", 0)))
    
    # Build callsign
    category = incident_data.get("category", incident_data.get("incident_type", "INCIDENT"))
    callsign = f"AFD: {category}"
    
    # Build remarks
    address = incident_data.get("address", incident_data.get("location", "Unknown Location"))
    status = incident_data.get("status", "Active")
    units = incident_data.get("units", "")
    
    remarks_parts = [f"{category} @ {address}"]
    if units:
        remarks_parts.append(f"Units: {units}")
    remarks_parts.append(f"Status: {status}")
    
    remarks = " | ".join(remarks_parts)
    
    # Build link
    link = f"https://data.austintexas.gov/resource/wpu4-x69d.json?incident_number={incident_id}"
    
    return build_incident_cot(
        uid=uid,
        lat=lat,
        lon=lon,
        callsign=callsign,
        remarks=remarks,
        link=link,
        stale_minutes=stale_minutes
    )


def build_traffic_incident_cot(
    incident_data: dict,
    stale_minutes: int = 10
) -> str:
    """
    Build a CoT XML event for a traffic incident.
    
    Args:
        incident_data: Traffic incident data from SODA API
        stale_minutes: Minutes until event becomes stale
    
    Returns:
        CoT XML string
    """
    # Extract fields - adjust field names based on actual SODA response
    incident_id = incident_data.get("event_id", incident_data.get("id", "unknown"))
    uid = f"austin.traffic.{incident_id}"
    
    # Get coordinates - adjust field names as needed
    lat = float(incident_data.get("latitude", incident_data.get("lat", 0)))
    lon = float(incident_data.get("longitude", incident_data.get("lon", 0)))
    
    # Build callsign
    category = incident_data.get("category", incident_data.get("incident_type", "TRAFFIC INCIDENT"))
    callsign = f"APD: {category}"
    
    # Build remarks
    location = incident_data.get("location", incident_data.get("address", "Unknown Location"))
    status = incident_data.get("status", "Active")
    description = incident_data.get("description", "")
    
    remarks_parts = [f"{category} @ {location}"]
    if description:
        remarks_parts.append(description)
    remarks_parts.append(f"Status: {status}")
    
    remarks = " | ".join(remarks_parts)
    
    # Build link
    link = f"https://data.austintexas.gov/resource/dx9v-zd7x.json?event_id={incident_id}"
    
    return build_incident_cot(
        uid=uid,
        lat=lat,
        lon=lon,
        callsign=callsign,
        remarks=remarks,
        link=link,
        stale_minutes=stale_minutes
    )
