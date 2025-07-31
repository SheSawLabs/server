#!/usr/bin/env python3
"""
전국여성안심지킴이집 서울시 데이터 수집 컨트롤러

서울특별시의 여성안심지킴이집 데이터만 수집하고 처리합니다.
"""

import subprocess
import json
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys
import os

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db_connection import DatabaseManager
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FemaleSafetyHouseController:
    """여성안심지킴이집 서울시 데이터 컨트롤러"""
    
    def __init__(self):
        """컨트롤러 초기화"""
        # 데이터베이스 연결
        self.db = DatabaseManager()
        
        # API 설정
        self.api_key_encoded = "AHGUBivmANZrbio%2FH4PL0qDTg8oJGREiFJbU4IKdSXo%2BG5Bk3rFlrb3QIY7Evt1tFXzOITlKBIKT4b9wkeQHAg%3D%3D"
        self.base_url = "http://api.data.go.kr/openapi/tn_pubr_public_female_safety_prtchouse_api"
        self.daily_limit = 1000  # 일일 API 호출 제한
        self.delay_between_requests = 0.1  # 요청 간 지연 시간
        
        logger.info("FemaleSafetyHouseController initialized")
    
    def fetch_data_with_curl(self, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
        """curl을 이용한 서울시 여성안심지킴이집 데이터 조회"""
        url = f"{self.base_url}?serviceKey={self.api_key_encoded}&pageNo={page}&numOfRows={per_page}&type=json&ctprvnNm=서울특별시"
        
        cmd = [
            'curl', '-k', '-X', 'GET', url,
            '--connect-timeout', '15',
            '--max-time', '30'
        ]
        
        try:
            logger.debug(f"Fetching page {page} with {per_page} records for Seoul")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
            
            if result.returncode == 0:
                response_text = result.stdout
                
                # JSON 파싱
                try:
                    data = json.loads(response_text)
                    
                    if 'response' in data:
                        header = data['response'].get('header', {})
                        if header.get('resultCode') == '00':
                            body = data['response'].get('body', {})
                            items = body.get('items', [])
                            
                            return {
                                'success': True,
                                'data': items,
                                'total_count': int(body.get('totalCount', 0)),
                                'current_page': int(body.get('pageNo', page)),
                                'records_count': len(items)
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
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    logger.debug(f"Response: {response_text[:200]}")
                    return {
                        'success': False,
                        'error': f'JSON decode error: {e}',
                        'data': []
                    }
            else:
                logger.error(f"Curl command failed: {result.stderr}")
                return {
                    'success': False,
                    'error': f'Curl error: {result.stderr}',
                    'data': []
                }
                
        except subprocess.TimeoutExpired:
            logger.error("Request timeout")
            return {
                'success': False,
                'error': 'Request timeout',
                'data': []
            }
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
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
                # 좌표 검증 및 변환
                latitude = None
                longitude = None
                
                try:
                    if item.get('latitude'):
                        latitude = float(item['latitude'])
                    if item.get('longitude'):
                        longitude = float(item['longitude'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid coordinates for {item.get('storNm', 'Unknown')}")
                
                # 운영 여부 변환
                is_active = item.get('useYn', 'N').upper() == 'Y'
                
                # 지정년도 변환
                designation_year = None
                try:
                    if item.get('appnYear'):
                        designation_year = int(item['appnYear'])
                except (ValueError, TypeError):
                    pass
                
                # 주소에서 동 정보 추출
                dong = self._extract_dong_from_address(item.get('rdnmadr', ''), item.get('lnmadr', ''))
                
                processed_item = {
                    'store_name': item.get('storNm', '').strip(),
                    'city_province_name': item.get('ctprvnNm', '').strip(),
                    'district_name': item.get('signguNm', '').strip(),
                    'district_code': item.get('signguCode', '').strip(),
                    'dong_name': dong,
                    'road_address': item.get('rdnmadr', '').strip(),
                    'lot_address': item.get('lnmadr', '').strip(),
                    'latitude': latitude,
                    'longitude': longitude,
                    'phone_number': item.get('phoneNumber', '').strip(),
                    'police_station': item.get('cmptncPolcsttnNm', '').strip(),
                    'designation_year': designation_year,
                    'is_active': is_active,
                    'reference_date': item.get('referenceDate', '').strip(),
                    'institution_code': item.get('insttCode', '').strip(),
                    'institution_name': item.get('insttNm', '').strip()
                }
                
                # 필수 필드 검증
                if not processed_item['store_name']:
                    logger.warning(f"Skipping item with no store name: {item}")
                    continue
                
                processed_data.append(processed_item)
                
            except Exception as e:
                logger.error(f"Error processing item {item}: {e}")
                continue
        
        logger.info(f"Processed {len(processed_data)} female safety house records")
        return processed_data
    
    def save_to_database(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """처리된 데이터를 데이터베이스에 저장"""
        if not data:
            return {'success': True, 'saved_count': 0}
        
        try:
            # 테이블 생성 (없는 경우)
            self._ensure_table_exists()
            
            # UPSERT 쿼리 (중복 방지)
            insert_query = """
            INSERT INTO female_safety_houses (
                store_name, city_province_name, district_name, district_code, dong_name,
                road_address, lot_address, latitude, longitude, phone_number,
                police_station, designation_year, is_active, reference_date,
                institution_code, institution_name
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (store_name, district_code, road_address) DO UPDATE SET
                city_province_name = EXCLUDED.city_province_name,
                district_name = EXCLUDED.district_name,
                dong_name = EXCLUDED.dong_name,
                lot_address = EXCLUDED.lot_address,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                phone_number = EXCLUDED.phone_number,
                police_station = EXCLUDED.police_station,
                designation_year = EXCLUDED.designation_year,
                is_active = EXCLUDED.is_active,
                reference_date = EXCLUDED.reference_date,
                institution_code = EXCLUDED.institution_code,
                institution_name = EXCLUDED.institution_name,
                updated_at = CURRENT_TIMESTAMP
            """
            
            # 데이터 준비
            values = []
            for item in data:
                values.append((
                    item['store_name'],
                    item['city_province_name'],
                    item['district_name'],
                    item['district_code'],
                    item['dong_name'],
                    item['road_address'],
                    item['lot_address'],
                    item['latitude'],
                    item['longitude'],
                    item['phone_number'],
                    item['police_station'],
                    item['designation_year'],
                    item['is_active'],
                    item['reference_date'],
                    item['institution_code'],
                    item['institution_name']
                ))
            
            # 배치 삽입 실행
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(insert_query, values)
                    saved_count = cursor.rowcount
                    conn.commit()
            
            logger.info(f"Upserted {saved_count} female safety house records")
            return {'success': True, 'saved_count': saved_count}
            
        except Exception as e:
            logger.error(f"Error saving data to database: {e}")
            return {'success': False, 'error': str(e), 'saved_count': 0}
    
    def _ensure_table_exists(self):
        """여성안심지킴이집 테이블 생성"""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS female_safety_houses (
            id SERIAL PRIMARY KEY,
            store_name VARCHAR(200) NOT NULL,
            city_province_name VARCHAR(50),
            district_name VARCHAR(50),
            district_code VARCHAR(10),
            dong_name VARCHAR(50),
            road_address TEXT,
            lot_address TEXT,
            latitude DECIMAL(10, 7),
            longitude DECIMAL(10, 7),
            phone_number VARCHAR(20),
            police_station VARCHAR(100),
            designation_year INTEGER,
            is_active BOOLEAN DEFAULT TRUE,
            reference_date VARCHAR(10),
            institution_code VARCHAR(20),
            institution_name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(store_name, district_code, road_address)
        );
        
        CREATE INDEX IF NOT EXISTS idx_female_safety_houses_location 
        ON female_safety_houses(city_province_name, district_name, dong_name);
        
        CREATE INDEX IF NOT EXISTS idx_female_safety_houses_coords 
        ON female_safety_houses(latitude, longitude);
        
        CREATE INDEX IF NOT EXISTS idx_female_safety_houses_active 
        ON female_safety_houses(is_active);
        """
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_table_query)
                    conn.commit()
            logger.info("Female safety houses table ensured")
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            raise
    
    def _extract_dong_from_address(self, road_address: str, lot_address: str) -> str:
        """주소에서 동 정보 추출"""
        import re
        
        # 우선순위: 지번주소 -> 도로명주소
        addresses_to_check = [lot_address, road_address]
        
        for address in addresses_to_check:
            if not address:
                continue
                
            # 동 패턴 매칭 (동, 가동, 로동 등)
            dong_patterns = [
                r'([가-힣]+(?:동|가동|로동|리))',  # 기본 동 패턴
                r'([가-힣]+(?:면|리))',           # 면, 리 패턴
                r'([가-힣]+(?:가))',              # 가 패턴
            ]
            
            for pattern in dong_patterns:
                matches = re.findall(pattern, address)
                if matches:
                    # 첫 번째 동 정보 사용
                    dong = matches[0]
                    
                    # 동 정규화
                    dong = dong.replace('동', '동')  # 동 확실히 하기
                    if not dong.endswith(('동', '가동', '로동', '면', '리', '가')):
                        dong += '동'
                    
                    logger.debug(f"Extracted dong '{dong}' from address: {address}")
                    return dong
        
        # 동을 찾지 못한 경우
        logger.debug(f"Could not extract dong from addresses: {road_address}, {lot_address}")
        return None
    
    def get_progress_info(self) -> Dict[str, Any]:
        """현재 수집 진행 상황 조회"""
        try:
            # 현재 저장된 데이터 수 조회
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) as count FROM female_safety_houses")
                    result = cursor.fetchone()
                    current_count = result['count'] if result else 0
                    
                    # 활성 상태별 통계
                    cursor.execute("""
                        SELECT 
                            COUNT(*) FILTER (WHERE is_active = true) as active_count,
                            COUNT(*) FILTER (WHERE is_active = false) as inactive_count
                        FROM female_safety_houses
                    """)
                    stats = cursor.fetchone()
                    active_count = stats['active_count'] if stats else 0
                    inactive_count = stats['inactive_count'] if stats else 0
            
            # 전체 데이터 수는 API로 조회
            api_result = self.fetch_data_with_curl(page=1, per_page=1)
            total_count = api_result.get('total_count', 0) if api_result['success'] else 728
            
            # 진행률 계산
            progress_percentage = (current_count / total_count * 100) if total_count > 0 else 0
            
            return {
                'current_count': current_count,
                'total_count': total_count,
                'progress_percentage': progress_percentage,
                'remaining_count': max(0, total_count - current_count),
                'active_count': active_count,
                'inactive_count': inactive_count
            }
            
        except Exception as e:
            logger.error(f"Error getting progress info: {e}")
            return {
                'current_count': 0,
                'total_count': 728,  # 기본값
                'progress_percentage': 0,
                'remaining_count': 728,
                'active_count': 0,
                'inactive_count': 0
            }
    
    def run_full_collection(self) -> Dict[str, Any]:
        """전체 서울시 여성안심지킴이집 데이터 수집"""
        logger.info("Starting Seoul female safety house data collection")
        
        try:
            per_page = 100  # 한 번에 100개씩
            total_fetched = 0
            total_saved = 0
            total_api_calls = 0
            current_page = 1
            
            while True:
                # API 호출 제한 확인
                if total_api_calls >= self.daily_limit:
                    logger.warning(f"Daily API limit reached: {total_api_calls}")
                    break
                
                # 페이지 데이터 조회
                logger.info(f"Processing page {current_page}")
                result = self.fetch_data_with_curl(current_page, per_page)
                total_api_calls += 1
                
                if not result['success']:
                    logger.error(f"Failed to fetch page {current_page}: {result.get('error')}")
                    break
                
                if not result['data']:
                    logger.info(f"No more data available at page {current_page}")
                    break
                
                # 데이터 처리
                processed_data = self.process_raw_data(result['data'])
                total_fetched += len(processed_data)
                
                # 데이터베이스 저장
                save_result = self.save_to_database(processed_data)
                if save_result['success']:
                    total_saved += save_result['saved_count']
                    logger.info(f"Page {current_page} completed: {save_result['saved_count']} records upserted")
                else:
                    logger.error(f"Failed to save page {current_page}: {save_result.get('error')}")
                    break
                
                # 요청 간 지연
                time.sleep(self.delay_between_requests)
                
                # 다음 페이지로
                current_page += 1
                
                # 총 데이터 수에 도달했는지 확인
                if total_fetched >= result.get('total_count', 0):
                    logger.info(f"All data collected: {total_fetched}/{result.get('total_count', 0)}")
                    break
            
            logger.info(f"Seoul female safety house collection completed: {total_fetched} records fetched, {total_saved} records saved, {total_api_calls} API calls used")
            
            return {
                'success': True,
                'records_fetched': total_fetched,
                'records_saved': total_saved,
                'api_calls_used': total_api_calls,
                'pages_processed': current_page - 1
            }
            
        except Exception as e:
            logger.error(f"Error in full collection: {e}")
            return {
                'success': False,
                'error': str(e),
                'records_fetched': 0,
                'records_saved': 0,
                'api_calls_used': 0
            }


def main():
    """테스트 실행"""
    print("🏠 Seoul Female Safety House Controller Test")
    print("=" * 60)
    
    controller = FemaleSafetyHouseController()
    
    # 진행 상황 확인
    progress = controller.get_progress_info()
    print(f"\n📊 Current Progress:")
    print(f"   Saved: {progress['current_count']:,} records")
    print(f"   Total: {progress['total_count']:,} records")
    print(f"   Progress: {progress['progress_percentage']:.1f}%")
    print(f"   Active: {progress['active_count']:,} / Inactive: {progress['inactive_count']:,}")
    
    # 전체 데이터 수집
    print(f"\n🧪 Starting full data collection...")
    result = controller.run_full_collection()
    
    if result['success']:
        print(f"✅ Collection completed successfully!")
        print(f"   Records fetched: {result['records_fetched']}")
        print(f"   Records saved: {result['records_saved']}")
        print(f"   API calls used: {result['api_calls_used']}")
        print(f"   Pages processed: {result['pages_processed']}")
        
        # 업데이트된 진행 상황
        progress_after = controller.get_progress_info()
        print(f"\n📊 Final Status:")
        print(f"   Total saved: {progress_after['current_count']:,} records")
        print(f"   Active: {progress_after['active_count']:,} / Inactive: {progress_after['inactive_count']:,}")
        
    else:
        print(f"❌ Collection failed: {result.get('error')}")


if __name__ == "__main__":
    main()