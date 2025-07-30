"""
CCTV 설치 정보 API 컨트롤러

서울시 CCTV 설치 현황 데이터를 수집하고 PostgreSQL에 저장
"""

import logging
import sys
import os
from typing import List, Dict, Any, Optional

# 모듈 import를 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_utils import APIClient, DataProcessor
from db.db_connection import get_db_manager
from config.settings import settings

logger = logging.getLogger(__name__)


class CCTVController:
    """CCTV 설치 정보 API 컨트롤러"""
    
    def __init__(self):
        self.api_client = APIClient()
        self.db_manager = get_db_manager()
        self.data_processor = DataProcessor()
        
        # API 서비스명 (서울 열린데이터 CCTV 서비스)
        self.service_name = "safeOpenCCTV"
        
        # API 필드 -> DB 필드 매핑 (safeOpenCCTV 서비스 기준)
        self.field_mapping = {
            'SVCAREAID': 'district',      # 자치구명
            'ADDR': 'address',            # 주소
            'WGSXPT': 'latitude',         # 위도 (WGS84) 
            'WGSYPT': 'longitude',        # 경도 (WGS84)
            'QTY': 'cctv_count'           # CCTV 개수
        }
        
        # 대체 필드명 (API 응답에 따라 조정)
        self.alternative_fields = {
            'district': ['SVCAREAID', 'BOROGH_NM', 'SGG_NM', 'DISTRICT', '자치구'],
            'dong': ['DONG_NM', 'EMD_NM', 'DONG', '동명'],
            'address': ['ADDR', 'ADDRESS', 'REFINE_ROADNM_ADDR', '주소'],
            'latitude': ['WGSXPT', 'WGSYPT', 'LAT', 'LATITUDE', 'Y', '위도'],
            'longitude': ['WGSYPT', 'WGSXPT', 'LOT', 'LONGITUDE', 'X', '경도'],
            'cctv_count': ['QTY', 'CCTV_CNT', 'CNT', 'COUNT', '개수']
        }
    
    def find_field_value(self, record: Dict[str, Any], field_type: str) -> Any:
        """레코드에서 필드 값 찾기 (대체 필드명 고려)"""
        for field_name in self.alternative_fields.get(field_type, []):
            if field_name in record and record[field_name]:
                return record[field_name]
        return None
    
    def process_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """개별 레코드 처리"""
        try:
            # 각 필드별로 값 찾기
            processed_data = {}
            
            for db_field in ['district', 'dong', 'address', 'latitude', 'longitude', 'cctv_count']:
                value = self.find_field_value(record, db_field)
                
                if db_field == 'latitude':
                    try:
                        processed_data[db_field] = float(value) if value else None
                    except (ValueError, TypeError):
                        processed_data[db_field] = None
                        
                elif db_field == 'longitude':
                    try:
                        processed_data[db_field] = float(value) if value else None
                    except (ValueError, TypeError):
                        processed_data[db_field] = None
                        
                elif db_field == 'cctv_count':
                    try:
                        processed_data[db_field] = int(value) if value else 1
                    except (ValueError, TypeError):
                        processed_data[db_field] = 1
                        
                else:  # 문자열 필드
                    processed_data[db_field] = str(value).strip() if value else None
            
            # 주소 정리
            if processed_data.get('address'):
                processed_data['address'] = self.data_processor.clean_address(processed_data['address'])
            
            # 필수 데이터 검증
            if not processed_data.get('address'):
                logger.warning("Record missing address, skipping")
                return None
            
            # 좌표 유효성 검사 (선택적)
            lat, lon = processed_data.get('latitude'), processed_data.get('longitude')
            if lat and lon:
                if not self.data_processor.validate_coordinates(lat, lon):
                    logger.warning(f"Invalid coordinates ({lat}, {lon}) for address: {processed_data['address']}")
                    # 좌표가 이상해도 주소가 있으면 저장
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing record: {e}")
            return None
    
    def fetch_data(self) -> List[Dict[str, Any]]:
        """API에서 CCTV 데이터 가져오기"""
        logger.info(f"Fetching CCTV data from API service: {self.service_name}")
        
        try:
            # 모든 페이지 데이터 가져오기
            raw_data = self.api_client.fetch_all_pages(self.service_name)
            
            if not raw_data:
                logger.warning("No data fetched from API")
                return []
            
            logger.info(f"Fetched {len(raw_data)} raw records")
            
            # 데이터 처리
            processed_data = []
            for record in raw_data:
                processed_record = self.process_record(record)
                if processed_record:
                    processed_data.append(processed_record)
            
            logger.info(f"Processed {len(processed_data)} valid records")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching CCTV data: {e}")
            return []
    
    def save_to_database(self, data: List[Dict[str, Any]]) -> int:
        """데이터베이스에 데이터 저장"""
        if not data:
            logger.warning("No data to save")
            return 0
        
        logger.info(f"Saving {len(data)} CCTV records to database")
        
        try:
            # 기존 데이터 삭제 (전체 갱신 방식)
            delete_query = "DELETE FROM cctv_installations"
            deleted_count = self.db_manager.execute_non_query(delete_query)
            logger.info(f"Deleted {deleted_count} existing records")
            
            # 새 데이터 삽입
            insert_query = """
                INSERT INTO cctv_installations (district, dong, address, latitude, longitude, cctv_count)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            # 데이터 준비
            insert_data = []
            for record in data:
                insert_data.append((
                    record.get('district'),
                    record.get('dong'),
                    record.get('address'),
                    record.get('latitude'),
                    record.get('longitude'),
                    record.get('cctv_count', 1)
                ))
            
            # 배치 삽입
            inserted_count = self.db_manager.execute_many(insert_query, insert_data)
            logger.info(f"Inserted {inserted_count} new records")
            
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            raise
    
    def run_update(self) -> Dict[str, Any]:
        """CCTV 데이터 업데이트 실행"""
        logger.info("Starting CCTV data update")
        
        start_time = time.time()
        result = {
            'success': False,
            'records_fetched': 0,
            'records_saved': 0,
            'execution_time': 0,
            'error': None
        }
        
        try:
            # 1. API에서 데이터 가져오기
            data = self.fetch_data()
            result['records_fetched'] = len(data)
            
            if not data:
                result['error'] = "No data fetched from API"
                return result
            
            # 2. 데이터베이스에 저장
            saved_count = self.save_to_database(data)
            result['records_saved'] = saved_count
            
            # 3. 성공 처리
            result['success'] = True
            result['execution_time'] = time.time() - start_time
            
            logger.info(f"CCTV data update completed successfully: {saved_count} records")
            
        except Exception as e:
            result['error'] = str(e)
            result['execution_time'] = time.time() - start_time
            logger.error(f"CCTV data update failed: {e}")
        
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """CCTV 설치 현황 통계 조회"""
        try:
            # 전체 통계
            total_query = "SELECT COUNT(*) as total_count, SUM(cctv_count) as total_cctv FROM cctv_installations"
            total_result = self.db_manager.execute_query(total_query)
            
            # 자치구별 통계
            district_query = """
                SELECT district, COUNT(*) as location_count, SUM(cctv_count) as cctv_count
                FROM cctv_installations 
                WHERE district IS NOT NULL
                GROUP BY district 
                ORDER BY cctv_count DESC
            """
            district_result = self.db_manager.execute_query(district_query)
            
            # 좌표 유무 통계
            coord_query = """
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) as with_coords,
                    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL THEN 1 END) as without_coords
                FROM cctv_installations
            """
            coord_result = self.db_manager.execute_query(coord_query)
            
            return {
                'total_locations': total_result[0]['total_count'],
                'total_cctv_count': total_result[0]['total_cctv'],
                'by_district': district_result,
                'coordinates_stats': coord_result[0]
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}


import time

def main():
    """CCTV 컨트롤러 테스트"""
    print("=== CCTV 컨트롤러 테스트 ===\n")
    
    controller = CCTVController()
    
    # 1. 설정 확인
    print("1. 설정 확인:")
    print(f"   API 서비스명: {controller.service_name}")
    print(f"   API 키 설정: {'✅' if settings.SEOUL_OPEN_API_KEY else '❌'}")
    
    # 2. 데이터베이스 연결 테스트
    print(f"\n2. 데이터베이스 연결:")
    if controller.db_manager.test_connection():
        print("   ✅ 연결 성공")
    else:
        print("   ❌ 연결 실패")
        return
    
    # 3. 기존 통계 조회
    print(f"\n3. 기존 데이터 통계:")
    stats = controller.get_statistics()
    if stats:
        print(f"   전체 위치: {stats.get('total_locations', 0)}개")
        print(f"   전체 CCTV: {stats.get('total_cctv_count', 0)}대")
        print(f"   좌표 보유율: {stats.get('coordinates_stats', {}).get('with_coords', 0)}/{stats.get('coordinates_stats', {}).get('total', 0)}")
    else:
        print("   통계 조회 실패 또는 데이터 없음")
    
    # 4. 샘플 데이터 처리 테스트
    print(f"\n4. 샘플 데이터 처리:")
    sample_record = {
        'SVCAREAID': '강남구',
        'ADDR': '서울특별시 강남구 테헤란로 212',
        'WGSXPT': '37.5048',
        'WGSYPT': '127.0438',
        'QTY': '3'
    }
    
    processed = controller.process_record(sample_record)
    if processed:
        print(f"   ✅ 처리 성공: {processed}")
    else:
        print(f"   ❌ 처리 실패")
    
    # 5. 실제 API 호출 및 업데이트 (선택적)
    print(f"\n5. 실제 데이터 업데이트:")
    if settings.SEOUL_OPEN_API_KEY:
        user_input = input("   실제 API 호출을 실행하시겠습니까? (y/N): ")
        if user_input.lower() == 'y':
            print("   데이터 업데이트 실행 중...")
            result = controller.run_update()
            
            if result['success']:
                print(f"   ✅ 업데이트 성공!")
                print(f"   가져온 레코드: {result['records_fetched']}개")
                print(f"   저장된 레코드: {result['records_saved']}개")
                print(f"   실행 시간: {result['execution_time']:.2f}초")
            else:
                print(f"   ❌ 업데이트 실패: {result['error']}")
        else:
            print("   업데이트를 건너뜁니다.")
    else:
        print("   ❌ API 키가 설정되지 않아 실제 호출을 할 수 없습니다.")


if __name__ == "__main__":
    main()