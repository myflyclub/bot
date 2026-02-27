"""
Formatter for Route of the Day (ROTD) messages.

Produces a readable, styled plain-text report for channel posts.
"""

from typing import Any, Dict, List, Optional

from shared.formatting import format_int


def _format_charms(charms_a: List[Dict[str, Any]], charms_b: List[Dict[str, Any]], code_a: str, code_b: str) -> Optional[str]:
    def tidy(items: List[Dict[str, Any]]) -> str:
        out = []
        for c in items[:3]:
            title = c.get("title") or c.get("type")
            strength = c.get("strength")
            if title and strength is not None:
                out.append(f"{title} (strength {strength})")
            elif title:
                out.append(str(title))
        return ", ".join(out) if out else "-"

    if not charms_a and not charms_b:
        return None

    return "\n".join(
        [
            "🧲 Charms",
            f"{code_a}: {tidy(charms_a)}",
            f"{code_b}: {tidy(charms_b)}",
        ]
    )


def format_rotd_text(payload: Dict[str, Any]) -> str:
    a_name = payload.get("a_name", "Airport A")
    a_code = payload.get("a_code", "A")
    a_flag = payload.get("a_flag") or ""
    b_name = payload.get("b_name", "Airport B")
    b_code = payload.get("b_code", "B")
    b_flag = payload.get("b_flag") or ""

    route_line = f"{a_code} {a_flag} -> {b_code} {b_flag}".strip()

    a_city_label = " ".join(f"{a_flag} {a_name}".split()).strip()
    b_city_label = " ".join(f"{b_flag} {b_name}".split()).strip()

    pop_col = f"{a_city_label}: {format_int(payload.get('pop_a', 0))}\n{b_city_label}: {format_int(payload.get('pop_b', 0))}"
    income_col = (
        f"{a_city_label}: ${format_int(payload.get('income_ppp_a', 0))}\n"
        f"{b_city_label}: ${format_int(payload.get('income_ppp_b', 0))}"
    )

    lines: List[str] = [
        f"🎯 Random Route of the Day - {payload.get('date_str', '-')}",
        "",
        f"{a_name} ({a_code}) -> {b_name} ({b_code})",
        route_line,
        "",
        f"🌐 Flight Type: {payload.get('flight_type', '-')}",
        f"📏 Distance: {format_int(payload.get('distance_km', 0))} km",
        f"🛬 Runway Restriction: {payload.get('runway_restriction', '-')}",
        f"🤝 Relationship: {payload.get('relation_text', '-')}",
        f"🧲 Affinity: {payload.get('affinities_text', '-')}",
        f"👥 Direct Demand: {payload.get('direct_demand', '-')}",
        "",
        f"🏙️ Population\n{pop_col}",
        "",
        f"💰 Income per Capita\n{income_col}",
        "",
        ("✅ Existing direct links available" if payload.get("has_direct") else "❌ No existing direct links"),
        "",
    ]

    charms_block = _format_charms(
        payload.get("charms_a", []) or [],
        payload.get("charms_b", []) or [],
        a_code,
        b_code,
    )
    if charms_block:
        lines.append(charms_block)
        lines.append("")

    lines.append("🎫 Tickets")
    lines.append("")

    def add_itinerary(section_title: str, data: Optional[Dict[str, Any]]) -> None:
        if not data:
            return
        lines.append(section_title)
        summary = data.get("summary", "")
        if summary:
            lines.append(summary)

        for seg in data.get("segments", []):
            seg_from = seg.get("from", "-")
            seg_to = seg.get("to", "-")

            carrier = seg.get("carrier", "-")
            code = seg.get("code", "-")
            aircraft = seg.get("aircraft", "-")
            duration = seg.get("duration", "-")
            price = seg.get("price", "-")
            cabin = seg.get("cabin", "-")
            quality = seg.get("quality", "-")
            amenities = seg.get("amenities", []) or []
            amenities_text = ", ".join(amenities) if amenities else "none"
            carrier_l = str(carrier).strip().lower()
            is_local_transit = carrier_l in {"local transit", "local transfer"}
            lines.append(f"{'🚕' if is_local_transit else '🛫'} {seg_from} -> {seg_to}")
            if is_local_transit:
                # Local hops usually have no flight number/aircraft; show a cleaner transfer line.
                lines.append(f"🚌🚇 Local transfer | {duration}")
            else:
                lines.append(f"✈️ {carrier} - {code}")
                lines.append(
                    f"{aircraft} | ⏱️ {duration} | 💵 {price} ({cabin}) | ⭐ {quality} | 🖥️ {amenities_text}"
                )
        lines.append("")

    add_itinerary("🏷️ Best Deal", payload.get("best_deal"))
    add_itinerary("🔥 Best Seller", payload.get("best_seller"))

    return "\n".join(lines).strip()
