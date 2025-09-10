"""FastAPI main application for Austin ATAK integrations."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from app.config import settings
from app.store.seen import seen_store
from app.cot.sender import cot_sender
from app.feeds.fire import fire_feed
from app.feeds.traffic import traffic_feed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Austin ATAK integrations...")
    
    try:
        # Initialize database
        await seen_store.connect()
        logger.info("Database connected")
        
        # Start CoT sender
        await cot_sender.start()
        logger.info("CoT sender started")
        
        # Start feed pollers
        await fire_feed.start()
        await traffic_feed.start()
        logger.info("Feed pollers started")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Cleanup
    logger.info("Shutting down Austin ATAK integrations...")
    
    try:
        await fire_feed.stop()
        await traffic_feed.stop()
        await cot_sender.stop()
        await seen_store.disconnect()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="Austin ATAK Integrations",
    description="Real-time fire and traffic incident feeds for TAK/ATAK",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "austin-atak-integrations"}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        # Check if all components are running
        checks = {
            "database": seen_store._connection is not None,
            "cot_sender": cot_sender.is_running,
            "fire_feed": fire_feed._running,
            "traffic_feed": traffic_feed._running,
        }
        
        all_ready = all(checks.values())
        
        if all_ready:
            return {"status": "ready", "checks": checks}
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "not ready", "checks": checks}
            )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "error": str(e)}
        )


@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint."""
    try:
        fire_stats = await fire_feed.get_stats()
        traffic_stats = await traffic_feed.get_stats()
        
        metrics_data = {
            "fire_feed": {
                "last_poll": fire_stats.get("last_poll"),
                "poll_count": fire_stats.get("poll_count", 0),
                "incidents_fetched": fire_stats.get("incidents_fetched", 0),
                "incidents_sent": fire_stats.get("incidents_sent", 0),
            },
            "traffic_feed": {
                "last_poll": traffic_stats.get("last_poll"),
                "poll_count": traffic_stats.get("poll_count", 0),
                "incidents_fetched": traffic_stats.get("incidents_fetched", 0),
                "incidents_sent": traffic_stats.get("incidents_sent", 0),
            },
            "cot_sender": {
                "running": cot_sender.is_running,
            }
        }
        
        return metrics_data
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def stats():
    """Detailed statistics endpoint."""
    try:
        fire_stats = await fire_feed.get_stats()
        traffic_stats = await traffic_feed.get_stats()
        
        # Get lifecycle statistics
        fire_lifecycle = fire_feed._lifecycle_manager.get_tracking_stats()
        traffic_lifecycle = traffic_feed._lifecycle_manager.get_tracking_stats()
        
        return {
            "fire_feed": {
                **fire_stats,
                "lifecycle": fire_lifecycle
            },
            "traffic_feed": {
                **traffic_stats,
                "lifecycle": traffic_lifecycle
            },
            "cot_sender": {
                "running": cot_sender.is_running,
                "cot_url": settings.cot_url,
            },
            "configuration": {
                "poll_seconds": settings.poll_seconds,
                "cot_stale_minutes": settings.cot_stale_minutes,
                "fire_dataset": settings.fire_dataset,
                "traffic_dataset": settings.traffic_dataset,
            }
        }
        
    except Exception as e:
        logger.error(f"Stats collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cleanup")
async def cleanup_old_incidents(days_old: int = 7):
    """Clean up old incidents from the database."""
    try:
        deleted_count = await seen_store.cleanup_old_incidents(days_old)
        return {
            "message": f"Cleaned up {deleted_count} incidents older than {days_old} days",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Austin ATAK Integrations",
        "version": "1.0.0",
        "description": "Real-time fire and traffic incident feeds for TAK/ATAK",
        "endpoints": {
            "health": "/healthz",
            "readiness": "/ready",
            "metrics": "/metrics",
            "stats": "/stats",
            "cleanup": "/cleanup"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
        reload=False
    )
