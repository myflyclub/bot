"""
Oil Price Monitor Module

This module integrates the price parser and HTTP client to create a complete
oil price monitoring system with change detection and local storage.
"""

import json
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from .price_parser import OilPriceParser, OilPriceData
from .http_client import OilPriceHTTPClient

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class PriceChangeEvent:
    """Data class for price change events"""
    timestamp: float
    old_price: Optional[float]
    new_price: float
    old_cycle: Optional[int]
    new_cycle: int
    price_change: float
    price_change_percent: float
    event_type: str  # 'initial', 'update', 'reset'

class OilPriceMonitor:
    """Main monitoring system for oil prices (v2: in-memory only)"""
    
    def __init__(self, 
                 base_url: str = "https://play.myfly.club/oil-prices",
                 change_threshold: float = 0.01,  # 1 cent threshold
                 polling_interval: int = 300):  # Default 5 minutes
        self.parser = OilPriceParser()
        self.http_client = OilPriceHTTPClient(base_url, polling_interval)
        self.change_threshold = change_threshold
        
        # Current state (in-memory only)
        self.current_price: Optional[OilPriceData] = None
        self.last_change_event: Optional[PriceChangeEvent] = None
        self.monitoring_active = False
        
        # Statistics tracking (in-memory only)
        self.total_updates_processed = 0
        self.total_changes_detected = 0
        self.session_start_time = time.time()
        
        logger.info("Oil price monitor initialized (v2: in-memory only)")
    
    def _update_statistics(self, event_type: str = 'update'):
        """Update in-memory statistics"""
        self.total_updates_processed += 1
        
        if event_type in ['initial', 'update']:
            self.total_changes_detected += 1
        
        logger.debug(f"Statistics updated: {self.total_updates_processed} processed, {self.total_changes_detected} changes")
    
    def _detect_price_change(self, new_price_data: OilPriceData) -> Optional[PriceChangeEvent]:
        """Detect if there's a meaningful price change"""
        if self.current_price is None:
            # First price check
            event = PriceChangeEvent(
                timestamp=time.time(),
                old_price=None,
                new_price=new_price_data.price,
                old_cycle=None,
                new_cycle=new_price_data.cycle,
                price_change=0.0,
                price_change_percent=0.0,
                event_type='initial'
            )
            logger.info(f"Initial price detected: ${new_price_data.price:.2f} (Cycle: {new_price_data.cycle})")
            return event
        
        # Check if cycle has changed (indicating new data)
        if new_price_data.cycle > self.current_price.cycle:
            price_change = new_price_data.price - self.current_price.price
            price_change_percent = (price_change / self.current_price.price) * 100
            
            # Check if change exceeds threshold
            if abs(price_change) >= self.change_threshold:
                event = PriceChangeEvent(
                    timestamp=time.time(),
                    old_price=self.current_price.price,
                    new_price=new_price_data.price,
                    old_cycle=self.current_price.cycle,
                    new_cycle=new_price_data.cycle,
                    price_change=price_change,
                    price_change_percent=price_change_percent,
                    event_type='update'
                )
                
                logger.info(f"Price change detected: ${self.current_price.price:.2f} → ${new_price_data.price:.2f} "
                          f"(Change: ${price_change:+.2f}, {price_change_percent:+.2f}%)")
                return event
            else:
                logger.debug(f"Price change below threshold: ${price_change:.2f} (threshold: ${self.change_threshold:.2f})")
                return None
        else:
            logger.debug(f"No new cycle data (current: {self.current_price.cycle}, new: {new_price_data.cycle})")
            return None
    
    def check_for_updates(self) -> Optional[PriceChangeEvent]:
        """
        Check for oil price updates
        
        Returns:
            PriceChangeEvent if a change was detected, None otherwise
        """
        try:
            # Fetch latest prices from endpoint
            has_changed, content, response_info = self.http_client.fetch_oil_prices()

            # Handle circuit breaker Open state (skip without errors)
            if response_info and isinstance(response_info, dict) and response_info.get('circuit_breaker') == 'open':
                logger.warning("HTTP circuit breaker is open; skipping update check this cycle")
                return None
            
            if not has_changed:
                logger.debug("No content changes detected")
                return None
            
            if not content:
                logger.warning("No content received despite change detection")
                return None
            
            # Parse the new content
            new_price_data = self.parser.get_latest_price(content)
            
            # Detect price changes
            change_event = self._detect_price_change(new_price_data)
            
            if change_event:
                # Update current price
                self.current_price = new_price_data
                self.last_change_event = change_event
                
                # Update statistics
                self._update_statistics(change_event.event_type)
                
                logger.info(f"Price update processed: {change_event.event_type}")
                return change_event
            else:
                # Even if no meaningful change, update current price if cycle is newer
                if (self.current_price is None or 
                    new_price_data.cycle > self.current_price.cycle):
                    self.current_price = new_price_data
                    self._update_statistics('minor_update')
                    logger.debug(f"Price updated without significant change: ${new_price_data.price:.2f}")
                
                return None
                
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return None
    
    def get_current_price(self) -> Optional[OilPriceData]:
        """Get the current oil price"""
        return self.current_price
    
    def get_price_change_summary(self) -> Dict[str, Any]:
        """Get a summary of current price status and session statistics"""
        current_time = time.time()
        session_duration = current_time - self.session_start_time
        
        summary = {
            'current_price': self.current_price.price if self.current_price else None,
            'current_cycle': self.current_price.cycle if self.current_price else None,
            'last_update': self.last_change_event.timestamp if self.last_change_event else None,
            'session_stats': {
                'session_duration': session_duration,
                'total_updates_processed': self.total_updates_processed,
                'total_changes_detected': self.total_changes_detected,
                'session_start_time': self.session_start_time,
                'monitoring_active': self.monitoring_active
            },
            'last_change_event': {
                'event_type': self.last_change_event.event_type if self.last_change_event else None,
                'price_change': self.last_change_event.price_change if self.last_change_event else None,
                'price_change_percent': self.last_change_event.price_change_percent if self.last_change_event else None,
                'old_price': self.last_change_event.old_price if self.last_change_event else None,
                'new_price': self.last_change_event.new_price if self.last_change_event else None
            } if self.last_change_event else None
        }
        
        return summary
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get the current monitoring status"""
        http_status = self.http_client.get_polling_status()
        current_time = time.time()
        session_duration = current_time - self.session_start_time
        
        status = {
            'monitoring_active': self.monitoring_active,
            'current_price': {
                'price': self.current_price.price if self.current_price else None,
                'cycle': self.current_price.cycle if self.current_price else None,
                'timestamp': self.current_price.timestamp if self.current_price else None
            },
            'last_change_event': asdict(self.last_change_event) if self.last_change_event else None,
            'session_stats': {
                'session_duration': session_duration,
                'total_updates_processed': self.total_updates_processed,
                'total_changes_detected': self.total_changes_detected,
                'session_start_time': self.session_start_time
            },
            'change_threshold': self.change_threshold,
            'http_client_status': http_status
        }
        
        return status
    
    def start_monitoring(self):
        """Start the monitoring system"""
        if self.monitoring_active:
            logger.warning("Monitoring is already active")
            return
        
        self.monitoring_active = True
        logger.info("Oil price monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring system"""
        if not self.monitoring_active:
            logger.warning("Monitoring is not active")
            return
        
        self.monitoring_active = False
        logger.info("Oil price monitoring stopped")
    
    def reset_monitoring_state(self):
        """Reset the monitoring state (useful for testing)"""
        self.current_price = None
        self.last_change_event = None
        self.monitoring_active = False
        self.total_updates_processed = 0
        self.total_changes_detected = 0
        self.session_start_time = time.time()
        self.http_client.reset_polling_state()
        
        logger.info("Monitoring state reset (v2: in-memory only)")
    
    def close(self):
        """Clean up resources"""
        self.http_client.close()
        logger.info("Oil price monitor closed")


def create_monitor(base_url: str = "https://play.myfly.club/oil-prices",
                  polling_interval: int = 300) -> OilPriceMonitor:
    """Factory function to create a new monitor instance (v2: in-memory only)"""
    return OilPriceMonitor(base_url, polling_interval=polling_interval)


# Example usage and testing
if __name__ == "__main__":
    # Test the price monitor
    monitor = create_monitor()
    
    try:
        print("🧪 Testing Oil Price Monitor")
        print("=" * 40)
        
        # Test 1: Check for updates
        print("\n📡 Test 1: Checking for updates")
        change_event = monitor.check_for_updates()
        
        if change_event:
            print(f"✅ Price change detected:")
            print(f"   Old price: ${change_event.old_price:.2f}" if change_event.old_price else "   Old price: None")
            print(f"   New price: ${change_event.new_price:.2f}")
            print(f"   Change: ${change_event.price_change:+.2f} ({change_event.price_change_percent:+.2f}%)")
            print(f"   Event type: {change_event.event_type}")
        else:
            print("✅ No significant price changes detected")
        
        # Test 2: Get current price
        print("\n💰 Test 2: Current price")
        current_price = monitor.get_current_price()
        if current_price:
            print(f"✅ Current price: ${current_price.price:.2f} (Cycle: {current_price.cycle})")
        else:
            print("❌ No current price available")
        
        # Test 3: Get monitoring status
        print("\n📊 Test 3: Monitoring status")
        status = monitor.get_monitoring_status()
        print("✅ Monitoring status:")
        for key, value in status.items():
            if key == 'http_client_status':
                print(f"   {key}: HTTP client details available")
            else:
                print(f"   {key}: {value}")
        
        # Test 4: Get price change summary
        print("\n📈 Test 4: Price change summary")
        summary = monitor.get_price_change_summary()
        print(f"✅ Price summary (v2: in-memory):")
        if summary['current_price']:
            print(f"   Current price: ${summary['current_price']:.2f}")
            print(f"   Current cycle: {summary['current_cycle']}")
        else:
            print("   Current price: Not available")
        print(f"   Session duration: {summary['session_stats']['session_duration']:.1f}s")
        print(f"   Updates processed: {summary['session_stats']['total_updates_processed']}")
        print(f"   Changes detected: {summary['session_stats']['total_changes_detected']}")
        
        print("\n🎉 Price monitor tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        logging.error(f"Test error: {e}", exc_info=True)
    
    finally:
        monitor.close()
