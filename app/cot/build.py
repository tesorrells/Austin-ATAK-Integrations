"""CoT XML builder for incident events."""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Optional
import html
import logging

logger = logging.getLogger(__name__)


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
    
    # Convert to string with proper formatting
    rough_string = ET.tostring(event, encoding="unicode")
    
    # Parse and reformat for better readability
    reparsed = ET.fromstring(rough_string)
    return ET.tostring(reparsed, encoding="unicode")


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
    # Extract fields based on actual API response
    incident_id = incident_data.get("traffic_report_id", "unknown")
    uid = f"austin.fire.{incident_id}"
    
    # Get coordinates from actual API fields
    try:
        lat = float(incident_data.get("latitude", 0))
        lon = float(incident_data.get("longitude", 0))
        
        # Validate coordinates are reasonable (Austin area roughly)
        if not (-98.0 <= lon <= -97.0) or not (30.0 <= lat <= 31.0):
            logger.warning(f"Fire incident {incident_id} has coordinates outside Austin area: {lat}, {lon}")
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid coordinates for fire incident {incident_id}: {e}")
        lat, lon = 0.0, 0.0
    
    # Build callsign from issue_reported field
    issue_reported = incident_data.get("issue_reported", "INCIDENT")
    callsign = f"AFD: {issue_reported}"
    
    # Build remarks
    address = incident_data.get("address", "Unknown Location")
    status = incident_data.get("traffic_report_status", "Active")
    published_date = incident_data.get("published_date", "")
    
    remarks_parts = [f"{issue_reported} @ {address}"]
    remarks_parts.append(f"Status: {status}")
    
    # Add published date if available
    if published_date:
        try:
            # Parse and format the date for readability
            from datetime import datetime
            dt = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            formatted_date = dt.strftime("%Y-%m-%d %H:%M UTC")
            remarks_parts.append(f"Reported: {formatted_date}")
        except:
            pass  # Skip if date parsing fails
    
    remarks = " | ".join(remarks_parts)
    
    # Build link using traffic_report_id
    link = f"https://data.austintexas.gov/resource/wpu4-x69d.json?traffic_report_id={incident_id}"
    
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
    # Extract fields based on actual API response
    incident_id = incident_data.get("traffic_report_id", "unknown")
    uid = f"austin.traffic.{incident_id}"
    
    # Get coordinates from actual API fields
    try:
        lat = float(incident_data.get("latitude", 0))
        lon = float(incident_data.get("longitude", 0))
        
        # Validate coordinates are reasonable (Austin area roughly)
        if not (-98.0 <= lon <= -97.0) or not (30.0 <= lat <= 31.0):
            logger.warning(f"Traffic incident {incident_id} has coordinates outside Austin area: {lat}, {lon}")
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid coordinates for traffic incident {incident_id}: {e}")
        lat, lon = 0.0, 0.0
    
    # Build callsign from issue_reported field
    issue_reported = incident_data.get("issue_reported", "TRAFFIC INCIDENT")
    callsign = f"APD: {issue_reported}"
    
    # Build remarks
    address = incident_data.get("address", "Unknown Location")
    status = incident_data.get("traffic_report_status", "Active")
    published_date = incident_data.get("published_date", "")
    
    remarks_parts = [f"{issue_reported} @ {address}"]
    remarks_parts.append(f"Status: {status}")
    
    # Add published date if available
    if published_date:
        try:
            # Parse and format the date for readability
            from datetime import datetime
            dt = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            formatted_date = dt.strftime("%Y-%m-%d %H:%M UTC")
            remarks_parts.append(f"Reported: {formatted_date}")
        except:
            pass  # Skip if date parsing fails
    
    remarks = " | ".join(remarks_parts)
    
    # Build link using traffic_report_id
    link = f"https://data.austintexas.gov/resource/dx9v-zd7x.json?traffic_report_id={incident_id}"
    
    return build_incident_cot(
        uid=uid,
        lat=lat,
        lon=lon,
        callsign=callsign,
        remarks=remarks,
        link=link,
        stale_minutes=stale_minutes
    )
