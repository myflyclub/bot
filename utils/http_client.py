"""
HTTP Client Module for Oil Price Monitoring

This module handles HTTP requests to the oil price endpoint with content change detection,
smart polling, and efficient resource management.
"""

import requests
import hashlib
import logging
import time
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.config import Config

# Configure logging
logger = logging.getLogger(__name__)

class OilPriceHTTPClient:
    """HTTP client for oil price endpoint with content change detection"""
    
    def __init__(self, base_url: str = "https://play.myfly.club/oil-prices", 
                 base_polling_interval: int = 300):
        self.base_url = base_url
        self.session = self._create_session()
        self.last_content_hash: Optional[str] = None
        self.last_response_time: Optional[float] = None
        self.last_etag: Optional[str] = None
        self.last_modified: Optional[str] = None
        self.consecutive_no_changes = 0
        self.max_consecutive_no_changes = 3
        
        # Smart polling configuration - now uses config value
        self.base_polling_interval = base_polling_interval
        self.relaxed_polling_interval = base_polling_interval * 3  # 3x base interval for relaxed mode
        self.current_polling_interval = self.base_polling_interval

        # Circuit breaker state
        self.cb_failure_threshold = Config.CB_FAILURE_THRESHOLD
        self.cb_open_seconds = Config.CB_OPEN_SECONDS
        self.cb_half_open_probes = Config.CB_HALF_OPEN_PROBES
        self.cb_state = 'closed'  # 'closed' | 'open' | 'half_open'
        self.cb_failures = 0
        self.cb_open_until: Optional[float] = None
        self.cb_probes_remaining = 0
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic and proper headers"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        # Add retry adapter
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'User-Agent': 'OilPriceAlert/1.0 (Discord Bot)',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        return session
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content for change detection"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def _should_use_conditional_request(self) -> bool:
        """Determine if we should use conditional request headers"""
        return bool(self.last_etag or self.last_modified)
    
    def _prepare_conditional_headers(self) -> Dict[str, str]:
        """Prepare conditional request headers for efficient polling"""
        headers = {}
        
        if self.last_etag:
            headers['If-None-Match'] = self.last_etag
        
        if self.last_modified:
            headers['If-Modified-Not-Since'] = self.last_modified
        
        return headers
    
    def _before_request(self) -> Optional[Dict[str, Any]]:
        """Check circuit breaker state before making a request.
        Returns a response_info dict if the breaker is open and request should be skipped.
        """
        now = time.time()
        if self.cb_state == 'open':
            if self.cb_open_until and now >= self.cb_open_until:
                # Move to half-open and allow limited probes
                self.cb_state = 'half_open'
                self.cb_probes_remaining = max(1, self.cb_half_open_probes)
            else:
                return {'circuit_breaker': 'open', 'timestamp': now}
        if self.cb_state == 'half_open':
            if self.cb_probes_remaining <= 0:
                return {'circuit_breaker': 'open', 'timestamp': now}
            # consume a probe
            self.cb_probes_remaining -= 1
        return None

    def _record_success(self):
        # Reset failures and close breaker on success
        self.cb_failures = 0
        if self.cb_state in ('open', 'half_open'):
            logger.warning("Circuit breaker closing after successful probe")
        self.cb_state = 'closed'
        self.cb_open_until = None
        self.cb_probes_remaining = 0

    def _record_failure(self, reason: str):
        self.cb_failures += 1
        logger.debug(f"Circuit breaker failure count: {self.cb_failures} (reason: {reason})")
        if self.cb_state == 'half_open':
            # Immediate reopen on failure in half-open
            self.cb_state = 'open'
            self.cb_open_until = time.time() + self.cb_open_seconds
            logger.warning(f"Circuit breaker re-opened for {self.cb_open_seconds}s after failed probe")
            return
        if self.cb_failures >= self.cb_failure_threshold and self.cb_state == 'closed':
            self.cb_state = 'open'
            self.cb_open_until = time.time() + self.cb_open_seconds
            logger.warning(f"Circuit breaker opened for {self.cb_open_seconds}s (failures={self.cb_failures})")

    def fetch_oil_prices(self, use_conditional: bool = True) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Fetch oil prices from the endpoint with optional conditional requests
        
        Args:
            use_conditional: Whether to use conditional request headers
            
        Returns:
            Tuple of (has_changed, content, response_info)
            - has_changed: Boolean indicating if content has changed
            - content: Response content if changed, None if unchanged
            - response_info: Dictionary with response metadata
        """
        try:
            # Circuit breaker pre-check
            cb_block = self._before_request()
            if cb_block is not None:
                logger.info("Circuit breaker open, skipping HTTP request")
                return False, None, cb_block

            # Prepare request
            headers = {}
            if use_conditional and self._should_use_conditional_request():
                headers.update(self._prepare_conditional_headers())
                logger.debug("Using conditional request headers")
            
            # Make request
            start_time = time.time()
            response = self.session.get(
                self.base_url,
                headers=headers,
                timeout=30
            )
            response_time = time.time() - start_time
            
            # Store response metadata
            response_info = {
                'status_code': response.status_code,
                'response_time': response_time,
                'headers': dict(response.headers),
                'timestamp': time.time()
            }
            
            # Handle different response scenarios
            if response.status_code == 304:  # Not Modified
                logger.info("Content unchanged (HTTP 304)")
                self._update_polling_interval(False)
                self._record_success()
                return False, None, response_info
            
            elif response.status_code == 200:  # OK
                content = response.text
                content_hash = self._calculate_content_hash(content)
                
                # Check if content has actually changed
                has_changed = content_hash != self.last_content_hash
                
                if has_changed:
                    logger.info(f"Content changed detected (hash: {content_hash[:8]}...)")
                    self._update_content_metadata(content_hash, response)
                    self._update_polling_interval(True)
                else:
                    logger.info("Content unchanged (same hash)")
                    self._update_polling_interval(False)
                self._record_success()
                
                return has_changed, content, response_info
            
            else:
                logger.warning(f"Unexpected response status: {response.status_code}")
                response_info['error'] = f"HTTP {response.status_code}"
                self._record_failure(response_info['error'])
                return False, None, response_info
                
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            self._record_failure('timeout')
            return False, None, {'error': 'timeout', 'timestamp': time.time()}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            self._record_failure('connection_error')
            return False, None, {'error': f'connection_error: {e}', 'timestamp': time.time()}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            self._record_failure('request_exception')
            return False, None, {'error': f'request_error: {e}', 'timestamp': time.time()}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            self._record_failure('unexpected')
            return False, None, {'error': f'unexpected_error: {e}', 'timestamp': time.time()}
    
    def _update_content_metadata(self, content_hash: str, response: requests.Response):
        """Update stored content metadata after successful response"""
        self.last_content_hash = content_hash
        self.last_response_time = time.time()
        
        # Update ETag and Last-Modified if available
        if 'ETag' in response.headers:
            self.last_etag = response.headers['ETag']
        
        if 'Last-Modified' in response.headers:
            self.last_modified = response.headers['Last-Modified']
    
    def _update_polling_interval(self, content_changed: bool):
        """Update polling interval based on content change detection"""
        if content_changed:
            # Reset to base interval when changes detected
            self.current_polling_interval = self.base_polling_interval
            self.consecutive_no_changes = 0
            logger.debug(f"Content changed, resetting to base polling interval: {self.base_polling_interval}s")
        else:
            # Increase interval when no changes detected
            self.consecutive_no_changes += 1
            if self.consecutive_no_changes >= self.max_consecutive_no_changes:
                self.current_polling_interval = self.relaxed_polling_interval
                logger.debug(f"No changes for {self.consecutive_no_changes} requests, using relaxed interval: {self.relaxed_polling_interval}s")
    
    def get_next_poll_time(self) -> float:
        """Get the next recommended polling time"""
        if self.last_response_time is None:
            return time.time() + self.base_polling_interval
        
        return self.last_response_time + self.current_polling_interval
    
    def get_polling_status(self) -> Dict[str, Any]:
        """Get current polling status and configuration"""
        return {
            'base_interval': self.base_polling_interval,
            'relaxed_interval': self.relaxed_polling_interval,
            'current_interval': self.current_polling_interval,
            'consecutive_no_changes': self.consecutive_no_changes,
            'last_response_time': self.last_response_time,
            'last_content_hash': self.last_content_hash[:8] if self.last_content_hash else None,
            'next_poll_time': self.get_next_poll_time(),
            'base_url': self.base_url,
            'circuit_breaker': {
                'state': self.cb_state,
                'failures': self.cb_failures,
                'open_until': self.cb_open_until,
                'failure_threshold': self.cb_failure_threshold,
                'open_seconds': self.cb_open_seconds,
                'half_open_probes': self.cb_half_open_probes
            }
        }
    
    def reset_polling_state(self):
        """Reset polling state (useful for testing or manual intervention)"""
        self.last_content_hash = None
        self.last_response_time = None
        self.last_etag = None
        self.last_modified = None
        self.consecutive_no_changes = 0
        self.current_polling_interval = self.base_polling_interval
        # Reset breaker
        self.cb_state = 'closed'
        self.cb_failures = 0
        self.cb_open_until = None
        self.cb_probes_remaining = 0
        logger.info("Polling state reset")
    
    def close(self):
        """Close the HTTP session"""
        if self.session:
            self.session.close()
            logger.info("HTTP session closed")


def create_http_client(base_url: str = "https://play.myfly.club/oil-prices",
                       base_polling_interval: int = 300) -> OilPriceHTTPClient:
    """Factory function to create a new HTTP client instance"""
    return OilPriceHTTPClient(base_url, base_polling_interval)


# Example usage and testing
if __name__ == "__main__":
    # Test the HTTP client
    client = create_http_client()
    
    try:
        print("🧪 Testing Oil Price HTTP Client")
        print("=" * 40)
        
        # Test 1: Initial fetch
        print("\n📡 Test 1: Initial fetch")
        has_changed, content, response_info = client.fetch_oil_prices(use_conditional=False)
        print(f"✅ Initial fetch: {'Changed' if has_changed else 'Unchanged'}")
        print(f"   Status: {response_info.get('status_code', 'N/A')}")
        print(f"   Response time: {response_info.get('response_time', 0):.2f}s")
        
        if content:
            print(f"   Content length: {len(content)} characters")
        
        # Test 2: Conditional request (should return 304 if no changes)
        print("\n🔄 Test 2: Conditional request")
        has_changed, content, response_info = client.fetch_oil_prices(use_conditional=True)
        print(f"✅ Conditional request: {'Changed' if has_changed else 'Unchanged'}")
        print(f"   Status: {response_info.get('status_code', 'N/A')}")
        
        # Test 3: Get polling status
        print("\n📊 Test 3: Polling status")
        status = client.get_polling_status()
        print("✅ Polling status:")
        for key, value in status.items():
            if key == 'next_poll_time':
                print(f"   {key}: {time.strftime('%H:%M:%S', time.localtime(value))}")
            else:
                print(f"   {key}: {value}")
        
        print("\n🎉 HTTP client tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logging.error(f"Test error: {e}", exc_info=True)
    
    finally:
        client.close()
