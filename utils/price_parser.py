"""
Oil Price Parser Module

This module handles parsing of JSON responses from the oil price endpoint
and extracts the latest price based on the highest cycle number.
"""

import json
import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class OilPriceData:
    """Data class for oil price information"""
    price: float
    cycle: int
    timestamp: Optional[str] = None

class OilPriceParser:
    """Parser for oil price JSON responses"""
    
    def __init__(self):
        self.last_parsed_data: Optional[List[OilPriceData]] = None
        self.last_latest_price: Optional[OilPriceData] = None
    
    def parse_json_response(self, json_string: str) -> List[OilPriceData]:
        """
        Parse JSON response string into list of OilPriceData objects
        
        Args:
            json_string: JSON string from the endpoint
            
        Returns:
            List of OilPriceData objects
            
        Raises:
            ValueError: If JSON is malformed or data structure is invalid
            KeyError: If required fields are missing
        """
        try:
            # Parse JSON string
            raw_data = json.loads(json_string)
            
            # Validate data structure
            if not isinstance(raw_data, list):
                raise ValueError("Response must be a JSON array")
            
            if not raw_data:
                raise ValueError("Response array cannot be empty")
            
            # Parse each price entry
            parsed_data = []
            for i, entry in enumerate(raw_data):
                try:
                    # Validate entry structure
                    if not isinstance(entry, dict):
                        raise ValueError(f"Entry {i} must be an object, got {type(entry)}")
                    
                    # Extract and validate price field
                    if 'price' not in entry:
                        raise KeyError(f"Entry {i} missing 'price' field")
                    
                    price = entry['price']
                    if not isinstance(price, (int, float)):
                        raise ValueError(f"Entry {i} 'price' must be numeric, got {type(price)}")
                    
                    # Extract and validate cycle field
                    if 'cycle' not in entry:
                        raise KeyError(f"Entry {i} missing 'cycle' field")
                    
                    cycle = entry['cycle']
                    if not isinstance(cycle, int):
                        raise ValueError(f"Entry {i} 'cycle' must be integer, got {type(cycle)}")
                    
                    # Create OilPriceData object
                    price_data = OilPriceData(
                        price=float(price),
                        cycle=cycle
                    )
                    parsed_data.append(price_data)
                    
                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping invalid entry {i}: {e}")
                    continue
            
            if not parsed_data:
                raise ValueError("No valid price entries found in response")
            
            # Sort by cycle number for consistency
            parsed_data.sort(key=lambda x: x.cycle)
            
            # Store parsed data
            self.last_parsed_data = parsed_data
            
            logger.info(f"Successfully parsed {len(parsed_data)} price entries")
            return parsed_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            raise ValueError(f"Invalid JSON format: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            raise
    
    def get_latest_price(self, json_string: str) -> OilPriceData:
        """
        Extract the latest oil price from JSON response
        
        Args:
            json_string: JSON string from the endpoint
            
        Returns:
            OilPriceData object with the latest price (highest cycle)
            
        Raises:
            ValueError: If parsing fails or no valid data found
        """
        # Parse the JSON response
        parsed_data = self.parse_json_response(json_string)
        
        # Find the entry with the highest cycle number
        latest_entry = max(parsed_data, key=lambda x: x.cycle)
        
        # Store the latest price
        self.last_latest_price = latest_entry
        
        logger.info(f"Latest oil price: ${latest_entry.price:.2f} (Cycle: {latest_entry.cycle})")
        return latest_entry
    
    def get_price_history(self, json_string: str, limit: int = 10) -> List[OilPriceData]:
        """
        Get recent price history from JSON response
        
        Args:
            json_string: JSON string from the endpoint
            limit: Maximum number of recent entries to return
            
        Returns:
            List of recent OilPriceData objects, sorted by cycle (newest first)
        """
        parsed_data = self.parse_json_response(json_string)
        
        # Sort by cycle (descending) and take the most recent entries
        sorted_data = sorted(parsed_data, key=lambda x: x.cycle, reverse=True)
        return sorted_data[:limit]
    
    def validate_price_data(self, price_data: OilPriceData) -> bool:
        """
        Validate price data for reasonable values
        
        Args:
            price_data: OilPriceData object to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Check price range (reasonable oil prices: $10 - $200 per barrel)
        if not (10.0 <= price_data.price <= 200.0):
            logger.warning(f"Price ${price_data.price:.2f} is outside reasonable range")
            return False
        
        # Check cycle number (should be positive)
        if price_data.cycle <= 0:
            logger.warning(f"Invalid cycle number: {price_data.cycle}")
            return False
        
        return True
    
    def get_statistics(self, json_string: str) -> Dict[str, Union[float, int]]:
        """
        Get basic statistics from the price data
        
        Args:
            json_string: JSON string from the endpoint
            
        Returns:
            Dictionary with statistics
        """
        parsed_data = self.parse_json_response(json_string)
        
        if not parsed_data:
            return {}
        
        prices = [entry.price for entry in parsed_data]
        cycles = [entry.cycle for entry in parsed_data]
        
        stats = {
            'total_entries': len(parsed_data),
            'latest_price': max(entry.price for entry in parsed_data if entry.cycle == max(cycles)),
            'latest_cycle': max(cycles),
            'min_price': min(prices),
            'max_price': max(prices),
            'avg_price': sum(prices) / len(prices),
            'price_range': max(prices) - min(prices)
        }
        
        return stats

