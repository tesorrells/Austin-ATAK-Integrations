"""Incident lifecycle management for CoT events."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from app.cot.build import build_incident_cot

logger = logging.getLogger(__name__)


def is_incident_active(incident_data: Dict[str, Any]) -> bool:
    """
    Determine if an incident is currently active.
    
    Args:
        incident_data: Incident data from API
        
    Returns:
        True if incident is active, False if archived/closed
    """
    status = incident_data.get("traffic_report_status", "").upper()
    return status == "ACTIVE"


def build_incident_closure_cot(
    incident_data: Dict[str, Any],
    feed_type: str,
    closure_reason: str = "INCIDENT CLOSED"
) -> str:
    """
    Build a CoT XML event to close/remove an incident.
    
    Args:
        incident_data: Original incident data
        feed_type: Type of feed (fire or traffic)
        closure_reason: Reason for closure
        
    Returns:
        CoT XML string with immediate stale time
    """
    # Extract fields based on actual API response
    incident_id = incident_data.get("traffic_report_id", "unknown")
    uid = f"austin.{feed_type}.{incident_id}"
    
    # Get coordinates from actual API fields
    try:
        lat = float(incident_data.get("latitude", 0))
        lon = float(incident_data.get("longitude", 0))
    except (ValueError, TypeError):
        lat, lon = 0.0, 0.0
    
    # Build callsign for closure
    issue_reported = incident_data.get("issue_reported", "INCIDENT")
    if feed_type == "fire":
        callsign = f"AFD: {issue_reported} - {closure_reason}"
    else:
        callsign = f"APD: {issue_reported} - {closure_reason}"
    
    # Build remarks for closure
    address = incident_data.get("address", "Unknown Location")
    status = incident_data.get("traffic_report_status", "CLOSED")
    published_date = incident_data.get("published_date", "")
    
    remarks_parts = [f"{issue_reported} @ {address}"]
    remarks_parts.append(f"Status: {status}")
    remarks_parts.append(f"Closure: {closure_reason}")
    
    # Add published date if available
    if published_date:
        try:
            dt = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            formatted_date = dt.strftime("%Y-%m-%d %H:%M UTC")
            remarks_parts.append(f"Originally Reported: {formatted_date}")
        except:
            pass
    
    remarks = " | ".join(remarks_parts)
    
    # Build link using traffic_report_id
    if feed_type == "fire":
        link = f"https://data.austintexas.gov/resource/wpu4-x69d.json?traffic_report_id={incident_id}"
    else:
        link = f"https://data.austintexas.gov/resource/dx9v-zd7x.json?traffic_report_id={incident_id}"
    
    # Create closure CoT with immediate stale time (1 minute)
    return build_incident_cot(
        uid=uid,
        lat=lat,
        lon=lon,
        callsign=callsign,
        remarks=remarks,
        link=link,
        stale_minutes=1  # Immediate stale for closure
    )


def should_send_closure_cot(
    previous_incident: Optional[Dict[str, Any]],
    current_incident: Optional[Dict[str, Any]]
) -> bool:
    """
    Determine if we should send a closure CoT based on status changes.
    
    Args:
        previous_incident: Previous state of incident (None if new)
        current_incident: Current state of incident (None if disappeared)
        
    Returns:
        True if we should send a closure CoT
    """
    if previous_incident is None:
        # New incident - no closure needed
        return False
    
    previous_status = previous_incident.get("traffic_report_status", "").upper()
    
    # Send closure if incident disappeared from feed (current is None but previous was ACTIVE)
    if current_incident is None and previous_status == "ACTIVE":
        return True
    
    if current_incident is None:
        return False
    
    current_status = current_incident.get("traffic_report_status", "").upper()
    
    # Send closure if status changed from ACTIVE to ARCHIVED
    if previous_status == "ACTIVE" and current_status == "ARCHIVED":
        return True
    
    return False


def get_closure_reason(incident_data: Dict[str, Any]) -> str:
    """
    Determine the closure reason based on incident data.
    
    Args:
        incident_data: Incident data
        
    Returns:
        Closure reason string
    """
    status = incident_data.get("traffic_report_status", "").upper()
    
    if status == "ARCHIVED":
        return "INCIDENT ARCHIVED"
    elif status == "CLOSED":
        return "INCIDENT CLOSED"
    elif status == "RESOLVED":
        return "INCIDENT RESOLVED"
    else:
        return "INCIDENT NO LONGER ACTIVE"


class IncidentLifecycleManager:
    """Manages incident lifecycle and closure notifications."""
    
    def __init__(self):
        self._tracked_incidents: Dict[str, Dict[str, Any]] = {}
    
    def track_incident(self, incident_id: str, incident_data: Dict[str, Any]) -> None:
        """Track an incident for lifecycle management."""
        self._tracked_incidents[incident_id] = incident_data.copy()
    
    def check_for_closures(
        self, 
        current_incidents: Dict[str, Dict[str, Any]], 
        feed_type: str
    ) -> list[str]:
        """
        Check for incidents that need closure CoTs.
        
        Args:
            current_incidents: Current incidents from API (incident_id -> data)
            feed_type: Type of feed (fire or traffic)
            
        Returns:
            List of closure CoT XML strings to send
        """
        closure_cots = []
        
        # Check each tracked incident
        for incident_id, previous_data in list(self._tracked_incidents.items()):
            current_data = current_incidents.get(incident_id)
            
            if should_send_closure_cot(previous_data, current_data):
                try:
                    closure_reason = get_closure_reason(previous_data)
                    closure_cot = build_incident_closure_cot(
                        previous_data, 
                        feed_type, 
                        closure_reason
                    )
                    closure_cots.append(closure_cot)
                    
                    logger.info(f"Sending closure CoT for {feed_type} incident {incident_id}: {closure_reason}")
                    
                    # Remove from tracking since it's closed
                    del self._tracked_incidents[incident_id]
                    
                except Exception as e:
                    logger.error(f"Error creating closure CoT for {incident_id}: {e}")
        
        # Update tracking with current incidents
        for incident_id, incident_data in current_incidents.items():
            self.track_incident(incident_id, incident_data)
        
        return closure_cots
    
    def cleanup_old_incidents(self, max_age_hours: int = 24) -> int:
        """
        Clean up old tracked incidents that are no longer relevant.
        
        Args:
            max_age_hours: Maximum age in hours for tracked incidents
            
        Returns:
            Number of incidents cleaned up
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        for incident_id, incident_data in list(self._tracked_incidents.items()):
            try:
                published_date = incident_data.get("published_date", "")
                if published_date:
                    dt = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                    if dt < cutoff_time:
                        del self._tracked_incidents[incident_id]
                        cleaned_count += 1
            except:
                # If we can't parse the date, remove it anyway
                del self._tracked_incidents[incident_id]
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old tracked incidents")
        
        return cleaned_count
    
    def get_tracking_stats(self) -> Dict[str, Any]:
        """Get statistics about tracked incidents."""
        active_count = 0
        archived_count = 0
        
        for incident_data in self._tracked_incidents.values():
            if is_incident_active(incident_data):
                active_count += 1
            else:
                archived_count += 1
        
        return {
            "total_tracked": len(self._tracked_incidents),
            "active": active_count,
            "archived": archived_count
        }
