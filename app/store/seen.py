"""SQLite-based deduplication and state management."""

import aiosqlite
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Set, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class SeenStore:
    """SQLite-based store for tracking seen incidents and deduplication."""
    
    def __init__(self, db_path: str = "app/store/seen.db"):
        self.db_path = db_path
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Initialize database connection and create tables."""
        self._connection = await aiosqlite.connect(self.db_path)
        
        # Create tables
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS seen_incidents (
                id TEXT PRIMARY KEY,
                feed_type TEXT NOT NULL,
                incident_data TEXT NOT NULL,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cot_sent BOOLEAN DEFAULT FALSE
            )
        """)
        
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS feed_state (
                feed_type TEXT PRIMARY KEY,
                last_poll TIMESTAMP,
                last_watermark TEXT,
                poll_count INTEGER DEFAULT 0,
                incidents_fetched INTEGER DEFAULT 0,
                incidents_sent INTEGER DEFAULT 0
            )
        """)
        
        await self._connection.commit()
        logger.info("Database initialized successfully")
    
    async def disconnect(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    def _generate_incident_id(self, feed_type: str, incident_data: Dict[str, Any]) -> str:
        """Generate a stable ID for an incident."""
        # Try to use existing ID fields first
        if feed_type == "fire":
            incident_id = incident_data.get("incident_number") or incident_data.get("id")
        elif feed_type == "traffic":
            incident_id = incident_data.get("event_id") or incident_data.get("id")
        else:
            incident_id = incident_data.get("id")
        
        if incident_id:
            return f"{feed_type}.{incident_id}"
        
        # Fallback: create hash from key fields
        key_fields = {
            "type": incident_data.get("category", incident_data.get("incident_type", "")),
            "location": incident_data.get("address", incident_data.get("location", "")),
            "lat": str(incident_data.get("latitude", incident_data.get("lat", ""))),
            "lon": str(incident_data.get("longitude", incident_data.get("lon", ""))),
        }
        
        key_string = json.dumps(key_fields, sort_keys=True)
        hash_id = hashlib.md5(key_string.encode()).hexdigest()[:12]
        return f"{feed_type}.{hash_id}"
    
    async def is_incident_seen(self, feed_type: str, incident_data: Dict[str, Any]) -> bool:
        """Check if an incident has been seen before."""
        if not self._connection:
            return False
        
        incident_id = self._generate_incident_id(feed_type, incident_data)
        
        cursor = await self._connection.execute(
            "SELECT id FROM seen_incidents WHERE id = ?",
            (incident_id,)
        )
        result = await cursor.fetchone()
        return result is not None
    
    async def mark_incident_seen(
        self, 
        feed_type: str, 
        incident_data: Dict[str, Any], 
        cot_sent: bool = False
    ) -> str:
        """
        Mark an incident as seen and return its ID.
        
        Args:
            feed_type: Type of feed (fire, traffic)
            incident_data: Incident data dictionary
            cot_sent: Whether CoT was sent for this incident
            
        Returns:
            The incident ID
        """
        if not self._connection:
            raise RuntimeError("Database not connected")
        
        incident_id = self._generate_incident_id(feed_type, incident_data)
        now = datetime.now(timezone.utc).isoformat()
        
        # Check if incident already exists
        cursor = await self._connection.execute(
            "SELECT id FROM seen_incidents WHERE id = ?",
            (incident_id,)
        )
        exists = await cursor.fetchone()
        
        if exists:
            # Update existing record
            await self._connection.execute("""
                UPDATE seen_incidents 
                SET last_seen = ?, cot_sent = ?
                WHERE id = ?
            """, (now, cot_sent, incident_id))
        else:
            # Insert new record
            await self._connection.execute("""
                INSERT INTO seen_incidents (id, feed_type, incident_data, first_seen, last_seen, cot_sent)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (incident_id, feed_type, json.dumps(incident_data), now, now, cot_sent))
        
        await self._connection.commit()
        return incident_id
    
    async def update_feed_state(
        self, 
        feed_type: str, 
        incidents_fetched: int, 
        incidents_sent: int,
        last_watermark: Optional[str] = None
    ) -> None:
        """Update feed polling state."""
        if not self._connection:
            return
        
        now = datetime.now(timezone.utc).isoformat()
        
        await self._connection.execute("""
            INSERT OR REPLACE INTO feed_state 
            (feed_type, last_poll, last_watermark, poll_count, incidents_fetched, incidents_sent)
            VALUES (?, ?, ?, 
                COALESCE((SELECT poll_count FROM feed_state WHERE feed_type = ?), 0) + 1,
                COALESCE((SELECT incidents_fetched FROM feed_state WHERE feed_type = ?), 0) + ?,
                COALESCE((SELECT incidents_sent FROM feed_state WHERE feed_type = ?), 0) + ?
            )
        """, (feed_type, now, last_watermark, feed_type, feed_type, incidents_fetched, feed_type, incidents_sent))
        
        await self._connection.commit()
    
    async def get_feed_stats(self, feed_type: str) -> Dict[str, Any]:
        """Get statistics for a feed."""
        if not self._connection:
            return {}
        
        cursor = await self._connection.execute(
            "SELECT * FROM feed_state WHERE feed_type = ?",
            (feed_type,)
        )
        result = await cursor.fetchone()
        
        if result:
            return {
                "feed_type": result[0],
                "last_poll": result[1],
                "last_watermark": result[2],
                "poll_count": result[3],
                "incidents_fetched": result[4],
                "incidents_sent": result[5]
            }
        
        return {}
    
    async def cleanup_old_incidents(self, days_old: int = 7) -> int:
        """Clean up incidents older than specified days."""
        if not self._connection:
            return 0
        
        cutoff_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
        
        cursor = await self._connection.execute(
            "DELETE FROM seen_incidents WHERE last_seen < ?",
            (cutoff_date.isoformat(),)
        )
        
        deleted_count = cursor.rowcount
        await self._connection.commit()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old incidents")
        
        return deleted_count


# Global store instance
seen_store = SeenStore()
