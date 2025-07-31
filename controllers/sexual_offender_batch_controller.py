#!/usr/bin/env python3
"""
성범죄자 공개 및 고지 지번 주소 정보 배치 수집 컨트롤러

curl을 이용해 API를 호출하고 데이터를 수집합니다.
일일 10,000개 제한에 맞춰 자동 수집합니다.
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


class SexualOffenderBatchController:
    """성범죄자 주소 정보 배치 수집 컨트롤러"""
    
    def __init__(self):
        """컨트롤러 초기화"""
        # 데이터베이스 연결
        self.db = DatabaseManager()
        
        # API 설정
        self.api_key_encoded = "AHGUBivmANZrbio%2FH4PL0qDTg8oJGREiFJbU4IKdSXo%2BG5Bk3rFlrb3QIY7Evt1tFXzOITlKBIKT4b9wkeQHAg%3D%3D"
        self.base_url = "https://apis.data.go.kr/1383000/sais/SexualAbuseNoticeHouseNumAddrServiceV2/getSexualAbuseNoticeHouseNumAddrListV2"
        self.daily_limit = 9500  # 일일 API 호출 제한 (여유분 고려)
        self.delay_between_requests = 0.2  # 요청 간 지연 시간
        
        logger.info("SexualOffenderBatchController initialized")
    
    def fetch_data_with_curl(self, page: int = 1, per_page: int = 1000) -> Dict[str, Any]:
        """curl을 이용한 데이터 조회"""
        url = f"{self.base_url}?serviceKey={self.api_key_encoded}&pageNo={page}&numOfRows={per_page}&type=json"
        
        cmd = [
            'curl', '-k', '-X', 'GET', url,
            '--connect-timeout', '15',
            '--max-time', '30'
        ]
        
        try:
            logger.debug(f"Fetching page {page} with {per_page} records")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
            
            if result.returncode == 0:
                response_text = result.stdout
                
                # JSON 파싱
                try:
                    data = json.loads(response_text)
                    
                    if 'response' in data:
                        header = data['response'].get('header', {})
                        if header.get('resultCode') == '0':
                            body = data['response'].get('body', {})
                            items = body.get('items', {})
                            
                            # items 처리
                            if isinstance(items, dict) and 'item' in items:
                                data_list = items['item']
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
                    'latitude': None,  # 나중에 지오코딩
                    'longitude': None,
                    'geocoding_method': 'pending'
                }
                
                processed_data.append(processed_item)
                
            except Exception as e:
                logger.error(f"Error processing item {item}: {e}")
                continue
        
        logger.info(f"Processed {len(processed_data)} sexual offender address records")
        return processed_data
    
    def save_to_database_append(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """처리된 데이터를 데이터베이스에 추가 (UPSERT)"""
        if not data:
            return {'success': True, 'saved_count': 0}
        
        try:
            # UPSERT 쿼리 (중복 방지)
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
            
            logger.info(f"Upserted {saved_count} sexual offender records")
            return {'success': True, 'saved_count': saved_count}
            
        except Exception as e:
            logger.error(f"Error saving data to database: {e}")
            return {'success': False, 'error': str(e), 'saved_count': 0}
    
    def get_progress_info(self) -> Dict[str, Any]:
        """현재 수집 진행 상황 조회"""
        try:
            # 현재 저장된 데이터 수 조회
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) as count FROM sexual_offender_addresses")
                    result = cursor.fetchone()
                    current_count = result['count'] if result else 0
            
            # 전체 데이터 수는 API로 조회
            api_result = self.fetch_data_with_curl(page=1, per_page=1)
            total_count = api_result.get('total_count', 0) if api_result['success'] else 600201
            
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
                'total_count': 600201,  # 기본값
                'progress_percentage': 0,
                'remaining_count': 600201
            }
    
    def run_batch_update(self, max_records: Optional[int] = None, start_page: int = 1) -> Dict[str, Any]:
        """배치 데이터 수집 실행"""
        logger.info(f"Starting sexual offender batch collection from page {start_page}")
        
        try:
            per_page = 1000  # 한 번에 1000개씩
            total_fetched = 0
            total_saved = 0
            total_api_calls = 0
            current_page = start_page
            
            while True:
                # API 호출 제한 확인
                if total_api_calls >= self.daily_limit:
                    logger.warning(f"Daily API limit reached: {total_api_calls}")
                    break
                
                # 최대 레코드 수 확인
                if max_records and total_fetched >= max_records:
                    logger.info(f"Max records limit reached: {total_fetched}")
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
                
                # 최대 레코드 수 조정
                if max_records:
                    remaining = max_records - total_fetched
                    if remaining < len(processed_data):
                        processed_data = processed_data[:remaining]
                
                total_fetched += len(processed_data)
                
                # 데이터베이스 저장
                save_result = self.save_to_database_append(processed_data)
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
                
                # 최대 레코드 수 도달 확인
                if max_records and total_fetched >= max_records:
                    logger.info(f"Reached max_records limit: {max_records}")
                    break
            
            logger.info(f"Sexual offender batch collection completed: {total_fetched} records fetched, {total_saved} records saved, {total_api_calls} API calls used")
            
            return {
                'success': True,
                'records_fetched': total_fetched,
                'records_saved': total_saved,
                'api_calls_used': total_api_calls,
                'pages_processed': current_page - start_page
            }
            
        except Exception as e:
            logger.error(f"Error in batch collection: {e}")
            return {
                'success': False,
                'error': str(e),
                'records_fetched': 0,
                'records_saved': 0,
                'api_calls_used': 0
            }


def main():
    """테스트 실행"""
    print("🏢 Sexual Offender Address Batch Controller Test")
    print("=" * 60)
    
    controller = SexualOffenderBatchController()
    
    # 진행 상황 확인
    progress = controller.get_progress_info()
    print(f"\n📊 Current Progress:")
    print(f"   Saved: {progress['current_count']:,} records")
    print(f"   Total: {progress['total_count']:,} records")
    print(f"   Progress: {progress['progress_percentage']:.1f}%")
    print(f"   Remaining: {progress['remaining_count']:,} records")
    
    # 샘플 데이터 수집 테스트 (500개)
    print(f"\n🧪 Testing sample data collection (500 records)...")
    result = controller.run_batch_update(max_records=500)
    
    if result['success']:
        print(f"✅ Test completed successfully!")
        print(f"   Records fetched: {result['records_fetched']}")
        print(f"   Records saved: {result['records_saved']}")
        print(f"   API calls used: {result['api_calls_used']}")
        print(f"   Pages processed: {result['pages_processed']}")
        
        # 업데이트된 진행 상황
        progress_after = controller.get_progress_info()
        print(f"\n📊 Updated Progress:")
        print(f"   Saved: {progress_after['current_count']:,} records")
        print(f"   Progress: {progress_after['progress_percentage']:.1f}%")
        
    else:
        print(f"❌ Test failed: {result.get('error')}")


if __name__ == "__main__":
    main()