"""Traffic incidents feed poller for Austin/Travis County."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import httpx
from app.config import settings
from app.store.seen import seen_store
from app.cot.build import build_traffic_incident_cot
from app.cot.sender import cot_sender

logger = logging.getLogger(__name__)


class TrafficFeedPoller:
    """Poller for Austin traffic incidents feed."""
    
    def __init__(self):
        self.base_url = "https://data.austintexas.gov/resource"
        self.dataset_id = settings.traffic_dataset
        self.poll_interval = settings.poll_seconds
        self.stale_minutes = settings.cot_stale_minutes
        self._running = False
        self._client: Optional[httpx.AsyncClient] = None
    
    async def start(self) -> None:
        """Start the traffic feed poller."""
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
        logger.info("Traffic feed poller started")
        
        # Start polling loop
        asyncio.create_task(self._poll_loop())
    
    async def stop(self) -> None:
        """Stop the traffic feed poller."""
        self._running = False
        if self._client:
            await self._client.aclose()
        logger.info("Traffic feed poller stopped")
    
    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._poll_incidents()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in traffic feed polling loop: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def _poll_incidents(self) -> None:
        """Poll for new traffic incidents."""
        if not self._client:
            return
        
        try:
            # Build query for incidents updated in the last 10 minutes
            # This helps us catch updates to existing incidents
            ten_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=10)
            where_clause = f"last_update >= '{ten_minutes_ago.isoformat()}'"
            
            url = f"{self.base_url}/{self.dataset_id}.json"
            params = {
                "$where": where_clause,
                "$order": "last_update DESC",
                "$limit": 100  # Reasonable limit
            }
            
            logger.debug(f"Polling traffic incidents: {url}")
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            
            incidents = response.json()
            logger.info(f"Fetched {len(incidents)} traffic incidents")
            
            # Process incidents
            incidents_sent = 0
            for incident in incidents:
                try:
                    await self._process_incident(incident)
                    incidents_sent += 1
                except Exception as e:
                    logger.error(f"Error processing traffic incident: {e}")
                    continue
            
            # Update feed state
            await seen_store.update_feed_state(
                feed_type="traffic",
                incidents_fetched=len(incidents),
                incidents_sent=incidents_sent
            )
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error polling traffic incidents: {e}")
        except Exception as e:
            logger.error(f"Unexpected error polling traffic incidents: {e}")
    
    async def _process_incident(self, incident: Dict[str, Any]) -> None:
        """Process a single traffic incident."""
        # Validate required fields
        if not self._validate_incident(incident):
            return
        
        # Check if we've seen this incident before
        is_seen = await seen_store.is_incident_seen("traffic", incident)
        
        # Build CoT XML
        try:
            cot_xml = build_traffic_incident_cot(incident, self.stale_minutes)
        except Exception as e:
            logger.error(f"Error building CoT for traffic incident: {e}")
            return
        
        # Send CoT if sender is available
        cot_sent = False
        if cot_sender.is_running:
            cot_sent = await cot_sender.send_cot(cot_xml)
            if cot_sent:
                logger.debug(f"Sent CoT for traffic incident: {incident.get('event_id', 'unknown')}")
            else:
                logger.warning(f"Failed to send CoT for traffic incident: {incident.get('event_id', 'unknown')}")
        
        # Mark incident as seen
        await seen_store.mark_incident_seen("traffic", incident, cot_sent)
        
        if not is_seen:
            logger.info(f"New traffic incident: {incident.get('event_id', 'unknown')} - {incident.get('category', 'TRAFFIC INCIDENT')}")
    
    def _validate_incident(self, incident: Dict[str, Any]) -> bool:
        """Validate that an incident has required fields."""
        # Check for coordinates
        lat = incident.get("latitude") or incident.get("lat")
        lon = incident.get("longitude") or incident.get("lon")
        
        if not lat or not lon:
            logger.debug("Skipping traffic incident without coordinates")
            return False
        
        try:
            # Ensure coordinates are valid numbers
            float(lat)
            float(lon)
        except (ValueError, TypeError):
            logger.debug("Skipping traffic incident with invalid coordinates")
            return False
        
        # Check for incident identifier
        incident_id = incident.get("event_id") or incident.get("id")
        if not incident_id:
            logger.debug("Skipping traffic incident without ID")
            return False
        
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get polling statistics."""
        return await seen_store.get_feed_stats("traffic")


# Global traffic feed instance
traffic_feed = TrafficFeedPoller()
