"""
MyFly Club API client for Route of the Day feature.

This client uses a requests.Session with retry and a simple circuit breaker, aligned with
project resilience patterns. It avoids the Airports endpoint unless explicitly needed.
"""

import time
import logging
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.config import Config

logger = logging.getLogger(__name__)


class SimpleCircuitBreaker:
    def __init__(self, failure_threshold: int, open_seconds: int, half_open_probes: int):
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self.half_open_probes = half_open_probes
        self.state = 'closed'
        self.failures = 0
        self.open_until: Optional[float] = None
        self.probes_remaining = 0

    def before_request(self) -> bool:
        now = time.time()
        if self.state == 'open':
            if self.open_until and now >= self.open_until:
                self.state = 'half_open'
                self.probes_remaining = max(1, self.half_open_probes)
            else:
                return False
        if self.state == 'half_open':
            if self.probes_remaining <= 0:
                return False
            self.probes_remaining -= 1
        return True

    def record_success(self):
        self.failures = 0
        self.state = 'closed'
        self.open_until = None
        self.probes_remaining = 0

    def record_failure(self):
        if self.state == 'half_open':
            self.state = 'open'
            self.open_until = time.time() + self.open_seconds
            return
        self.failures += 1
        if self.failures >= self.failure_threshold and self.state == 'closed':
            self.state = 'open'
            self.open_until = time.time() + self.open_seconds


def _create_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        'User-Agent': 'MfcMultitaskBot/1.0 (ROTD)',
        'Accept': 'application/json'
    })
    return session


class MyFlyApiClient:
    BASE = "https://play.myfly.club"

    def __init__(self):
        self.session = _create_session()
        self.breaker = SimpleCircuitBreaker(
            failure_threshold=Config.CB_FAILURE_THRESHOLD,
            open_seconds=Config.CB_OPEN_SECONDS,
            half_open_probes=Config.CB_HALF_OPEN_PROBES,
        )

    def _get(self, path: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        if not self.breaker.before_request():
            logger.warning("ROTD breaker open; skipping request %s", path)
            return None
        url = f"{self.BASE}{path}"
        try:
            resp = self.session.get(url, timeout=timeout)
            if resp.status_code == 200:
                self.breaker.record_success()
                return resp.json()
            else:
                logger.warning("GET %s -> %s", url, resp.status_code)
                self.breaker.record_failure()
                return None
        except requests.RequestException as e:
            logger.error("Request error %s: %s", url, e)
            self.breaker.record_failure()
            return None

    def search_route(self, origin_id: int, dest_id: int) -> Optional[Dict[str, Any]]:
        return self._get(f"/search-route/{origin_id}/{dest_id}")

    def research_link(self, origin_id: int, dest_id: int) -> Optional[Dict[str, Any]]:
        return self._get(f"/research-link/{origin_id}/{dest_id}")

    def get_airport(self, airport_id: int) -> Optional[Dict[str, Any]]:
        """Fetch airport details by ID. Used for random selection."""
        return self._get(f"/airports/{airport_id}")

    def get_all_airports(self) -> Optional[list]:
        """Fetch the complete list of airports. Returns list of airport dicts."""
        result = self._get("/airports")
        if result and isinstance(result, list):
            return result
        return None

    # Intentionally omit airports endpoint unless explicitly needed for charms


def create_mfc_client() -> MyFlyApiClient:
    return MyFlyApiClient()
