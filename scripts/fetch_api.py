import requests
import json
import time
import pandas as pd
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIFetcher:
    """Fetches data from various Seoul public safety APIs."""
    
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        """
        Initialize API fetcher with API keys.
        
        Args:
            api_keys: Dictionary of API keys for different services
        """
        self.api_keys = api_keys or self._load_api_keys()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Seoul Safety Data Pipeline/1.0'
        })
        self.request_delay = 0.2  # 200ms between requests to be polite
        
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment variables."""
        api_keys = {}
        
        # Try to load using config loader
        try:
            from config_loader import (
                get_seoul_open_data_key,
                get_safemap_key,
                get_women_safety_key,
                get_sexual_offender_key,
                get_seoul_streetlight_key
            )
            
            # Map to legacy key names for backward compatibility
            key_mapping = {
                'seoul_open_data_key': get_seoul_open_data_key(),
                'police_api_key': get_seoul_open_data_key(),  # Use Seoul Open Data for police data
                'safety_api_key': get_safemap_key(),
                'women_safety_key': get_women_safety_key(),
                'sexual_offender_key': get_sexual_offender_key(),
                'streetlight_key': get_seoul_streetlight_key()
            }
            
            for key_name, api_key in key_mapping.items():
                if api_key:
                    api_keys[key_name] = api_key
            
            if api_keys:
                logger.info("Loaded API keys using config loader")
                return api_keys
                
        except ImportError:
            logger.debug("config_loader module not found, using direct environment variable access")
        
        # Direct environment variable access
        env_keys = {
            'seoul_open_data_key': 'SEOUL_OPEN_API_KEY',
            'police_api_key': 'SEOUL_OPEN_API_KEY',  # Same as Seoul Open Data
            'safety_api_key': 'SAFEMAP_API_KEY',
            'women_safety_key': 'WOMEN_SAFETY_API_KEY',
            'sexual_offender_key': 'SEXUAL_OFFENDER_API_KEY',
            'streetlight_key': 'SEOUL_STREETLIGHT_API_KEY'
        }
        
        for key, env_var in env_keys.items():
            env_value = os.getenv(env_var)
            if env_value:
                api_keys[key] = env_value
        
        if not api_keys:
            logger.warning("No API keys found. Please set API keys in your .env file")
        
        return api_keys
    
    def _make_request(self, url: str, params: Dict[str, Any], max_retries: int = 3) -> Optional[Dict]:
        """Make HTTP request with retry logic."""
        for attempt in range(max_retries):
            try:
                time.sleep(self.request_delay)
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Rate limited, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"API request failed: {response.status_code} - {response.text}")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(2 ** attempt)
        
        return None
    
    def fetch_police_facilities(self) -> pd.DataFrame:
        """Fetch police facility data from Seoul Open Data API."""
        api_key = self.api_keys.get('seoul_open_data_key')
        if not api_key:
            logger.error("Seoul Open Data API key not found")
            return pd.DataFrame()
        
        base_url = "http://openapi.seoul.go.kr:8088"
        service_name = "ListPoliceStationService"  # Adjust based on actual service name
        
        all_data = []
        start_index = 1
        end_index = 1000
        
        while True:
            url = f"{base_url}/{api_key}/json/{service_name}/{start_index}/{end_index}/"
            
            logger.info(f"Fetching police facilities: {start_index}-{end_index}")
            result = self._make_request(url, {})
            
            if not result:
                break
            
            # Parse response structure (adjust based on actual API response)
            try:
                service_key = list(result.keys())[0]  # Usually the service name
                data = result[service_key]
                
                if 'RESULT' in data and data['RESULT']['CODE'] != 'INFO-000':
                    logger.error(f"API error: {data['RESULT']['MESSAGE']}")
                    break
                
                rows = data.get('row', [])
                if not rows:
                    break
                
                all_data.extend(rows)
                
                # Check if we've reached the end
                if len(rows) < (end_index - start_index + 1):
                    break
                
                start_index = end_index + 1
                end_index += 1000
                
            except (KeyError, IndexError) as e:
                logger.error(f"Error parsing police facility API response: {e}")
                break
        
        if all_data:
            df = pd.DataFrame(all_data)
            logger.info(f"Fetched {len(df)} police facility records")
            
            # Standardize column names
            column_mapping = {
                'FCLT_NM': 'facility_name',
                'ADDR': 'address', 
                'LAT': 'latitude',
                'LOT': 'longitude',
                'TEL_NO': 'phone',
                'FCLT_DIV': 'facility_type'
            }
            
            # Rename columns that exist
            existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing_mapping)
            
            # Convert coordinates to numeric
            if 'latitude' in df.columns:
                df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
            if 'longitude' in df.columns:  
                df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
            
            return df
        
        return pd.DataFrame()
    
    def fetch_womens_safe_houses(self) -> pd.DataFrame:
        """Fetch women's safe house data from Seoul Open Data API."""
        api_key = self.api_keys.get('seoul_open_data_key')
        if not api_key:
            logger.error("Seoul Open Data API key not found")
            return pd.DataFrame()
        
        base_url = "http://openapi.seoul.go.kr:8088"
        service_name = "ListWomenSafeHouseService"  # Adjust based on actual service name
        
        all_data = []
        start_index = 1
        end_index = 1000
        
        while True:
            url = f"{base_url}/{api_key}/json/{service_name}/{start_index}/{end_index}/"
            
            logger.info(f"Fetching women's safe houses: {start_index}-{end_index}")
            result = self._make_request(url, {})
            
            if not result:
                break
            
            try:
                service_key = list(result.keys())[0]
                data = result[service_key]
                
                if 'RESULT' in data and data['RESULT']['CODE'] != 'INFO-000':
                    logger.error(f"API error: {data['RESULT']['MESSAGE']}")
                    break
                
                rows = data.get('row', [])
                if not rows:
                    break
                
                all_data.extend(rows)
                
                if len(rows) < (end_index - start_index + 1):
                    break
                
                start_index = end_index + 1
                end_index += 1000
                
            except (KeyError, IndexError) as e:
                logger.error(f"Error parsing safe house API response: {e}")
                break
        
        if all_data:
            df = pd.DataFrame(all_data)
            logger.info(f"Fetched {len(df)} women's safe house records")
            
            column_mapping = {
                'FCLT_NM': 'facility_name',
                'ADDR': 'address',
                'LAT': 'latitude', 
                'LOT': 'longitude',
                'TEL_NO': 'phone',
                'OPER_TIME': 'operating_hours'
            }
            
            existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing_mapping)
            
            if 'latitude' in df.columns:
                df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
            if 'longitude' in df.columns:
                df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
            
            return df
        
        return pd.DataFrame()
    
    def fetch_emergency_bells(self) -> pd.DataFrame:
        """Fetch emergency bell/safety bell data."""
        api_key = self.api_keys.get('seoul_open_data_key')
        if not api_key:
            logger.error("Seoul Open Data API key not found")
            return pd.DataFrame()
        
        base_url = "http://openapi.seoul.go.kr:8088"
        service_name = "ListEmergencyBellService"  # Adjust based on actual service name
        
        all_data = []
        start_index = 1
        end_index = 1000
        
        while True:
            url = f"{base_url}/{api_key}/json/{service_name}/{start_index}/{end_index}/"
            
            logger.info(f"Fetching emergency bells: {start_index}-{end_index}")
            result = self._make_request(url, {})
            
            if not result:
                break
            
            try:
                service_key = list(result.keys())[0]
                data = result[service_key]
                
                if 'RESULT' in data and data['RESULT']['CODE'] != 'INFO-000':
                    logger.error(f"API error: {data['RESULT']['MESSAGE']}")
                    break
                
                rows = data.get('row', [])
                if not rows:
                    break
                
                all_data.extend(rows)
                
                if len(rows) < (end_index - start_index + 1):
                    break
                
                start_index = end_index + 1
                end_index += 1000
                
            except (KeyError, IndexError) as e:
                logger.error(f"Error parsing emergency bell API response: {e}")
                break
        
        if all_data:
            df = pd.DataFrame(all_data)
            logger.info(f"Fetched {len(df)} emergency bell records")
            
            column_mapping = {
                'BELL_NM': 'bell_name',
                'ADDR': 'address',
                'LAT': 'latitude',
                'LOT': 'longitude', 
                'INSTL_YM': 'install_date'
            }
            
            existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
            df = df.rename(columns=existing_mapping)
            
            if 'latitude' in df.columns:
                df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
            if 'longitude' in df.columns:
                df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
            
            return df
        
        return pd.DataFrame()
    
    def fetch_all_api_data(self) -> Dict[str, pd.DataFrame]:
        """Fetch all available API data."""
        logger.info("Starting API data fetching...")
        
        datasets = {
            'police_facilities': self.fetch_police_facilities,
            'womens_safe_houses': self.fetch_womens_safe_houses,
            'emergency_bells': self.fetch_emergency_bells
        }
        
        results = {}
        
        for name, fetch_func in datasets.items():
            try:
                logger.info(f"Fetching {name}...")
                df = fetch_func()
                results[name] = df
                
                if not df.empty:
                    # Save raw API data
                    output_path = f"../data/raw/{name}_api.csv"
                    df.to_csv(output_path, index=False, encoding='utf-8')
                    logger.info(f"Saved {name} to {output_path}")
                else:
                    logger.warning(f"No data retrieved for {name}")
                    
            except Exception as e:
                logger.error(f"Error fetching {name}: {e}")
                results[name] = pd.DataFrame()
        
        logger.info("API data fetching completed")
        return results


def main():
    """Example usage of APIFetcher."""
    fetcher = APIFetcher()
    
    # Check if API keys are available
    if not fetcher.api_keys.get('seoul_open_data_key'):
        print("No Seoul Open Data API key found.")
        print("Please add your API key to config/api_keys.json or set SEOUL_OPEN_DATA_KEY environment variable")
        print("You can get an API key from: https://data.seoul.go.kr/")
        return
    
    # Fetch individual datasets
    print("Fetching police facilities...")
    police_df = fetcher.fetch_police_facilities()
    print(f"Police facilities: {len(police_df)} records")
    
    print("\nFetching women's safe houses...")
    safehouse_df = fetcher.fetch_womens_safe_houses()
    print(f"Women's safe houses: {len(safehouse_df)} records")
    
    print("\nFetching emergency bells...")
    bells_df = fetcher.fetch_emergency_bells()
    print(f"Emergency bells: {len(bells_df)} records")
    
    # Fetch all data at once
    print("\nFetching all API data...")
    all_data = fetcher.fetch_all_api_data()
    
    for name, df in all_data.items():
        print(f"{name}: {len(df)} records")
        if not df.empty:
            print(f"  Columns: {list(df.columns)}")


if __name__ == "__main__":
    main()