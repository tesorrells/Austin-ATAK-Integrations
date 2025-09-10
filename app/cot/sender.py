"""PyTAK CoT sender for TAK Server communication."""

import asyncio
import logging
from typing import Optional
import pytak
from app.config import settings

logger = logging.getLogger(__name__)


class CoTSender:
    """PyTAK-based CoT sender for TAK Server communication."""
    
    def __init__(self):
        self._queue: Optional[asyncio.Queue] = None
        self._tx: Optional[pytak.TXWorker] = None
        self._writer: Optional[pytak.Writer] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the CoT sender."""
        if self._running:
            return
        
        try:
            # Create PyTAK configuration
            config = {
                "COT_URL": settings.cot_url,
                "PYTAK_TLS_CLIENT_CERT": settings.pytak_tls_client_cert,
                "PYTAK_TLS_CLIENT_CERT_PASSWORD": settings.pytak_tls_client_cert_password,
                "PYTAK_TLS_CA": settings.pytak_tls_ca,
            }
            
            # Create queue and workers using PyTAK v7+ API
            self._queue = asyncio.Queue()
            
            # Try different PyTAK API patterns
            try:
                # Pattern 1: Try with Writer first
                self._writer = pytak.Writer(self._queue, config)
                self._tx = pytak.TXWorker(self._queue, config, self._writer)
                await self._writer.start()
                await self._tx.start()
            except Exception as e1:
                logger.warning(f"Writer pattern failed: {e1}")
                try:
                    # Pattern 2: Try without Writer
                    self._tx = pytak.TXWorker(self._queue, config)
                    await self._tx.start()
                except Exception as e2:
                    logger.warning(f"TXWorker without Writer failed: {e2}")
                    try:
                        # Pattern 3: Try with QueueWorker
                        self._queue_worker = pytak.QueueWorker(self._queue, config)
                        self._tx = pytak.TXWorker(self._queue, config)
                        await self._queue_worker.start()
                        await self._tx.start()
                    except Exception as e3:
                        logger.error(f"All PyTAK patterns failed: {e3}")
                        raise e3
            
            self._running = True
            logger.info("CoT sender started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start CoT sender: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the CoT sender."""
        if not self._running:
            return
        
        try:
            if hasattr(self, '_tx') and self._tx:
                await self._tx.stop()
            if hasattr(self, '_writer') and self._writer:
                await self._writer.stop()
            if hasattr(self, '_queue_worker') and self._queue_worker:
                await self._queue_worker.stop()
            
            self._running = False
            logger.info("CoT sender stopped")
            
        except Exception as e:
            logger.error(f"Error stopping CoT sender: {e}")
    
    async def send_cot(self, cot_xml: str) -> bool:
        """
        Send a CoT XML event to the TAK Server.
        
        Args:
            cot_xml: CoT XML string to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self._running or not self._queue:
            logger.error("CoT sender not running")
            return False
        
        try:
            # Put the CoT XML in the queue
            await self._queue.put(cot_xml)
            logger.debug(f"CoT event queued for transmission")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send CoT event: {e}")
            return False
    
    @property
    def is_running(self) -> bool:
        """Check if the sender is running."""
        return self._running


# Global sender instance
cot_sender = CoTSender()
