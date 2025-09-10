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
                    # Pattern 2: Try creating a simple writer class that actually sends data
                    class SimpleWriter:
                        def __init__(self, queue, config):
                            self.queue = queue
                            self.config = config
                            self.socket = None
                            self.running = False
                        
                        async def start(self):
                            """Start the writer and establish connection."""
                            try:
                                import socket
                                import asyncio
                                
                                # Parse the COT_URL
                                cot_url = self.config.get("COT_URL", "")
                                if not cot_url:
                                    raise ValueError("COT_URL not configured")
                                
                                # Parse URL (e.g., tcp://tak-server:8087)
                                if cot_url.startswith("tcp://"):
                                    host_port = cot_url[6:]  # Remove "tcp://"
                                    if ":" in host_port:
                                        host, port = host_port.split(":", 1)
                                        port = int(port)
                                    else:
                                        host = host_port
                                        port = 8087  # Default port
                                else:
                                    raise ValueError(f"Unsupported COT_URL format: {cot_url}")
                                
                                # Create socket connection
                                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                self.socket.settimeout(10)
                                self.socket.connect((host, port))
                                logger.info(f"Connected to TAK server at {host}:{port}")
                                
                                self.running = True
                                
                                # Start background task to process queue
                                asyncio.create_task(self._process_queue())
                                
                            except Exception as e:
                                logger.error(f"Failed to start SimpleWriter: {e}")
                                raise
                        
                        async def _process_queue(self):
                            """Process the queue and send CoT events."""
                            while self.running:
                                try:
                                    # Get CoT event from queue (with timeout)
                                    cot_xml = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                                    
                                    if self.socket and cot_xml:
                                        # Send the CoT XML
                                        self.socket.send(cot_xml.encode('utf-8'))
                                        logger.info(f"Sent CoT event to TAK server ({len(cot_xml)} chars)")
                                        
                                except asyncio.TimeoutError:
                                    continue  # No events in queue, keep waiting
                                except Exception as e:
                                    logger.error(f"Error processing CoT queue: {e}")
                                    break
                        
                        async def stop(self):
                            """Stop the writer and close connection."""
                            self.running = False
                            if self.socket:
                                try:
                                    self.socket.close()
                                    logger.info("Closed connection to TAK server")
                                except:
                                    pass
                                self.socket = None
                    
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
            
            # Start TXWorker as a background task to avoid blocking startup
            try:
                # Try to start TXWorker as a background task
                self._tx_task = asyncio.create_task(self._tx.run())
                logger.info("Started TXWorker as background task")
                # Give it a moment to start
                await asyncio.sleep(0.1)
                
                # Check if the task is still running
                if self._tx_task.done():
                    logger.error("TXWorker task completed immediately - this indicates an error")
                    try:
                        result = self._tx_task.result()
                        logger.error(f"TXWorker task result: {result}")
                    except Exception as e:
                        logger.error(f"TXWorker task exception: {e}")
                else:
                    logger.info("TXWorker task is running successfully")
                    
            except Exception as e:
                logger.warning(f"Failed to start TXWorker as task: {e}")
                # Fallback: try other methods
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
                            logger.error("All TXWorker start methods failed")
                            raise
            
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
        if not self._running:
            logger.error("CoT sender not running")
            return False
        
        if not self._queue:
            logger.error("CoT queue not initialized")
            return False
        
        try:
            # Put the CoT XML in the queue
            await self._queue.put(cot_xml)
            logger.info(f"CoT event queued for transmission (length: {len(cot_xml)} chars)")
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
