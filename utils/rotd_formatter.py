"""
Formatter for Route of the Day (ROTD) messages.

Produces a compact text report aligned with the example format.
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


def _format_charms(charms_a: List[Dict[str, Any]], charms_b: List[Dict[str, Any]], code_a: str, code_b: str) -> str:
    def tidy(items):
        out = []
        for c in items[:3]:  # cap to 2-3 items to keep message short
            title = c.get('title') or c.get('type')
            strength = c.get('strength')
            if title and strength is not None:
                out.append(f"{title} (strength {strength})")
            elif title:
                out.append(str(title))
        return ", ".join(out) if out else "—"

    a_line = f"- {code_a}: {tidy(charms_a)}"
    b_line = f"- {code_b}: {tidy(charms_b)}"
    return f"Charms (from Airports features):\n{a_line}\n{b_line}\n"


def format_rotd_text(payload: Dict[str, Any]) -> str:
    """
    payload contract (required keys):
    - date_str: e.g., '26 October 2025'
    - a_name, a_code, a_flag
    - b_name, b_code, b_flag
    - distance_km (int)
    - runway_restriction (str)
    - pop_a, pop_b (int)
    - income_ppp_a, income_ppp_b (int)
    - relation_text (str)
    - affinities_text (str)
    - flight_type (str)
    - direct_demand (str)
    - charms_a: List[Charm]
    - charms_b: List[Charm]
    - best_deal: Dict or None (summary + segments)
    - best_seller: Dict or None
    """
    lines = []
    lines.append(f"Random Route of the Day: {payload['date_str']}")
    lines.append("")
    # Build title line without extra spaces if flags are missing
    a_flag = payload.get('a_flag') or ""
    b_flag = payload.get('b_flag') or ""
    a_flag_part = f" {a_flag}" if a_flag else ""
    b_flag_part = f" {b_flag}" if b_flag else ""
    lines.append(f"{payload['a_name']} ({payload['a_code']}){a_flag_part} - {payload['b_name']} ({payload['b_code']}){b_flag_part}")
    lines.append("")
    lines.append(f"Distance (direct): {payload['distance_km']:,} km")
    lines.append(f"Runway Restriction: {payload['runway_restriction']}")
    lines.append(f"Population: {payload['pop_a']:,} / {payload['pop_b']:,}")
    lines.append(f"Income per Capita, PPP: ${payload['income_ppp_a']:,} / ${payload['income_ppp_b']:,}")
    lines.append(f"Relationship between Countries: {payload['relation_text']}")
    lines.append(f"Affinities: {payload['affinities_text']}")
    lines.append(f"Flight Type: {payload['flight_type']}")
    lines.append(f"Direct Demand: {payload['direct_demand']}")
    lines.append("")

    # Charms section
    charms_a = payload.get('charms_a', []) or []
    charms_b = payload.get('charms_b', []) or []
    if charms_a or charms_b:
        charms_block = _format_charms(charms_a, charms_b, payload['a_code'], payload['b_code'])
        lines.append(charms_block.strip())
        lines.append("")

    if payload.get('has_direct'):
        lines.append("Existing direct links available")
    else:
        lines.append("No existing direct links")
    lines.append("")

    lines.append("Tickets")
    lines.append("")

    def add_itinerary(section_title: str, data: Optional[Dict[str, Any]]):
        if not data:
            return
        lines.append(section_title)
        lines.append(data.get('summary', ''))
        for seg in data.get('segments', []):
            lines.append(f"🛫 {seg['from']} - {seg['to']} 🛫")
            amenities_str = ", ".join(seg.get('amenities', [])) if seg.get('amenities') else ""
            qual_str = f" with {seg['quality']} quality including {amenities_str}" if amenities_str else f" with {seg['quality']} quality"
            lines.append(f"{seg['carrier']} - {seg['code']} | {seg['aircraft']} | Duration: {seg['duration']} | {seg['price']} ({seg['cabin']}){qual_str}")
        lines.append("")

    add_itinerary("Best Deal", payload.get('best_deal'))
    add_itinerary("Best Seller", payload.get('best_seller'))

    return "\n".join(lines).strip()
