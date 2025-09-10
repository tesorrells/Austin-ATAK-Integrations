"""Fire incidents feed poller for Austin/Travis County."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings
from app.store.seen import seen_store
from app.cot.build import build_fire_incident_cot
from app.cot.sender import cot_sender
from app.cot.lifecycle import IncidentLifecycleManager

logger = logging.getLogger(__name__)


class FireFeedPoller:
    """Poller for Austin fire incidents feed."""
    
    def __init__(self):
        self.base_url = "https://data.austintexas.gov/resource"
        self.dataset_id = settings.fire_dataset
        self.poll_interval = settings.poll_seconds
        self.stale_minutes = settings.cot_stale_minutes
        self._running = False
        self._client: Optional[httpx.AsyncClient] = None
        self._lifecycle_manager = IncidentLifecycleManager()
    
    async def start(self) -> None:
        """Start the fire feed poller."""
        if self._running:
            return
        
        # Create HTTP client with app token if available
        headers = {}
        if settings.soda_app_token:
            headers["X-App-Token"] = settings.soda_app_token
        
        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
            follow_redirects=True
        )
        
        self._running = True
        logger.info("Fire feed poller started")
        
        # Start polling loop as a background task
        asyncio.create_task(self._poll_loop())
        logger.info("Fire feed polling loop started")
    
    async def stop(self) -> None:
        """Stop the fire feed poller."""
        self._running = False
        if self._client:
            await self._client.aclose()
        logger.info("Fire feed poller stopped")
    
    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._poll_incidents()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in fire feed polling loop: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def _poll_incidents(self) -> None:
        """Poll for new fire incidents."""
        if not self._client:
            return
        
        try:
            # Build query for incidents published in the last 10 minutes
            # This helps us catch updates to existing incidents
            ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
            where_clause = f"published_date >= '{ten_minutes_ago.strftime('%Y-%m-%dT%H:%M:%S.000Z')}'"
            
            url = f"{self.base_url}/{self.dataset_id}.json"
            params = {
                "$where": where_clause,
                "$order": "published_date DESC",
                "$limit": 100  # Reasonable limit
            }
            
            logger.debug(f"Polling fire incidents: {url}")
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            
            incidents = response.json()
            logger.info(f"Fetched {len(incidents)} fire incidents")
            
            # Process incidents and check for closures
            incidents_sent = 0
            current_incidents = {}
            
            for incident in incidents:
                try:
                    incident_id = incident.get("traffic_report_id")
                    if incident_id:
                        current_incidents[incident_id] = incident
                    
                    await self._process_incident(incident)
                    incidents_sent += 1
                except Exception as e:
                    logger.error(f"Error processing fire incident: {e}")
                    continue
            
            # Check for incident closures
            closure_cots = self._lifecycle_manager.check_for_closures(current_incidents, "fire")
            for closure_cot in closure_cots:
                if cot_sender.is_running:
                    await cot_sender.send_cot(closure_cot)
                    incidents_sent += 1
            
            # Clean up old tracked incidents
            self._lifecycle_manager.cleanup_old_incidents()
            
            # Update feed state
            await seen_store.update_feed_state(
                feed_type="fire",
                incidents_fetched=len(incidents),
                incidents_sent=incidents_sent
            )
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error polling fire incidents: {e}")
        except Exception as e:
            logger.error(f"Unexpected error polling fire incidents: {e}")
    
    async def _process_incident(self, incident: Dict[str, Any]) -> None:
        """Process a single fire incident."""
        # Validate required fields
        if not self._validate_incident(incident):
            return
        
        # Check if we've seen this incident before
        is_seen = await seen_store.is_incident_seen("fire", incident)
        
        # Build CoT XML
        try:
            cot_xml = build_fire_incident_cot(incident, self.stale_minutes)
        except Exception as e:
            logger.error(f"Error building CoT for fire incident: {e}")
            return
        
        # Send CoT if sender is available
        cot_sent = False
        if cot_sender.is_running:
            cot_sent = await cot_sender.send_cot(cot_xml)
            if not cot_sent:
                logger.warning(f"Failed to send CoT for fire incident: {incident.get('traffic_report_id', 'unknown')}")
        else:
            logger.error("CoT sender is not running, cannot send CoT")
        
        # Mark incident as seen
        await seen_store.mark_incident_seen("fire", incident, cot_sent)
        
        if not is_seen:
            logger.info(f"New fire incident: {incident.get('traffic_report_id', 'unknown')} - {incident.get('issue_reported', 'INCIDENT')}")
    
    def _validate_incident(self, incident: Dict[str, Any]) -> bool:
        """Validate that an incident has required fields."""
        # Check for coordinates
        lat = incident.get("latitude")
        lon = incident.get("longitude")
        
        if not lat or not lon:
            logger.debug("Skipping fire incident without coordinates")
            return False
        
        try:
            # Ensure coordinates are valid numbers
            float(lat)
            float(lon)
        except (ValueError, TypeError):
            logger.debug("Skipping fire incident with invalid coordinates")
            return False
        
        # Check for incident identifier
        incident_id = incident.get("traffic_report_id")
        if not incident_id:
            logger.debug("Skipping fire incident without traffic_report_id")
            return False
        
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get polling statistics."""
        return await seen_store.get_feed_stats("fire")


# Global fire feed instance
fire_feed = FireFeedPoller()
