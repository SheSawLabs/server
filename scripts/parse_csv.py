import pandas as pd
import re
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CSVParser:
    """Parser for various Seoul public safety CSV datasets."""
    
    def __init__(self):
        self.address_patterns = {
            'seoul_prefix': r'^서울특별시\s*',
            'district_gu': r'([가-힣]+구)\s*',
            'dong_ro': r'([가-힣]+[동로길]\s*\d*[-\d]*)',
        }
    
    def standardize_address(self, address: str) -> str:
        """Standardize Seoul address format."""
        if pd.isna(address) or not isinstance(address, str):
            return ""
        
        # Remove leading/trailing whitespace
        address = address.strip()
        
        # Remove '서울특별시' prefix if present
        address = re.sub(self.address_patterns['seoul_prefix'], '', address)
        
        # Standardize spacing
        address = re.sub(r'\s+', ' ', address)
        
        return address
    
    def parse_cctv_data(self, file_path: str) -> pd.DataFrame:
        """Parse CCTV installation data CSV."""
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            logger.info(f"Loaded CCTV data: {len(df)} records")
            
            # Select and rename relevant columns
            column_mapping = {
                # Adjust these based on actual CSV column names
                '주소': 'address',
                '설치목적': 'purpose',
                '설치년도': 'install_year',
                '관리기관': 'management_agency'
            }
            
            # Keep only columns that exist in the dataframe
            available_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            df_clean = df[list(available_columns.keys())].rename(columns=available_columns)
            
            # Standardize addresses
            if 'address' in df_clean.columns:
                df_clean['address'] = df_clean['address'].apply(self.standardize_address)
            
            # Remove rows with empty addresses
            df_clean = df_clean[df_clean['address'].str.len() > 0]
            
            logger.info(f"Cleaned CCTV data: {len(df_clean)} records")
            return df_clean
            
        except Exception as e:
            logger.error(f"Error parsing CCTV data: {e}")
            return pd.DataFrame()
    
    def parse_lamp_data(self, file_path: str) -> pd.DataFrame:
        """Parse lamp/light pole data CSV."""
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            logger.info(f"Loaded lamp data: {len(df)} records")
            
            column_mapping = {
                '위도': 'latitude',
                '경도': 'longitude',
                '주소': 'address',
                '설치일자': 'install_date',
                '램프타입': 'lamp_type'
            }
            
            available_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            df_clean = df[list(available_columns.keys())].rename(columns=available_columns)
            
            # Convert lat/lon to numeric
            if 'latitude' in df_clean.columns:
                df_clean['latitude'] = pd.to_numeric(df_clean['latitude'], errors='coerce')
            if 'longitude' in df_clean.columns:
                df_clean['longitude'] = pd.to_numeric(df_clean['longitude'], errors='coerce')
            
            # Standardize addresses if present
            if 'address' in df_clean.columns:
                df_clean['address'] = df_clean['address'].apply(self.standardize_address)
            
            # Remove rows with invalid coordinates
            df_clean = df_clean.dropna(subset=['latitude', 'longitude'])
            
            logger.info(f"Cleaned lamp data: {len(df_clean)} records")
            return df_clean
            
        except Exception as e:
            logger.error(f"Error parsing lamp data: {e}")
            return pd.DataFrame()
    
    def parse_delivery_box_data(self, file_path: str) -> pd.DataFrame:
        """Parse safe delivery box locations CSV."""
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            logger.info(f"Loaded delivery box data: {len(df)} records")
            
            column_mapping = {
                '주소': 'address',
                '설치위치': 'install_location',
                '운영기관': 'operator',
                '설치일': 'install_date'
            }
            
            available_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            df_clean = df[list(available_columns.keys())].rename(columns=available_columns)
            
            if 'address' in df_clean.columns:
                df_clean['address'] = df_clean['address'].apply(self.standardize_address)
                df_clean = df_clean[df_clean['address'].str.len() > 0]
            
            logger.info(f"Cleaned delivery box data: {len(df_clean)} records")
            return df_clean
            
        except Exception as e:
            logger.error(f"Error parsing delivery box data: {e}")
            return pd.DataFrame()
    
    def parse_offender_data(self, file_path: str) -> pd.DataFrame:
        """Parse sexual offender residence data CSV."""
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            logger.info(f"Loaded offender data: {len(df)} records")
            
            column_mapping = {
                '주소': 'address',
                '거주지구분': 'residence_type',
                '신고일': 'report_date'
            }
            
            available_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            df_clean = df[list(available_columns.keys())].rename(columns=available_columns)
            
            if 'address' in df_clean.columns:
                df_clean['address'] = df_clean['address'].apply(self.standardize_address)
                df_clean = df_clean[df_clean['address'].str.len() > 0]
            
            logger.info(f"Cleaned offender data: {len(df_clean)} records")
            return df_clean
            
        except Exception as e:
            logger.error(f"Error parsing offender data: {e}")
            return pd.DataFrame()
    
    def parse_support_center_data(self, file_path: str) -> pd.DataFrame:
        """Parse public safety support centers CSV."""
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            logger.info(f"Loaded support center data: {len(df)} records")
            
            column_mapping = {
                '주소': 'address',
                '센터명': 'center_name',
                '전화번호': 'phone',
                '운영시간': 'operating_hours'
            }
            
            available_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
            df_clean = df[list(available_columns.keys())].rename(columns=available_columns)
            
            if 'address' in df_clean.columns:
                df_clean['address'] = df_clean['address'].apply(self.standardize_address)
                df_clean = df_clean[df_clean['address'].str.len() > 0]
            
            logger.info(f"Cleaned support center data: {len(df_clean)} records")
            return df_clean
            
        except Exception as e:
            logger.error(f"Error parsing support center data: {e}")
            return pd.DataFrame()


def main():
    """Example usage of CSVParser."""
    parser = CSVParser()
    
    # Example file paths (adjust as needed)
    data_files = {
        'cctv': '../data/raw/cctv_data.csv',
        'lamps': '../data/raw/lamp_data.csv',
        'delivery_boxes': '../data/raw/delivery_box_data.csv',
        'offenders': '../data/raw/offender_data.csv',
        'support_centers': '../data/raw/support_center_data.csv'
    }
    
    parsers = {
        'cctv': parser.parse_cctv_data,
        'lamps': parser.parse_lamp_data,
        'delivery_boxes': parser.parse_delivery_box_data,
        'offenders': parser.parse_offender_data,
        'support_centers': parser.parse_support_center_data
    }
    
    for data_type, file_path in data_files.items():
        try:
            df = parsers[data_type](file_path)
            if not df.empty:
                output_path = f'../data/cleaned/{data_type}_cleaned.csv'
                df.to_csv(output_path, index=False, encoding='utf-8')
                logger.info(f"Saved cleaned {data_type} data to {output_path}")
        except FileNotFoundError:
            logger.warning(f"File not found: {file_path}")
        except Exception as e:
            logger.error(f"Error processing {data_type}: {e}")


if __name__ == "__main__":
    main()