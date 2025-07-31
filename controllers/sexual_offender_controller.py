#!/usr/bin/env python3
"""
성범죄자 공개 및 고지 지번 주소 정보 수집 컨트롤러

여성가족부에서 제공하는 성범죄자 공개 및 고지 지번 주소 정보를 수집하고 처리합니다.
"""

import requests
import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import os

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_go_kr_api import DataGoKrAPI
from db.db_connection import DatabaseManager
from utils.geocoding import KakaoGeocoder

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SexualOffenderController:
    """성범죄자 공개 및 고지 지번 주소 정보 컨트롤러"""
    
    def __init__(self):
        """컨트롤러 초기화"""
        # API 클라이언트 초기화
        self.api_client = DataGoKrAPI()
        
        # 데이터베이스 연결
        self.db = DatabaseManager()
        
        # 주소 geocoder
        self.geocoder = KakaoGeocoder()
        
        # API 설정
        self.service_url = "1383000/sais/SexualAbuseNoticeHouseNumAddrServiceV2/getSexualAbuseNoticeHouseNumAddrListV2"
        self.daily_limit = 10000  # 일일 API 호출 제한
        self.delay_between_requests = 0.1  # 요청 간 지연 시간
        
        logger.info("SexualOffenderController initialized")
    
    def get_total_count(self) -> int:
        """전체 데이터 개수 조회"""
        try:
            params = {
                'pageNo': '1',
                'numOfRows': '1',
                'type': 'json'
            }
            
            response = self.api_client.fetch_data(self.service_url, params)
            
            if response and 'response' in response:
                body = response['response'].get('body', {})
                total_count = body.get('totalCount', 0)
                logger.info(f"Total sexual offender address records: {total_count:,}")
                return total_count
            else:
                logger.error("Failed to get total count")
                return 0
                
        except Exception as e:
            logger.error(f"Error getting total count: {e}")
            return 0
    
    def fetch_data_page(self, page: int = 1, per_page: int = 1000) -> Dict[str, Any]:
        """페이지별 데이터 조회"""
        try:
            params = {
                'pageNo': str(page),
                'numOfRows': str(per_page),
                'type': 'json'
            }
            
            logger.debug(f"Fetching page {page} with {per_page} records per page")
            
            response = self.api_client.fetch_data(self.service_url, params)
            
            if response and 'response' in response:
                header = response['response'].get('header', {})
                if header.get('resultCode') == '0':
                    body = response['response'].get('body', {})
                    items = body.get('items', {})
                    
                    # items가 리스트인지 딕셔너리인지 확인
                    if isinstance(items, dict) and 'item' in items:
                        data_list = items['item']
                        # 단일 아이템인 경우 리스트로 변환
                        if not isinstance(data_list, list):
                            data_list = [data_list]
                    else:
                        data_list = []
                    
                    return {
                        'success': True,
                        'data': data_list,
                        'total_count': body.get('totalCount', 0),
                        'current_page': body.get('pageNo', page),
                        'records_count': len(data_list)
                    }
                else:
                    logger.error(f"API error: {header.get('resultMsg', 'Unknown error')}")
                    return {
                        'success': False,
                        'error': header.get('resultMsg', 'Unknown error'),
                        'data': []
                    }
            else:
                logger.error("Invalid API response format")
                return {
                    'success': False,
                    'error': 'Invalid response format',
                    'data': []
                }
                
        except Exception as e:
            logger.error(f"Error fetching data for page {page}: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': []
            }
    
    def process_raw_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """원시 데이터를 처리하여 표준화된 형태로 변환"""
        processed_data = []
        
        for item in raw_data:
            try:
                # 기본 주소 정보 구성
                address_parts = []
                
                # 시도명, 시군구명, 읍면동명 조합
                if item.get('ctpvNm'):
                    address_parts.append(item['ctpvNm'])
                if item.get('sggNm'):
                    address_parts.append(item['sggNm'])
                if item.get('umdNm'):
                    address_parts.append(item['umdNm'])
                
                # 지번 주소 구성
                lot_number_parts = []
                if item.get('mno'):
                    lot_number_parts.append(str(item['mno']))
                if item.get('sno') and int(item.get('sno', 0)) > 0:
                    lot_number_parts.append(str(item['sno']))
                
                lot_number = '-'.join(lot_number_parts) if lot_number_parts else ''
                
                # 전체 주소
                full_address = ' '.join(address_parts)
                if lot_number:
                    full_address += f' {lot_number}'
                
                # 법정리명이 있으면 추가
                if item.get('stliNm'):
                    full_address += f' {item["stliNm"]}'
                
                processed_item = {
                    'data_creation_date': item.get('dataCrtYmd', ''),
                    'standard_code': item.get('stdgCd', ''),
                    'mountain_yn': item.get('mtnYn', '0') == '1',
                    'main_number': int(item.get('mno', 0)),
                    'sub_number': int(item.get('sno', 0)),
                    'standard_city_county_code': item.get('stdgCtpvSggCd', ''),
                    'standard_emd_code': item.get('stdgEmdCd', ''),
                    'road_name_number': item.get('roadNmNo', ''),
                    'underground_yn': item.get('udgdYn', '0') == '1',
                    'building_main_number': int(item.get('bmno', 0)),
                    'building_sub_number': int(item.get('bsno', 0)),
                    'city_province_name': item.get('ctpvNm', ''),
                    'city_county_name': item.get('sggNm', ''),
                    'emd_name': item.get('umdNm', ''),
                    'legal_dong_name': item.get('stliNm', ''),
                    'representative_lot_yn': item.get('rprsLotnoYn', '0') == '1',
                    'full_address': full_address,
                    'lot_number': lot_number,
                    'latitude': None,
                    'longitude': None,
                    'geocoding_method': None
                }
                
                processed_data.append(processed_item)
                
            except Exception as e:
                logger.error(f"Error processing item {item}: {e}")
                continue
        
        logger.info(f"Processed {len(processed_data)} sexual offender address records")
        return processed_data
    
    def geocode_addresses(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """주소 데이터에 좌표 정보 추가"""
        geocoded_data = []
        
        for item in data:
            try:
                # 일단 좌표 없이 저장 (나중에 별도 프로세스로 지오코딩)
                # KakaoGeocoder는 coordinate_to_address 메서드만 있어서
                # 주소->좌표 변환은 별도 구현 필요
                item['latitude'] = None
                item['longitude'] = None
                item['geocoding_method'] = 'pending'
                
                geocoded_data.append(item)
                
            except Exception as e:
                logger.error(f"Error processing address {item.get('full_address', '')}: {e}")
                # 좌표 없이도 저장
                geocoded_data.append(item) 
                continue
        
        logger.info(f"Prepared {len(geocoded_data)} records for geocoding (will be processed later)")
        return geocoded_data
    
    def save_to_database(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """처리된 데이터를 데이터베이스에 저장"""
        if not data:
            return {'success': True, 'saved_count': 0}
        
        try:
            # 테이블 생성 (없는 경우)
            self._ensure_table_exists()
            
            # 데이터 삽입
            insert_query = """
            INSERT INTO sexual_offender_addresses (
                data_creation_date, standard_code, mountain_yn, main_number, sub_number,
                standard_city_county_code, standard_emd_code, road_name_number,
                underground_yn, building_main_number, building_sub_number,
                city_province_name, city_county_name, emd_name, legal_dong_name,
                representative_lot_yn, full_address, lot_number, latitude, longitude, geocoding_method
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (standard_code, main_number, sub_number) DO UPDATE SET
                data_creation_date = EXCLUDED.data_creation_date,
                mountain_yn = EXCLUDED.mountain_yn,
                standard_city_county_code = EXCLUDED.standard_city_county_code,
                standard_emd_code = EXCLUDED.standard_emd_code,
                road_name_number = EXCLUDED.road_name_number,
                underground_yn = EXCLUDED.underground_yn,
                building_main_number = EXCLUDED.building_main_number,
                building_sub_number = EXCLUDED.building_sub_number,
                city_province_name = EXCLUDED.city_province_name,
                city_county_name = EXCLUDED.city_county_name,
                emd_name = EXCLUDED.emd_name,
                legal_dong_name = EXCLUDED.legal_dong_name,
                representative_lot_yn = EXCLUDED.representative_lot_yn,
                full_address = EXCLUDED.full_address,
                lot_number = EXCLUDED.lot_number,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                geocoding_method = EXCLUDED.geocoding_method,
                updated_at = CURRENT_TIMESTAMP
            """
            
            # 데이터 준비
            values = []
            for item in data:
                values.append((
                    item['data_creation_date'],
                    item['standard_code'],
                    item['mountain_yn'],
                    item['main_number'],
                    item['sub_number'],
                    item['standard_city_county_code'],
                    item['standard_emd_code'],
                    item['road_name_number'],
                    item['underground_yn'],
                    item['building_main_number'],
                    item['building_sub_number'],
                    item['city_province_name'],
                    item['city_county_name'],
                    item['emd_name'],
                    item['legal_dong_name'],
                    item['representative_lot_yn'],
                    item['full_address'],
                    item['lot_number'],
                    item['latitude'],
                    item['longitude'],
                    item['geocoding_method']
                ))
            
            # 배치 삽입 실행
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(insert_query, values)
                    saved_count = cursor.rowcount
                    conn.commit()
            
            logger.info(f"Saved {saved_count} sexual offender address records to database")
            return {'success': True, 'saved_count': saved_count}
            
        except Exception as e:
            logger.error(f"Error saving data to database: {e}")
            return {'success': False, 'error': str(e), 'saved_count': 0}
    
    def _ensure_table_exists(self):
        """성범죄자 주소 정보 테이블 생성"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS sexual_offender_addresses (
            id SERIAL PRIMARY KEY,
            data_creation_date VARCHAR(8),
            standard_code VARCHAR(20) NOT NULL,
            mountain_yn BOOLEAN DEFAULT FALSE,
            main_number INTEGER,
            sub_number INTEGER,
            standard_city_county_code VARCHAR(10),
            standard_emd_code VARCHAR(10),
            road_name_number VARCHAR(20),
            underground_yn BOOLEAN DEFAULT FALSE,
            building_main_number INTEGER,
            building_sub_number INTEGER,
            city_province_name VARCHAR(50),
            city_county_name VARCHAR(50),
            emd_name VARCHAR(50),
            legal_dong_name VARCHAR(50),
            representative_lot_yn BOOLEAN DEFAULT FALSE,
            full_address TEXT,
            lot_number VARCHAR(20),
            latitude DECIMAL(10, 7),
            longitude DECIMAL(10, 7),
            geocoding_method VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(standard_code, main_number, sub_number)
        );
        
        CREATE INDEX IF NOT EXISTS idx_sexual_offender_addresses_location 
        ON sexual_offender_addresses(city_province_name, city_county_name, emd_name);
        
        CREATE INDEX IF NOT EXISTS idx_sexual_offender_addresses_coords 
        ON sexual_offender_addresses(latitude, longitude);
        """
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_table_query)
                    conn.commit()
            logger.info("Sexual offender addresses table ensured")
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            raise
    
    def get_progress_info(self) -> Dict[str, Any]:
        """현재 수집 진행 상황 조회"""
        try:
            # 현재 저장된 데이터 수 조회
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM sexual_offender_addresses")
                    current_count = cursor.fetchone()[0]
            
            # 전체 데이터 수 조회
            total_count = self.get_total_count()
            
            # 진행률 계산
            progress_percentage = (current_count / total_count * 100) if total_count > 0 else 0
            
            return {
                'current_count': current_count,
                'total_count': total_count,
                'progress_percentage': progress_percentage,
                'remaining_count': max(0, total_count - current_count)
            }
            
        except Exception as e:
            logger.error(f"Error getting progress info: {e}")
            return {
                'current_count': 0,
                'total_count': 0,
                'progress_percentage': 0,
                'remaining_count': 0
            }
    
    def run_full_collection(self, max_records: Optional[int] = None) -> Dict[str, Any]:
        """전체 데이터 수집 실행"""
        logger.info("Starting full sexual offender address data collection")
        
        try:
            # 전체 데이터 수 확인
            total_count = self.get_total_count()
            if total_count == 0:
                return {'success': False, 'error': 'No data available'}
            
            # 수집할 최대 레코드 수 결정
            if max_records:
                total_count = min(total_count, max_records)
            
            # 페이지별 수집
            per_page = 1000  # 한 번에 1000개씩
            total_pages = (total_count + per_page - 1) // per_page
            
            total_saved = 0
            total_api_calls = 0
            
            for page in range(1, total_pages + 1):
                logger.info(f"Processing page {page}/{total_pages}")
                
                # 페이지 데이터 조회
                result = self.fetch_data_page(page, per_page)
                total_api_calls += 1
                
                if not result['success']:
                    logger.error(f"Failed to fetch page {page}: {result.get('error')}")
                    continue
                
                if not result['data']:
                    logger.info(f"No data in page {page}, stopping")
                    break
                
                # 데이터 처리
                processed_data = self.process_raw_data(result['data'])
                
                # 좌표 정보 추가 (샘플링)
                if processed_data:
                    # 서울 지역 데이터만 geocoding (비용 절약)
                    seoul_data = [item for item in processed_data if '서울' in item.get('city_province_name', '')]
                    non_seoul_data = [item for item in processed_data if '서울' not in item.get('city_province_name', '')]
                    
                    if seoul_data:
                        seoul_data = self.geocode_addresses(seoul_data)
                    
                    final_data = seoul_data + non_seoul_data
                else:
                    final_data = processed_data
                
                # 데이터베이스 저장
                save_result = self.save_to_database(final_data)
                if save_result['success']:
                    total_saved += save_result['saved_count']
                    logger.info(f"Page {page} completed: {save_result['saved_count']} records saved")
                else:
                    logger.error(f"Failed to save page {page}: {save_result.get('error')}")
                
                # API 제한 고려한 지연
                time.sleep(0.5)
                
                # 일일 제한 확인
                if total_api_calls >= self.daily_limit:
                    logger.warning(f"Daily API limit reached: {total_api_calls}")
                    break
            
            logger.info(f"Sexual offender address collection completed: {total_saved} records saved, {total_api_calls} API calls used")
            
            return {
                'success': True,
                'records_saved': total_saved,
                'api_calls_used': total_api_calls,
                'pages_processed': min(page, total_pages)
            }
            
        except Exception as e:
            logger.error(f"Error in full collection: {e}")
            return {
                'success': False,
                'error': str(e),
                'records_saved': 0,
                'api_calls_used': 0
            }


def main():
    """테스트 실행"""
    print("🔍 Sexual Offender Address Data Controller Test")
    print("=" * 50)
    
    controller = SexualOffenderController()
    
    # 진행 상황 확인
    progress = controller.get_progress_info()
    print(f"\n📊 Current Progress:")
    print(f"   Saved: {progress['current_count']:,} records")
    print(f"   Total: {progress['total_count']:,} records")
    print(f"   Progress: {progress['progress_percentage']:.1f}%")
    
    # 샘플 데이터 수집 테스트
    print(f"\n🧪 Testing sample data collection...")
    result = controller.run_full_collection(max_records=100)
    
    if result['success']:
        print(f"✅ Test completed successfully!")
        print(f"   Records saved: {result['records_saved']}")
        print(f"   API calls used: {result['api_calls_used']}")
    else:
        print(f"❌ Test failed: {result.get('error')}")


if __name__ == "__main__":
    main()