"""
Aviation info service that fetches live airport/airplane data from MyFly APIs.

No DB or static datasets are used; data is fetched from API endpoints and cached
in-memory for a short period to reduce repetitive calls.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utils.mfc_api import create_mfc_client


def _pick(payload: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    return default


@dataclass
class CachedValue:
    value: Any
    expires_at: float


class AviationInfoService:
    def __init__(self, cache_ttl_seconds: int = 300):
        self.client = create_mfc_client()
        self.cache_ttl_seconds = cache_ttl_seconds
        self._models_cache: Dict[int, CachedValue] = {}
        self._airport_cache: Dict[int, CachedValue] = {}
        self._all_airports_cache: Optional[CachedValue] = None
        self._cache_hits = 0
        self._cache_misses = 0

    def _now(self) -> float:
        return time.time()

    def _from_cache(self, cache: Dict[int, CachedValue], key: int) -> Optional[Any]:
        item = cache.get(key)
        if not item:
            self._cache_misses += 1
            return None
        if item.expires_at < self._now():
            cache.pop(key, None)
            self._cache_misses += 1
            return None
        self._cache_hits += 1
        return item.value

    def _put_cache(self, cache: Dict[int, CachedValue], key: int, value: Any) -> None:
        cache[key] = CachedValue(value=value, expires_at=self._now() + self.cache_ttl_seconds)

    def get_airport_by_id(self, airport_id: int) -> Optional[Dict[str, Any]]:
        cached = self._from_cache(self._airport_cache, airport_id)
        if isinstance(cached, dict):
            return cached

        airport = self.client.get_airport(airport_id)
        if isinstance(airport, dict) and airport:
            self._put_cache(self._airport_cache, airport_id, airport)
            return airport
        return None

    def get_all_airports(self) -> List[Dict[str, Any]]:
        if self._all_airports_cache and self._all_airports_cache.expires_at >= self._now():
            self._cache_hits += 1
            if isinstance(self._all_airports_cache.value, list):
                return self._all_airports_cache.value
        self._cache_misses += 1
        airports = self.client.get_all_airports() or []
        if isinstance(airports, list):
            self._all_airports_cache = CachedValue(
                value=airports,
                expires_at=self._now() + self.cache_ttl_seconds,
            )
            return airports
        return []

    def find_airport_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        q = (code or "").strip().upper()
        if len(q) not in (3, 4):
            return None
        airports = self.get_all_airports()
        for airport in airports:
            if not isinstance(airport, dict):
                continue
            iata = str(_pick(airport, ["iata", "iataCode"], default="")).upper()
            icao = str(_pick(airport, ["icao", "icaoCode"], default="")).upper()
            if q and q in (iata, icao):
                return airport
        return None

    def get_research_link(self, origin_id: int, dest_id: int) -> Optional[Dict[str, Any]]:
        payload = self.client.research_link(origin_id, dest_id)
        if isinstance(payload, dict) and payload:
            return payload
        return None

    def get_research_by_codes(self, origin_code: str, dest_code: str) -> Optional[Dict[str, Any]]:
        origin = self.find_airport_by_code(origin_code)
        dest = self.find_airport_by_code(dest_code)
        if not origin or not dest:
            return None
        origin_id = _pick(origin, ["id"])
        dest_id = _pick(dest, ["id"])
        if not isinstance(origin_id, int) or not isinstance(dest_id, int):
            return None
        payload = self.get_research_link(origin_id, dest_id)
        if not payload:
            return None
        payload["_origin_airport"] = origin
        payload["_dest_airport"] = dest
        return payload

    def get_airplane_models(self) -> List[Dict[str, Any]]:
        cache_key = 0
        cached = self._from_cache(self._models_cache, cache_key)
        if isinstance(cached, list):
            return cached

        models = self.client.get_airplane_models() or []
        if isinstance(models, list):
            self._put_cache(self._models_cache, cache_key, models)
            return models
        return []

    def search_models(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        models = self.get_airplane_models()
        q = query.strip().lower()
        if not q:
            return []

        scored: List[tuple] = []
        for item in models:
            if not isinstance(item, dict):
                continue
            name = str(_pick(item, ["name", "model", "airplaneModelName", "shortName", "code"], default=""))
            manufacturer = str(_pick(item, ["manufacturer", "airplaneManufacturerName", "brand"], default=""))
            haystack = f"{name} {manufacturer}".lower()
            if q not in haystack:
                continue
            # Prefer exact name starts, then smaller names, then stable fallback
            starts = 0 if name.lower().startswith(q) else 1
            score = (starts, len(name), name.lower())
            scored.append((score, item))

        scored.sort(key=lambda x: x[0])
        return [x[1] for x in scored[:limit]]

    def normalize_airport(self, airport: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": _pick(airport, ["id"]),
            "name": _pick(airport, ["name", "airportName"], default="Unknown"),
            "iata": _pick(airport, ["iata", "iataCode"], default="-"),
            "icao": _pick(airport, ["icao", "icaoCode"], default="-"),
            "city": _pick(airport, ["city", "cityName"], default="-"),
            "country": _pick(airport, ["countryName", "country", "countryCode"], default="-"),
            "country_code": _pick(airport, ["countryCode", "country_code"], default=""),
            "size": _pick(airport, ["size"], default="-"),
            "runway": _pick(airport, ["runwayLength", "runway"], default="-"),
        }

    def normalize_model(self, model: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": _pick(model, ["id", "airplaneModelId"]),
            "name": _pick(model, ["name", "model", "airplaneModelName"], default="Unknown"),
            "manufacturer": _pick(model, ["manufacturer", "airplaneManufacturerName"], default="-"),
            "family": _pick(model, ["family", "series"], default="-"),
            "quality": _pick(model, ["quality"], default="-"),
            "capacity": _pick(model, ["capacity"], default="-"),
            "range": _pick(model, ["range", "maxRange"], default="-"),
            "speed": _pick(model, ["speed", "cruiseSpeed"], default="-"),
            "runway_requirement": _pick(model, ["minimumRunway", "runwayRequirement"], default="-"),
        }

    def cache_stats(self) -> Dict[str, int]:
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "airport_cache_size": len(self._airport_cache),
            "models_cache_size": len(self._models_cache),
            "all_airports_cached": 1 if self._all_airports_cache else 0,
        }
