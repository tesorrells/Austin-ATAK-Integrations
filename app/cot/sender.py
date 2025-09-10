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
        self._writer: Optional[object] = None
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
            
            # Create queue
            self._queue = asyncio.Queue()
            
            # Try to create a writer using different approaches
            writer = None
            
            # Try different writer creation patterns
            try:
                # Pattern 1: Try pytak.Writer (if it exists)
                if hasattr(pytak, 'Writer'):
                    writer = pytak.Writer(self._queue, config)
                    logger.info("Created pytak.Writer")
                else:
                    raise AttributeError("pytak.Writer not available")
            except Exception as e1:
                logger.warning(f"pytak.Writer failed: {e1}")
                try:
                    # Pattern 2: Try creating a simple writer class
                    class SimpleWriter:
                        def __init__(self, queue, config):
                            self.queue = queue
                            self.config = config
                        
                        async def start(self):
                            pass
                        
                        async def stop(self):
                            pass
                    
                    writer = SimpleWriter(self._queue, config)
                    logger.info("Created SimpleWriter")
                except Exception as e2:
                    logger.warning(f"SimpleWriter failed: {e2}")
                    # Pattern 3: Try using QueueWorker as writer
                    try:
                        writer = pytak.QueueWorker(self._queue, config)
                        logger.info("Created pytak.QueueWorker as writer")
                    except Exception as e3:
                        logger.error(f"All writer patterns failed: {e3}")
                        raise e3
            
            # Store the writer
            self._writer = writer
            
            # Create TXWorker with the writer
            try:
                self._tx = pytak.TXWorker(self._queue, config, writer)
                logger.info("Created pytak.TXWorker with writer")
            except Exception as e:
                logger.error(f"Failed to create TXWorker: {e}")
                raise
            
            # Start the writer and transmitter
            await writer.start()
            
            # Try different ways to start TXWorker
            try:
                # Method 1: Try start() method
                await self._tx.start()
                logger.info("Started TXWorker with start() method")
            except AttributeError:
                try:
                    # Method 2: Try run() method
                    await self._tx.run()
                    logger.info("Started TXWorker with run() method")
                except AttributeError:
                    try:
                        # Method 3: Try _run() method
                        await self._tx._run()
                        logger.info("Started TXWorker with _run() method")
                    except AttributeError:
                        # Method 4: Try to start it as a task
                        asyncio.create_task(self._tx.run())
                        logger.info("Started TXWorker as asyncio task")
                        # Give it a moment to start
                        await asyncio.sleep(0.1)
            
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
            if self._tx:
                # Try different ways to stop TXWorker
                try:
                    await self._tx.stop()
                except AttributeError:
                    try:
                        await self._tx.close()
                    except AttributeError:
                        try:
                            self._tx.cancel()
                        except AttributeError:
                            pass  # TXWorker might not have a stop method
            
            if self._writer:
                await self._writer.stop()
            
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
