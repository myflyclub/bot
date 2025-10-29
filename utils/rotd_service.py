"""
Route of the Day (ROTD) service: selects a route, gathers data from MyFly endpoints,
and produces a normalized payload for formatting.

Design goals:
- Avoid Airports endpoint unless it's strictly necessary. Charms can be omitted for v1 and added later if needed.
- Use MyFly search-route and research-link as primary sources.
"""
import logging
import random
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, List

from config.config import Config
from utils.mfc_api import create_mfc_client

logger = logging.getLogger(__name__)


def _pick_flags(country_code_a: str, country_code_b: str) -> Tuple[str, str]:
    # Minimal: map ISO alpha-2 to flag emoji (naive). If missing, return empty.
    def flag(cc):
        if not cc or len(cc) != 2:
            return ""
        base = 127397
        return chr(base + ord(cc[0].upper())) + chr(base + ord(cc[1].upper()))
    return flag(country_code_a), flag(country_code_b)


class ROTDService:
    def __init__(self):
        self.client = create_mfc_client()
        self._max_airport_id: Optional[int] = None
        self._initialized = False

    def _initialize_max_id(self) -> int:
        """Fetch the maximum airport ID once at initialization."""
        if self._max_airport_id is not None:
            return self._max_airport_id
        
        logger.info("ROTD: Fetching airports to determine max ID (one-time initialization)")
        airports = self.client.get_all_airports()
        
        if airports and isinstance(airports, list):
            max_id = max(apt.get('id', 0) for apt in airports if apt.get('id'))
            self._max_airport_id = max_id
            logger.info(f"ROTD: Found {len(airports)} airports, max ID: {max_id}")
            return max_id
        else:
            logger.warning("ROTD: Failed to fetch airports, using fallback max ID of 5000")
            self._max_airport_id = 5000
            return 5000

    def _select_candidate_pair(self) -> Optional[Tuple[int, int]]:
        """
        Select a random valid airport pair by sampling random IDs and validating.
        Returns a tuple of (origin_id, dest_id) or None if selection fails.
        
        Strategy:
        - Initialize max airport ID once from /airports endpoint
        - Generate random IDs within range [1, max_id]
        - Validate both airports exist and meet size requirements
        - Validate the pair has available routes via search-route
        - Retry up to max_attempts if validation fails
        """
        min_size = Config.ROTD_MIN_AIRPORT_SIZE
        max_attempts = 20
        
        # Initialize max ID if needed (one-time operation)
        max_id = self._initialize_max_id()
        
        logger.info(f"ROTD: Searching for random airport pair (ID range: 1-{max_id}, min_size={min_size})")
        
        for attempt in range(max_attempts):
            # Generate two different random IDs
            origin_id = random.randint(1, max_id)
            dest_id = random.randint(1, max_id)
            
            if origin_id == dest_id:
                continue
            
            # Validate both airports exist and meet size requirements
            try:
                origin_airport = self.client.get_airport(origin_id)
                if not origin_airport:
                    logger.debug(f"ROTD attempt {attempt+1}: Airport {origin_id} not found")
                    continue
                
                origin_size = origin_airport.get('size', 0)
                if origin_size < min_size:
                    logger.debug(f"ROTD attempt {attempt+1}: Airport {origin_id} size {origin_size} < {min_size}")
                    continue
                
                dest_airport = self.client.get_airport(dest_id)
                if not dest_airport:
                    logger.debug(f"ROTD attempt {attempt+1}: Airport {dest_id} not found")
                    continue
                
                dest_size = dest_airport.get('size', 0)
                if dest_size < min_size:
                    logger.debug(f"ROTD attempt {attempt+1}: Airport {dest_id} size {dest_size} < {min_size}")
                    continue
                
                # Validate routes exist
                route = self.client.search_route(origin_id, dest_id)
                if route and isinstance(route, list) and len(route) > 0:
                    origin_iata = origin_airport.get('iata', '?')
                    dest_iata = dest_airport.get('iata', '?')
                    logger.info(f"ROTD: Found valid pair after {attempt+1} attempts: {origin_id} ({origin_iata}) -> {dest_id} ({dest_iata})")
                    return (origin_id, dest_id)
                else:
                    logger.debug(f"ROTD attempt {attempt+1}: No routes for {origin_id}->{dest_id}")
            
            except Exception as e:
                logger.debug(f"ROTD attempt {attempt+1}: Validation error for {origin_id}->{dest_id}: {e}")
                continue
        
        logger.warning(f"ROTD: Could not find valid random airport pair after {max_attempts} attempts")
        return None

    def generate_payload(self, origin_id: int, dest_id: int) -> Optional[Dict[str, Any]]:
        """Fetch data from MyFly endpoints and construct normalized payload.

        This method relies only on search-route and research-link, avoiding airports endpoint.
        """
        route = self.client.search_route(origin_id, dest_id)
        research = self.client.research_link(origin_id, dest_id)
        if not route or not research:
            logger.warning("ROTD: Missing data route=%s research=%s", bool(route), bool(research))
            return None

        # Helper: safe extract with multiple candidate keys
        def _pick(d: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
            if not isinstance(d, dict):
                return default
            for k in keys:
                if k in d and d[k] not in (None, ""):
                    return d[k]
            return default

        # Extract from research-link which uses fromAirport* and toAirport* prefixes
        a_name = research.get('fromAirportText', '').split('(')[0] if research.get('fromAirportText') else f"Airport {origin_id}"
        a_code = research.get('fromAirportIata', '—')
        a_country = research.get('fromAirportCountryCode', '')
        
        b_name = research.get('toAirportText', '').split('(')[0] if research.get('toAirportText') else f"Airport {dest_id}"
        b_code = research.get('toAirportIata', '—')
        b_country = research.get('toAirportCountryCode', '')

        flag_a, flag_b = _pick_flags(a_country, b_country)

        # Distance/runway/population/income from research
        distance_km = research.get('distance', 0)
        runway_restriction = "—"  # Not in research payload
        pop_a = research.get('fromAirportPopulation', 0)
        pop_b = research.get('toAirportPopulation', 0)
        income_ppp_a = research.get('fromAirportIncome', 0)
        income_ppp_b = research.get('toAirportIncome', 0)

        # Relationship and affinities
        mutual_rel = research.get('mutualRelationship', 0)
        if mutual_rel >= 2:
            relation_text = f"{mutual_rel} (Excellent)"
        elif mutual_rel >= 1:
            relation_text = f"{mutual_rel} (Good)"
        elif mutual_rel <= -1:
            relation_text = f"{mutual_rel} (Poor)"
        else:
            relation_text = f"{mutual_rel} (Neutral)"
        
        affinities_text = research.get('affinity', '—')
        
        flight_type = research.get('flightType', 'Domestic')
        
        # Direct demand from research
        dd = research.get('directDemand', {})
        if isinstance(dd, dict):
            econ = dd.get('economy', 0)
            biz = dd.get('business', 0)
            fst = dd.get('first')
            fst_str = f"{fst}" if fst is not None else "–"
            direct_demand = f"{econ} / {biz} / {fst_str}"
        else:
            direct_demand = "—"
        # Detect direct presence - check if any route has BEST_DEAL and no connections
        has_direct = False
        if isinstance(route, list):
            for itin in route:
                if isinstance(itin, dict):
                    route_segments = itin.get('route', [])
                    if len(route_segments) == 1:
                        has_direct = True
                        break

        # Charms: Avoid airport endpoint; leave empty lists for now
        charms_a = []
        charms_b = []

        # Itineraries: map from route list structure
        def map_itin(itin: Dict[str, Any]) -> Dict[str, Any]:
            # Route segments are in 'route' array
            raw_segments = itin.get('route', [])
            
            segs = []
            for s in raw_segments:
                from_code = s.get('fromAirportIata', '—')
                to_code = s.get('toAirportIata', '—')
                carrier = s.get('airlineName', '—')
                flight_code = s.get('flightCode', '—')
                aircraft = s.get('airplaneModelName', '—')
                duration_mins = s.get('duration', 0)
                # Convert minutes to hours and minutes
                if duration_mins:
                    hours = duration_mins // 60
                    mins = duration_mins % 60
                    if hours > 0:
                        duration = f"{hours} hour{'s' if hours > 1 else ''}" + (f" {mins} minutes" if mins > 0 else "")
                    else:
                        duration = f"{mins} minutes"
                else:
                    duration = '—'
                price = s.get('price', '—')
                cabin = s.get('linkClass', '—').title()
                quality = s.get('computedQuality', '—')
                features = s.get('features', [])
                # Map features to friendly names
                amenity_map = {
                    'IFE': 'IFE',
                    'POWER_OUTLET': 'power outlet',
                    'WIFI': 'wifi',
                    'BEVERAGE_SERVICE': 'beverage service',
                    'HOT_MEAL_SERVICE': 'hot meal service',
                    'COLD_MEAL_SERVICE': 'cold meal service'
                }
                amenities = [amenity_map.get(f, f.lower().replace('_', ' ')) for f in features]
                
                segs.append({
                    'from': from_code,
                    'to': to_code,
                    'carrier': carrier,
                    'code': flight_code,
                    'aircraft': aircraft,
                    'duration': duration,
                    'price': f"${price}" if isinstance(price, (int, float)) else price,
                    'cabin': cabin,
                    'quality': quality,
                    'amenities': amenities,
                })
            
            # Build summary from segments
            if segs:
                path = " - ".join([segs[0]['from']] + [seg['to'] for seg in segs])
                # Total price is sum of segment prices
                try:
                    total_price = sum(int(s.get('price', 0)) if isinstance(s.get('price'), (int, float)) else 0 for s in raw_segments)
                    cabin = segs[0]['cabin'] if segs else 'Economy'
                    summary = f"{path} — ${total_price} ({cabin})"
                except:
                    summary = path
            else:
                summary = ""
            
            return {'summary': summary, 'segments': segs}

        best_deal = None
        best_seller = None
        if isinstance(route, list):
            # Find BEST_DEAL and BEST_SELLER from remarks
            for itin in route:
                if isinstance(itin, dict):
                    remarks = itin.get('remarks', [])
                    if 'BEST_DEAL' in remarks and not best_deal:
                        best_deal = map_itin(itin)
                    elif 'BEST_SELLER' in remarks and not best_seller:
                        best_seller = map_itin(itin)
            
            # Fallback: use first two if no remarks found
            if not best_deal and route:
                best_deal = map_itin(route[0])
            if not best_seller and len(route) > 1:
                best_seller = map_itin(route[1])

        # Portable date string: e.g., '26 October 2025'
        now = datetime.now(timezone.utc)
        date_str = f"{now.day} {now.strftime('%B %Y')}"

        payload = {
            'date_str': date_str,
            'a_name': a_name,
            'a_code': a_code,
            'a_flag': flag_a,
            'b_name': b_name,
            'b_code': b_code,
            'b_flag': flag_b,
            'distance_km': int(distance_km) if isinstance(distance_km, (int, float)) else 0,
            'runway_restriction': runway_restriction,
            'pop_a': int(pop_a) if isinstance(pop_a, (int, float)) else 0,
            'pop_b': int(pop_b) if isinstance(pop_b, (int, float)) else 0,
            'income_ppp_a': int(income_ppp_a) if isinstance(income_ppp_a, (int, float)) else 0,
            'income_ppp_b': int(income_ppp_b) if isinstance(income_ppp_b, (int, float)) else 0,
            'relation_text': relation_text,
            'affinities_text': affinities_text,
            'flight_type': flight_type,
            'direct_demand': direct_demand,
            'has_direct': has_direct,
            'charms_a': charms_a,
            'charms_b': charms_b,
            'best_deal': best_deal,
            'best_seller': best_seller,
        }
        return payload
