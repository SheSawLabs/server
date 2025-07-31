import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from typing import Optional, Tuple, Dict
import logging
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DongAssigner:
    """Assigns administrative dong (법정동) to coordinates using Seoul GeoJSON/SHP data."""
    
    def __init__(self, geojson_path: Optional[str] = None):
        """
        Initialize dong assigner with Seoul administrative boundary data.
        
        Args:
            geojson_path: Path to Seoul 법정동 GeoJSON or SHP file
        """
        self.geojson_path = geojson_path or self._find_geojson_file()
        self.gdf = None
        self.loaded = False
        
    def _find_geojson_file(self) -> Optional[str]:
        """Automatically find Seoul dong GeoJSON/SHP file in common locations."""
        possible_paths = [
            "../data/seoul_dong.geojson",
            "../data/seoul_dong.json", 
            "../data/raw/seoul_dong.geojson",
            "../data/raw/seoul_dong.json",
            "../data/seoul_administrative_dong.geojson",
            "../data/raw/HangJeongDong_ver20220701.geojson",
            "../data/raw/seoul_dong.shp"
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                logger.info(f"Found Seoul dong data at: {path}")
                return path
        
        logger.warning("No Seoul dong GeoJSON/SHP file found. Please provide geojson_path parameter.")
        return None
    
    def load_boundaries(self) -> bool:
        """Load Seoul administrative boundary data."""
        if self.loaded:
            return True
            
        if not self.geojson_path or not Path(self.geojson_path).exists():
            logger.error(f"Seoul dong data file not found: {self.geojson_path}")
            return False
        
        try:
            # Load geospatial data
            self.gdf = gpd.read_file(self.geojson_path, encoding='utf-8')
            
            # Ensure CRS is WGS84 (EPSG:4326) for lat/lon coordinates
            if self.gdf.crs is None:
                self.gdf.set_crs('EPSG:4326', inplace=True)
            elif self.gdf.crs != 'EPSG:4326':
                self.gdf = self.gdf.to_crs('EPSG:4326')
            
            # Common column name variations for dong names
            dong_columns = ['dong', 'dong_name', 'adm_nm', 'name', 'EMD_NM', 'H_DNG_NM', '동명']
            
            self.dong_column = None
            for col in dong_columns:
                if col in self.gdf.columns:
                    self.dong_column = col
                    break
            
            if self.dong_column is None:
                logger.warning("Could not identify dong name column. Available columns:")
                logger.warning(list(self.gdf.columns))
                # Use the first string column as fallback
                for col in self.gdf.columns:
                    if self.gdf[col].dtype == 'object':
                        self.dong_column = col
                        logger.info(f"Using column '{col}' as dong name")
                        break
            
            # Filter for Seoul only if data contains other regions
            if 'sigungu' in self.gdf.columns or 'SGG_NM' in self.gdf.columns:
                sigungu_col = 'sigungu' if 'sigungu' in self.gdf.columns else 'SGG_NM'
                seoul_filter = self.gdf[sigungu_col].str.contains('서울', na=False)
                self.gdf = self.gdf[seoul_filter]
            
            self.loaded = True
            logger.info(f"Loaded Seoul dong boundaries: {len(self.gdf)} districts")
            logger.info(f"Using column '{self.dong_column}' for dong names")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading Seoul dong data: {e}")
            return False
    
    def assign_dong(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Assign dong name to given coordinates.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            
        Returns:
            Dong name string or None if not found
        """
        if not self.loaded and not self.load_boundaries():
            return None
        
        if pd.isna(latitude) or pd.isna(longitude):
            return None
        
        try:
            # Create point geometry
            point = Point(longitude, latitude)  # Note: longitude first for Point(x, y)
            
            # Find containing polygon
            containing = self.gdf[self.gdf.geometry.contains(point)]
            
            if len(containing) > 0:
                dong_name = containing.iloc[0][self.dong_column]
                return str(dong_name).strip()
            else:
                # If no exact match, try nearest neighbor (in case point is slightly outside)
                distances = self.gdf.geometry.distance(point)
                nearest_idx = distances.idxmin()
                
                # Only use nearest if it's very close (within ~100m in degrees)
                if distances.iloc[nearest_idx] < 0.001:  # approximately 100m
                    dong_name = self.gdf.iloc[nearest_idx][self.dong_column]
                    logger.debug(f"Used nearest dong for point ({latitude}, {longitude}): {dong_name}")
                    return str(dong_name).strip()
                
                return None
                
        except Exception as e:
            logger.error(f"Error assigning dong for coordinates ({latitude}, {longitude}): {e}")
            return None
    
    def assign_dong_batch(self, coordinates: list) -> list:
        """
        Assign dong names to a list of coordinate pairs.
        
        Args:
            coordinates: List of (latitude, longitude) tuples
            
        Returns:
            List of dong name strings (or None for unmatched coordinates)
        """
        if not self.loaded and not self.load_boundaries():
            return [None] * len(coordinates)
        
        results = []
        total = len(coordinates)
        
        for i, (lat, lon) in enumerate(coordinates):
            if i % 1000 == 0:
                logger.info(f"Dong assignment progress: {i}/{total}")
            
            dong = self.assign_dong(lat, lon)
            results.append(dong)
        
        logger.info(f"Dong assignment completed: {total} coordinates processed")
        return results
    
    def get_dong_list(self) -> list:
        """Get list of all dong names in the dataset."""
        if not self.loaded and not self.load_boundaries():
            return []
        
        return sorted(self.gdf[self.dong_column].unique().tolist())
    
    def get_dong_info(self, dong_name: str) -> Optional[Dict]:
        """Get information about a specific dong."""
        if not self.loaded and not self.load_boundaries():
            return None
        
        dong_data = self.gdf[self.gdf[self.dong_column] == dong_name]
        
        if len(dong_data) == 0:
            return None
        
        row = dong_data.iloc[0]
        geometry = row.geometry
        
        return {
            'name': dong_name,
            'area_km2': geometry.area * 111.32 ** 2,  # Rough conversion to km²
            'centroid': {
                'latitude': geometry.centroid.y,
                'longitude': geometry.centroid.x
            },
            'bounds': {
                'min_lat': geometry.bounds[1],
                'min_lon': geometry.bounds[0], 
                'max_lat': geometry.bounds[3],
                'max_lon': geometry.bounds[2]
            }
        }


def main():
    """Example usage of DongAssigner."""
    assigner = DongAssigner()
    
    if not assigner.load_boundaries():
        print("Could not load Seoul dong boundary data.")
        print("Please download Seoul 법정동 GeoJSON file and place it in ../data/")
        return
    
    # Test coordinates (Gangnam-gu, Jung-gu, Mapo-gu)
    test_coordinates = [
        (37.5665, 126.9780),  # Jung-gu (City Hall area)
        (37.4979, 127.0276),  # Gangnam-gu 
        (37.5563, 126.9236),  # Mapo-gu (Hongdae area)
        (37.5834, 127.0089),  # Jongno-gu
    ]
    
    print("Testing individual dong assignment:")
    for lat, lon in test_coordinates:
        dong = assigner.assign_dong(lat, lon)
        print(f"({lat}, {lon}) -> {dong}")
    
    print("\nTesting batch dong assignment:")
    dongs = assigner.assign_dong_batch(test_coordinates)
    for (lat, lon), dong in zip(test_coordinates, dongs):
        print(f"({lat}, {lon}) -> {dong}")
    
    print(f"\nTotal dongs in dataset: {len(assigner.get_dong_list())}")
    
    # Show info for first assigned dong
    if dongs[0]:
        info = assigner.get_dong_info(dongs[0])
        if info:
            print(f"\nInfo for {dongs[0]}:")
            print(f"  Area: {info['area_km2']:.2f} km²")
            print(f"  Centroid: ({info['centroid']['latitude']:.4f}, {info['centroid']['longitude']:.4f})")


if __name__ == "__main__":
    main()