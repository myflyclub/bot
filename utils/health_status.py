"""
Health and metrics aggregation utilities for the Oil Price Alert bot.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class HealthSnapshot:
    timestamp: float
    uptime: float
    monitoring_active: bool
    current_price: Optional[float]
    current_cycle: Optional[int]
    last_http_response_time: Optional[float]
    next_poll_time: Optional[float]
    circuit_breaker: Dict[str, Any]
    total_updates_processed: int
    total_changes_detected: int
    guild_count: int
    websocket_latency: Optional[float]


class HealthStatusAggregator:
    def __init__(self):
        self.process_start_time = time.time()

    def snapshot(self, price_monitor, bot) -> HealthSnapshot:
        now = time.time()

        http_status = price_monitor.http_client.get_polling_status() if price_monitor else {}
        breaker = http_status.get('circuit_breaker', {})

        current_price = price_monitor.get_current_price() if price_monitor else None
        return HealthSnapshot(
            timestamp=now,
            uptime=now - self.process_start_time,
            monitoring_active=bool(price_monitor and price_monitor.monitoring_active),
            current_price=current_price.price if current_price else None,
            current_cycle=current_price.cycle if current_price else None,
            last_http_response_time=http_status.get('last_response_time'),
            next_poll_time=http_status.get('next_poll_time'),
            circuit_breaker={
                'state': breaker.get('state'),
                'failures': breaker.get('failures'),
                'open_until': breaker.get('open_until'),
                'failure_threshold': breaker.get('failure_threshold'),
                'open_seconds': breaker.get('open_seconds'),
                'half_open_probes': breaker.get('half_open_probes'),
            },
            total_updates_processed=price_monitor.total_updates_processed if price_monitor else 0,
            total_changes_detected=price_monitor.total_changes_detected if price_monitor else 0,
            guild_count=len(bot.guilds) if bot and hasattr(bot, 'guilds') and bot.guilds else 0,
            websocket_latency=float(bot.latency) if bot and hasattr(bot, 'latency') and bot.latency is not None else None,
        )


