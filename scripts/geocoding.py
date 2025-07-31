import requests
import json
import time
import os
from typing import Tuple, Optional, Dict
import logging
import hashlib
import pickle
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KakaoGeocoder:
    """Geocoding service using Kakao Local API with caching."""
    
    def __init__(self, api_key: Optional[str] = None, cache_dir: str = "../data/cache"):
        """Initialize geocoder with API key and cache directory."""
        self.api_key = api_key or self._load_api_key()
        self.base_url = "https://dapi.kakao.com/v2/local/search/address.json"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "geocoding_cache.pkl"
        self.cache = self._load_cache()
        self.request_count = 0
        self.rate_limit_delay = 0.1  # 100ms between requests
        
    def _load_api_key(self) -> str:
        """Load API key from environment variable."""
        try:
            from config_loader import get_kakao_key
            api_key = get_kakao_key()
            if api_key:
                return api_key
        except ImportError:
            logger.debug("config_loader module not found, using direct environment variable access")
        
        # Direct environment variable access
        api_key = os.getenv('KAKAO_API_KEY', '')
        if not api_key:
            logger.warning("No Kakao API key found. Please set KAKAO_API_KEY in your .env file or environment variables")
        
        return api_key
    
    def _load_cache(self) -> Dict[str, Tuple[float, float]]:
        """Load geocoding cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    cache = pickle.load(f)
                    logger.info(f"Loaded geocoding cache with {len(cache)} entries")
                    return cache
            except Exception as e:
                logger.warning(f"Could not load cache: {e}")
        
        return {}
    
    def _save_cache(self):
        """Save geocoding cache to disk."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
        except Exception as e:
            logger.error(f"Could not save cache: {e}")
    
    def _get_cache_key(self, address: str) -> str:
        """Generate cache key for address."""
        return hashlib.md5(address.encode('utf-8')).hexdigest()
    
    def _make_request(self, address: str) -> Optional[Dict]:
        """Make API request to Kakao geocoding service."""
        if not self.api_key:
            logger.error("No API key available for geocoding")
            return None
        
        headers = {
            'Authorization': f'KakaoAK {self.api_key}'
        }
        
        params = {
            'query': address,
            'size': 1  # Only get the best match
        }
        
        try:
            # Rate limiting
            if self.request_count > 0:
                time.sleep(self.rate_limit_delay)
            
            response = requests.get(self.base_url, headers=headers, params=params, timeout=10)
            self.request_count += 1
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded, waiting 1 second...")
                time.sleep(1)
                return self._make_request(address)  # Retry once
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None
    
    def geocode(self, address: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Geocode an address to latitude, longitude coordinates.
        
        Args:
            address: Korean address string
            
        Returns:
            Tuple of (latitude, longitude) or (None, None) if geocoding fails
        """
        if not address or not isinstance(address, str):
            return None, None
        
        # Clean address
        address = address.strip()
        if not address:
            return None, None
        
        # Check cache first
        cache_key = self._get_cache_key(address)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Make API request
        result = self._make_request(address)
        
        if result and 'documents' in result and result['documents']:
            try:
                doc = result['documents'][0]
                lat = float(doc['y'])
                lon = float(doc['x'])
                
                # Cache the result
                self.cache[cache_key] = (lat, lon)
                
                # Save cache periodically
                if len(self.cache) % 100 == 0:
                    self._save_cache()
                
                logger.debug(f"Geocoded '{address}' -> ({lat}, {lon})")
                return lat, lon
                
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"Error parsing geocoding result for '{address}': {e}")
        else:
            logger.warning(f"No geocoding result for address: '{address}'")
        
        # Cache negative results to avoid repeated API calls
        self.cache[cache_key] = (None, None)
        return None, None
    
    def geocode_batch(self, addresses: list) -> list:
        """
        Geocode a list of addresses.
        
        Args:
            addresses: List of address strings
            
        Returns:
            List of (latitude, longitude) tuples
        """
        results = []
        total = len(addresses)
        
        for i, address in enumerate(addresses):
            if i % 100 == 0:
                logger.info(f"Geocoding progress: {i}/{total}")
            
            lat, lon = self.geocode(address)
            results.append((lat, lon))
        
        # Save final cache
        self._save_cache()
        logger.info(f"Geocoding completed: {total} addresses processed")
        
        return results
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total = len(self.cache)
        successful = sum(1 for v in self.cache.values() if v[0] is not None)
        failed = total - successful
        
        return {
            'total_cached': total,
            'successful': successful,
            'failed': failed,
            'requests_made': self.request_count
        }


def main():
    """Example usage of KakaoGeocoder."""
    geocoder = KakaoGeocoder()
    
    # Test addresses
    test_addresses = [
        "서울특별시 강남구 테헤란로 212",
        "서울 종로구 세종대로 110",
        "서울시 마포구 홍대입구역",
        "강북구 수유동 123-45"
    ]
    
    print("Testing individual geocoding:")
    for address in test_addresses:
        lat, lon = geocoder.geocode(address)
        print(f"{address} -> ({lat}, {lon})")
    
    print("\nTesting batch geocoding:")
    results = geocoder.geocode_batch(test_addresses)
    for addr, (lat, lon) in zip(test_addresses, results):
        print(f"{addr} -> ({lat}, {lon})")
    
    print("\nCache statistics:")
    stats = geocoder.get_cache_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()