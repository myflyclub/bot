"""
MyFly Club API client for Route of the Day feature.

This client uses a requests.Session with retry and a simple circuit breaker, aligned with
project resilience patterns. It avoids the Airports endpoint unless explicitly needed.
"""

import time
import logging
from typing import Any, Dict, List, Optional

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
    def __init__(self):
        self.session = _create_session()
        self.base_url = Config.MFC_BASE_URL
        self.search_route_path_template = Config.MFC_SEARCH_ROUTE_PATH_TEMPLATE
        self.research_link_path_template = Config.MFC_RESEARCH_LINK_PATH_TEMPLATE
        self.airport_by_id_path_template = Config.MFC_AIRPORT_BY_ID_PATH_TEMPLATE
        self.airports_path = Config.MFC_AIRPORTS_PATH
        self.airports_static_path = Config.MFC_AIRPORTS_STATIC_PATH
        self.airport_detail_path_template = Config.MFC_AIRPORT_DETAIL_PATH_TEMPLATE
        self.airport_detail_static_path_template = Config.MFC_AIRPORT_DETAIL_STATIC_PATH_TEMPLATE
        self.airplane_models_path = Config.MFC_AIRPLANE_MODELS_PATH
        self.breaker = SimpleCircuitBreaker(
            failure_threshold=Config.CB_FAILURE_THRESHOLD,
            open_seconds=Config.CB_OPEN_SECONDS,
            half_open_probes=Config.CB_HALF_OPEN_PROBES,
        )

    def _get(self, path: str, timeout: int = 30) -> Optional[Any]:
        if not self.breaker.before_request():
            logger.warning("ROTD breaker open; skipping request %s", path)
            return None
        url = f"{self.base_url}{path}"
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
        return self._get(self.search_route_path_template.format(origin_id=origin_id, dest_id=dest_id))

    def research_link(self, origin_id: int, dest_id: int) -> Optional[Dict[str, Any]]:
        return self._get(self.research_link_path_template.format(origin_id=origin_id, dest_id=dest_id))

    @staticmethod
    def _derive_runway_length(payload: Dict[str, Any]) -> Optional[int]:
        runway_length = payload.get("runwayLength")
        if isinstance(runway_length, (int, float)):
            return int(runway_length)

        runways = payload.get("runways")
        if not isinstance(runways, list):
            return None

        lengths: List[int] = []
        for runway in runways:
            if not isinstance(runway, dict):
                continue
            length = runway.get("length")
            if isinstance(length, (int, float)):
                lengths.append(int(length))
        return max(lengths) if lengths else None

    @classmethod
    def _merge_airport_payload(
        cls,
        airport_id: int,
        static_payload: Optional[Dict[str, Any]],
        dynamic_payload: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(static_payload, dict) and not isinstance(dynamic_payload, dict):
            return None

        merged: Dict[str, Any] = {}
        if isinstance(static_payload, dict):
            merged.update(static_payload)
        if isinstance(dynamic_payload, dict):
            merged.update(dynamic_payload)
        merged.setdefault("id", airport_id)

        runway_length = cls._derive_runway_length(merged)
        if runway_length is not None:
            merged["runwayLength"] = runway_length
        return merged

    def get_airport_detail(self, airport_id: int) -> Optional[Dict[str, Any]]:
        return self._get(self.airport_detail_path_template.format(airport_id=airport_id))

    def get_airport_detail_static(self, airport_id: int) -> Optional[Dict[str, Any]]:
        return self._get(self.airport_detail_static_path_template.format(airport_id=airport_id))

    def get_airport(self, airport_id: int) -> Optional[Dict[str, Any]]:
        """Fetch merged airport details by ID from detail-static + detail endpoints."""
        static_payload = self.get_airport_detail_static(airport_id)
        dynamic_payload = self.get_airport_detail(airport_id)
        merged = self._merge_airport_payload(airport_id, static_payload, dynamic_payload)
        if isinstance(merged, dict):
            return merged

        # Legacy fallback for older environments.
        legacy_payload = self._get(self.airport_by_id_path_template.format(airport_id=airport_id))
        if isinstance(legacy_payload, dict) and legacy_payload:
            runway_length = self._derive_runway_length(legacy_payload)
            if runway_length is not None:
                legacy_payload["runwayLength"] = runway_length
            return legacy_payload
        return None

    @staticmethod
    def _flatten_airports_static(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        features = payload.get("features")
        if not isinstance(features, list):
            return []

        airports: List[Dict[str, Any]] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties")
            if not isinstance(properties, dict):
                continue

            normalized = dict(properties)
            if "id" not in normalized and isinstance(feature.get("id"), int):
                normalized["id"] = feature.get("id")

            geometry = feature.get("geometry")
            if isinstance(geometry, dict):
                coordinates = geometry.get("coordinates")
                if isinstance(coordinates, list) and len(coordinates) >= 2:
                    lon, lat = coordinates[0], coordinates[1]
                    if isinstance(lat, (int, float)):
                        normalized["latitude"] = lat
                    if isinstance(lon, (int, float)):
                        normalized["longitude"] = lon

            runway_length = MyFlyApiClient._derive_runway_length(normalized)
            if runway_length is not None:
                normalized["runwayLength"] = runway_length

            airports.append(normalized)
        return airports

    def get_all_airports(self) -> Optional[list]:
        """Fetch airport catalog with static endpoint as primary source."""
        result = self._get(self.airports_static_path)
        if isinstance(result, dict):
            flattened = self._flatten_airports_static(result)
            if flattened:
                return flattened

        # Legacy fallback (older API returned a list directly).
        legacy_result = self._get(self.airports_path)
        if legacy_result and isinstance(legacy_result, list):
            return legacy_result
        return None

    def get_airplane_models(self) -> Optional[list]:
        """Fetch airplane models from the global endpoint (no auth required)."""
        result = self._get(self.airplane_models_path)
        if isinstance(result, list):
            return result
        # Defensive compatibility in case model catalog shape changes again.
        if isinstance(result, dict):
            for key in ("models", "airplaneModels", "items", "data"):
                value = result.get(key)
                if isinstance(value, list):
                    return value
        return None

    # Intentionally omit airports endpoint unless explicitly needed for charms


def create_mfc_client() -> MyFlyApiClient:
    return MyFlyApiClient()
